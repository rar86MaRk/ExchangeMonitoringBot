import asyncio
import logging
from typing import Dict, Optional

import ccxt.async_support as ccxt
from ccxt.base.errors import ExchangeError

logger = logging.getLogger("exchange_monitor.services.exchange")


def normalize_symbol(symbol: str) -> str:
    """Приводит ETHUSDT, ETH-USDT, ETH/USDT, ETH/USDT:USDT -> ETH/USDT (формат ccxt)"""
    s = symbol.upper().replace('_', '').replace('-', '/')
    # Убираем суффикс после : (например, :USDT для перпетуалов на APEX)
    if ':' in s:
        s = s.split(':')[0]
    if '/' in s:
        return s
    for quote in ('USDT', 'BUSD', 'USDC', 'BTC', 'ETH', 'BNB'):
        if s.endswith(quote):
            base = s[:-len(quote)]
            if base:
                return f"{base}/{quote}"
    return s


class ExchangeService:
    """Обёртка над ccxt (async_support) для получения текущих цен по парам."""

    def __init__(self) -> None:
        self._exchanges: Dict[str, ccxt.Exchange] = {}

    def _get_exchange(self, exchange_name: str) -> ccxt.Exchange:
        exchange_name = exchange_name.lower()
        if exchange_name not in self._exchanges:
            exchange_class = getattr(ccxt, exchange_name, None)
            if exchange_class is None:
                raise ValueError(f"Биржа '{exchange_name}' не поддерживается ccxt")
            self._exchanges[exchange_name] = exchange_class({"enableRateLimit": True})
        return self._exchanges[exchange_name]

    async def fetch_ticker(self, exchange_name: str, symbol: str) -> Optional[float]:
        """
        Возвращает закрытую цену (close) последней свечи.
        Возвращает None при ошибке (биржа недоступна, пара не найдена и т.д.).
        """
        normalized = normalize_symbol(symbol)
        try:
            exchange = self._get_exchange(exchange_name)
            # Load markets if needed
            if not exchange.markets:
                await exchange.load_markets()
            
            # Сначала пробуем нормализованный символ
            if normalized in exchange.markets:
                target_symbol = normalized
            # Если не нашли, пробуем оригинальный символ (с суффиксом :USDT и т.д.)
            elif symbol.upper() in exchange.markets:
                target_symbol = symbol.upper()
            else:
                logger.warning("Пара %s (норм: %s) не найдена на бирже %s", symbol, normalized, exchange_name)
                return None

            ticker = await exchange.fetch_ticker(target_symbol)
            price = ticker.get("close")
            if price is None:
                price = ticker.get("last")
            return float(price) if price else None
        except ExchangeError as exc:
            logger.warning("Ошибка биржи %s при получении %s: %s", exchange_name, symbol, exc)
            return None
        except Exception as exc:
            logger.exception("Неожиданная ошибка при получении цены %s на %s: %s", symbol, exchange_name, exc)
            return None

    async def validate_symbol(self, exchange_name: str, symbol: str) -> bool:
        """Проверяет, существует ли пара на указанной бирже."""
        normalized = normalize_symbol(symbol)
        try:
            exchange = self._get_exchange(exchange_name)
            if not exchange.markets:
                await exchange.load_markets()
            # Проверяем и нормализованный, и оригинальный символ
            if normalized in exchange.markets:
                return True
            if symbol.upper() in exchange.markets:
                return True
            return False
        except Exception as exc:
            logger.exception("Ошибка при проверке пары %s на %s: %s", symbol, exchange_name, exc)
            return False

    async def close(self) -> None:
        """Закрывает все открытые HTTP-сессии ccxt."""
        tasks = []
        for name, exchange in self._exchanges.items():
            tasks.append(exchange.close())
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._exchanges.clear()