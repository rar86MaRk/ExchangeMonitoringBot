#!/usr/bin/env python3
"""
Скрипт инициализации первого админского ключа.
Запускать один раз после первого деплоя:
    python -m scripts.init_admin
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import Database
from config import DATABASE_PATH


async def main():
    db = Database(DATABASE_PATH)
    await db.init()

    keys = await db.list_keys()
    admin_keys = [k for k in keys if k["is_admin"] and k["is_active"]]

    if admin_keys:
        print("Admin key already exists:")
        for k in admin_keys:
            print(f"   ID: {k['id']}, Prefix: {k['prefix']}***")
        await db.close()
        return

    key = await db.create_access_key(is_admin=True, created_by=0)
    print("=== CREATED FIRST ADMIN KEY (SUPER-ADMIN) ===")
    print(f"Key: {key}")
    print("\nSAVE THIS KEY! It's shown only once.")
    print("Use: /register <key> in bot to get admin rights.")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())