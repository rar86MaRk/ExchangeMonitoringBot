import asyncio
import logging
from typing import Callable

from aiogram import Bot

from database import Database
from services.exchange import ExchangeService

logger = logging.getLogger("exchange_monitor.services.monitor")


def format_change_price(old_price: float, new_price: float) -> tuple[float, str]:
    change = new_price - old_price
    change_percent = (change / old_price * 100) if old_price else 0.0
    sign = "+" if change > 0 else ("" if change < 0 else "±")
    return change_percent, sign


class PriceMonitor:
    def __init__(
        self,
        db: Database,
        exchange_service: ExchangeService,
        bot: Bot,
        interval_seconds: int = 60,
        notify_callback: Callable | None = None,
    ):
        self.db = db
        self.exchange_service = exchange_service
        self.bot = bot
        self.interval_seconds = interval_seconds
        self.notify_callback = notify_callback or self._default_notify
        self._task: asyncio.Task | None = None

    async def _default_notify(self, user_id: int, message: str) -> bool:
        try:
            await self.bot.send_message(user_id, message, parse_mode="HTML")
            return True
        except Exception as exc:
            logger.exception("Не удалось отправить алерт пользователю %s: %s", user_id, exc)
            return False

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run_loop())
        logger.info("PriceMonitor started, interval %s seconds", self.interval_seconds)

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info("PriceMonitor stopped")

    async def _run_loop(self) -> None:
        while True:
            try:
                await self.check_once()
            except Exception:
                logger.exception("Непоправимая ошибка в цикле мониторинга")
            await asyncio.sleep(self.interval_seconds)

    async def check_once(self) -> None:
        alerts = await self.get_all_active_alerts()
        if not alerts:
            return

        grouped = self._group_by_exchange_and_ticker(alerts)
        for (exchange_name, ticker), group in grouped.items():
            try:
                price = await self.exchange_service.fetch_ticker(exchange_name, ticker)
                if price is None:
                    logger.warning("Не удалось получить цену для %s/%s", exchange_name, ticker)
                    continue

                for alert in group:
                    change_percent, sign = format_change_price(alert.base_price, price)
                    if self._check_direction(alert.direction, change_percent, alert.threshold_percent):
                        await self._send_alert(alert, price, change_percent, sign)
            except Exception:
                logger.exception("Ошибка при проверке пары %s/%s", exchange_name, ticker)

    def _check_direction(self, direction: str, change_percent: float, threshold: float) -> bool:
        if direction == "up":
            return change_percent >= threshold
        elif direction == "down":
            return change_percent <= -threshold
        else:  # both
            return abs(change_percent) >= threshold

    def _group_by_exchange_and_ticker(self, alerts):
        grouped = {}
        for a in alerts:
            key = (a.exchange, a.ticker)
            grouped.setdefault(key, []).append(a)
        return grouped

    async def _send_alert(self, alert, current_price, change_percent, sign):
        message = (
            f"<b>🚨 АЛЕРТ</b>: {alert.ticker} на {alert.exchange.upper()} "
            f"изменился на {sign}{change_percent:.4f}%!\n"
            f"Текущая цена: ${current_price:,.2f}"
        )
        success = await self.notify_callback(alert.user_id, message)
        if success:
            await self.db.update_base_price(alert.id, current_price)
            logger.info(
                "Алерт отправлен %s (ID %s), новый базовый: %.2f",
                alert.user_id,
                alert.id,
                current_price,
            )

    async def get_all_active_alerts(self):
        rows = await self.db.get_all_active_alerts()
        return [
            type("_Alert", (), {
                "id": row[0],
                "user_id": row[1],
                "ticker": row[2],
                "threshold_percent": row[3],
                "exchange": row[4],
                "base_price": row[5],
                "direction": row[6],
            })()
            for row in rows
        ]

    async def cleanup_closed_alerts(self) -> None:
        """Форсирует завершение мониторинга (например, при остановке бота)."""
        await self.stop()