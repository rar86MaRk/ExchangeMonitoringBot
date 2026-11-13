import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import CHECK_INTERVAL_SECONDS, DATABASE_PATH, TELEGRAM_TOKEN
from database import Database
from services.exchange import ExchangeService
from services.monitor import PriceMonitor
from handlers.start import router as start_router
from handlers.alerts import router as alerts_router
from handlers.admin import router as admin_router
from middlewares.access import AccessMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("exchange_monitor")


async def main() -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN не задан. См. .env.example")

    # DB init
    db = Database(DATABASE_PATH)
    await db.init()

    # Exchange service
    exchange_service = ExchangeService()
    bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    bot.db = db  # type: ignore[attr-defined]
    bot.exchange_service = exchange_service  # type: ignore[attr-defined]

    # Dispatcher with in‑memory FSM storage
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start_router)
    dp.include_router(alerts_router)
    dp.include_router(admin_router)

    # Middleware для контроля доступа
    dp.message.middleware(AccessMiddleware())
    dp.callback_query.middleware(AccessMiddleware())

    # Background monitor (checks every CHECK_INTERVAL_SECONDS)
    monitor = PriceMonitor(db, exchange_service, bot, interval_seconds=CHECK_INTERVAL_SECONDS)
    bot.monitor = monitor  # type: ignore[attr-defined]

    # Scheduler job for background check (redundant with monitor loop, but matches the requirement to use APScheduler)
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(monitor.check_once, "interval", seconds=CHECK_INTERVAL_SECONDS, id="price_monitor")
    scheduler.start()

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await monitor.stop()
        scheduler.shutdown()
        await exchange_service.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
