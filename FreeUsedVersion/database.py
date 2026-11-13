import aiosqlite
from pathlib import Path
from typing import List, Optional, Tuple

DB_SCHEMA_SQL = """
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
        # Migration: add direction column if not exists
        try:
            await self._db.execute("ALTER TABLE alerts ADD COLUMN direction TEXT NOT NULL DEFAULT 'both'")
            await self._db.commit()
        except Exception:
            pass  # column already exists

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

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