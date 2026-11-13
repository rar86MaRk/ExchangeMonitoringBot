import aiosqlite
import secrets
from pathlib import Path
from typing import List, Optional, Tuple

DB_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS access_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_by INTEGER,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    is_banned INTEGER NOT NULL DEFAULT 0,
    access_key_id INTEGER,
    registered_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    FOREIGN KEY (access_key_id) REFERENCES access_keys(id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    threshold_percent REAL NOT NULL DEFAULT 0.5,
    exchange TEXT NOT NULL DEFAULT 'binance',
    base_price REAL NOT NULL DEFAULT 0.0,
    is_active INTEGER NOT NULL DEFAULT 1,
    direction TEXT NOT NULL DEFAULT 'both',
    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    UNIQUE(user_id, ticker, exchange)
);

CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(user_id, is_active, ticker, exchange);
CREATE INDEX IF NOT EXISTS idx_access_keys_hash ON access_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_users_key ON users(access_key_id);
"""

INSERT_ALERT_SQL = """
INSERT INTO alerts (user_id, ticker, threshold_percent, exchange, base_price, is_active, direction)
VALUES (?, ?, ?, ?, ?, 1, ?)
ON CONFLICT(user_id, ticker, exchange) DO UPDATE SET
    threshold_percent = excluded.threshold_percent,
    base_price = excluded.base_price,
    is_active = 1,
    direction = excluded.direction;
"""

GET_ALERTS_BY_USER_SQL = """
SELECT id, ticker, threshold_percent, exchange, base_price, is_active, direction
FROM alerts
WHERE user_id = ? AND is_active = 1
ORDER BY created_at DESC;
"""

DELETE_ALERT_SQL = """
UPDATE alerts SET is_active = 0 WHERE id = ?;
"""


class Database:
    def __init__(self, path: str):
        self.path = path
        self._db: Optional[aiosqlite.Connection] = None

    async def init(self) -> None:
        self._db = await aiosqlite.connect(str(self.path))
        await self._db.executescript(DB_SCHEMA_SQL)
        # Migration: add direction column to alerts if not exists
        try:
            await self._db.execute("ALTER TABLE alerts ADD COLUMN direction TEXT NOT NULL DEFAULT 'both'")
            await self._db.commit()
        except Exception:
            pass  # column already exists

        # Migration: add new columns to users table if not exists
        for col, col_type in [
            ("role", "TEXT NOT NULL DEFAULT 'user'"),
            ("is_banned", "INTEGER NOT NULL DEFAULT 0"),
            ("access_key_id", "INTEGER"),
            ("registered_at", "INTEGER NOT NULL DEFAULT (strftime('%s','now'))"),
        ]:
            try:
                await self._db.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
                await self._db.commit()
            except Exception:
                pass

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    # ===== Access Keys =====

    @staticmethod
    def _hash_key(key: str) -> str:
        import hashlib
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def _generate_key() -> str:
        return secrets.token_urlsafe(18)  # ~24 chars

    @staticmethod
    def _get_prefix(key: str) -> str:
        return key[:8]

    async def create_access_key(self, is_admin: bool, created_by: int) -> str:
        """Создает новый ключ доступа. Возвращает plaintext ключ (только один раз!)."""
        key = self._generate_key()
        key_hash = self._hash_key(key)
        prefix = self._get_prefix(key)
        await self._db.execute(
            "INSERT INTO access_keys (key_hash, key_prefix, is_admin, created_by) VALUES (?, ?, ?, ?)",
            (key_hash, prefix, 1 if is_admin else 0, created_by)
        )
        await self._db.commit()
        return key

    async def verify_key(self, key: str) -> Optional[dict]:
        """Проверяет ключ и возвращает инфо о нем если валидный."""
        key_hash = self._hash_key(key)
        row = await self._db.execute(
            "SELECT id, is_admin, is_active FROM access_keys WHERE key_hash = ?", (key_hash,)
        )
        result = await row.fetchone()
        if result and result[2]:  # is_active
            return {"id": result[0], "is_admin": bool(result[1])}
        return None

    async def get_key_info(self, key_id: int) -> Optional[dict]:
        row = await self._db.execute(
            "SELECT id, key_prefix, is_admin, created_by, created_at, is_active FROM access_keys WHERE id = ?",
            (key_id,)
        )
        result = await row.fetchone()
        if result:
            return {
                "id": result[0], "prefix": result[1], "is_admin": bool(result[2]),
                "created_by": result[3], "created_at": result[4], "is_active": bool(result[5])
            }
        return None

    async def list_keys(self) -> List[dict]:
        rows = await self._db.execute(
            "SELECT id, key_prefix, is_admin, created_by, created_at, is_active FROM access_keys ORDER BY created_at DESC"
        )
        return [
            {"id": r[0], "prefix": r[1], "is_admin": bool(r[2]), "created_by": r[3], "created_at": r[4], "is_active": bool(r[5])}
            for r in await rows.fetchall()
        ]

    async def deactivate_key(self, key_id: int) -> None:
        await self._db.execute("UPDATE access_keys SET is_active = 0 WHERE id = ?", (key_id,))
        await self._db.commit()

    # ===== Users =====

    async def register_user(self, user_id: int, username: str, key: str) -> bool:
        """Регистрирует пользователя по ключу. Возвращает True если успех."""
        key_info = await self.verify_key(key)
        if not key_info:
            return False

        key_id = key_info["id"]
        is_admin = key_info["is_admin"]
        role = "admin" if is_admin else "user"

        # Проверяем есть ли уже пользователь
        existing = await self._db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if await existing.fetchone():
            # Обновляем роль если нужно
            await self._db.execute(
                "UPDATE users SET username = ?, role = ?, access_key_id = ?, is_banned = 0 WHERE user_id = ?",
                (username, role, key_id, user_id)
            )
        else:
            await self._db.execute(
                "INSERT INTO users (user_id, username, role, access_key_id) VALUES (?, ?, ?, ?)",
                (user_id, username, role, key_id)
            )
        await self._db.commit()
        return True

    async def get_user(self, user_id: int) -> Optional[dict]:
        row = await self._db.execute(
            "SELECT user_id, username, role, is_banned, access_key_id, registered_at FROM users WHERE user_id = ?",
            (user_id,)
        )
        result = await row.fetchone()
        if result:
            return {
                "user_id": result[0], "username": result[1], "role": result[2],
                "is_banned": bool(result[3]), "access_key_id": result[4], "registered_at": result[5]
            }
        return None

    async def is_admin(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        return user and user["role"] == "admin" and not user["is_banned"]

    async def is_super_admin(self, user_id: int) -> bool:
        """Супер-админ — это первый созданный админ (created_by = NULL или created_by = 0)"""
        user = await self.get_user(user_id)
        if not user or user["role"] != "admin" or user["is_banned"]:
            return False
        key_info = await self.get_key_info(user["access_key_id"])
        return key_info and (key_info["created_by"] is None or key_info["created_by"] == 0)

    async def is_banned(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        return user and user["is_banned"]

    async def ban_user(self, admin_id: int, target_id: int) -> bool:
        """Банит пользователя. Админ может забанить любого, супер-админ может забанить админа."""
        admin = await self.get_user(admin_id)
        target = await self.get_user(target_id)
        if not admin or not target:
            return False
        if admin["role"] != "admin" or admin["is_banned"]:
            return False
        if target["role"] == "admin" and not await self.is_super_admin(admin_id):
            return False  # Только супер-админ может банить админов
        await self._db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (target_id,))
        await self._db.commit()
        return True

    async def unban_user(self, admin_id: int, target_id: int) -> bool:
        """Разбанивает пользователя."""
        admin = await self.get_user(admin_id)
        if not admin or admin["role"] != "admin" or admin["is_banned"]:
            return False
        await self._db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (target_id,))
        await self._db.commit()
        return True

    async def list_users(self) -> List[dict]:
        rows = await self._db.execute(
            "SELECT user_id, username, role, is_banned, access_key_id, registered_at FROM users ORDER BY registered_at DESC"
        )
        return [
            {"user_id": r[0], "username": r[1], "role": r[2], "is_banned": bool(r[3]),
             "access_key_id": r[4], "registered_at": r[5]}
            for r in await rows.fetchall()
        ]

    # ===== Alerts (existing) =====

    async def add_alert(self, user_id: int, ticker: str, threshold_percent: float, exchange: str, base_price: float, direction: str = "both") -> None:
        await self._db.execute(INSERT_ALERT_SQL, (user_id, ticker, threshold_percent, exchange, base_price, direction))
        await self._db.commit()

    async def get_active_alerts(self, user_id: int) -> List[Tuple[int, str, float, str, float, int, str]]:
        rows = await self._db.execute(GET_ALERTS_BY_USER_SQL, (user_id,))
        return await rows.fetchall()

    async def delete_alert(self, alert_id: int) -> None:
        await self._db.execute(DELETE_ALERT_SQL, (alert_id,))
        await self._db.commit()

    async def set_inactive(self, alert_id: int) -> None:
        await self._db.execute("UPDATE alerts SET is_active = 0 WHERE id = ?", (alert_id,))
        await self._db.commit()

    async def get_alert_by_id(self, alert_id: int) -> Optional[Tuple[int, int, str, float, str, float, int, str]]:
        rows = await self._db.execute(
            "SELECT id, user_id, ticker, threshold_percent, exchange, base_price, is_active, direction FROM alerts WHERE id = ?",
            (alert_id,),
        )
        row = await rows.fetchone()
        if row:
            return row
        return None

    async def update_base_price(self, alert_id: int, new_price: float) -> None:
        await self._db.execute(
            "UPDATE alerts SET base_price = ?, created_at = strftime('%s','now') WHERE id = ?",
            (new_price, alert_id),
        )
        await self._db.commit()

    async def get_all_active_alerts(self) -> List[Tuple[int, int, str, float, str, float, str]]:
        rows = await self._db.execute(
            "SELECT id, user_id, ticker, threshold_percent, exchange, base_price, direction FROM alerts WHERE is_active = 1"
        )
        return await rows.fetchall()