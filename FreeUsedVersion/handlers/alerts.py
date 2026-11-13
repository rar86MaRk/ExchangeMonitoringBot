import logging
import re
from typing import Optional

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

import ccxt.async_support as ccxt

from database import Database
from services.exchange import ExchangeService, normalize_symbol

logger = logging.getLogger("exchange_monitor.handlers.alerts")

router = Router()


# Получаем список всех доступных бирж из ccxt
def get_all_exchanges() -> list[str]:
    """Возвращает отсортированный список всех бирж, доступных в ccxt."""
    return sorted([name for name in ccxt.exchanges if not name.startswith('_')])


class AddAlertState(StatesGroup):
    awaiting_input = State()


def parse_alert_command(text: str) -> Optional[tuple[str, str, float, str]]:
    # Формат: /add_alert [тикер] [up/down/both] [процент] [биржа]
    # Примеры: /add_alert ETHUSDT up 0.5 binance
    #          /add_alert ETH/USDT down 1.0 bybit
    #          /add_alert BTCUSDT both 0.3 binance
    #          /add_alert BTC/USDT:USDT both 0.001 apex
    #          /add_alert BTC/NIS both 0.001 bit2c
    pattern = re.compile(
        r"^/add_alert\s+([A-Za-z0-9/\-:]+)\s+(up|down|both)\s+([0-9]+(?:\.[0-9]+)?)\s+([A-Za-z0-9]+)\s*$",
        re.IGNORECASE,
    )
    match = pattern.match(text)
    if not match:
        return None
    ticker, direction, threshold, exchange = match.groups()
    try:
        threshold = float(threshold)
    except ValueError:
        return None
    # Нормализуем тикер к формату ccxt (BASE/QUOTE), убираем суффикс после : (для фьючерсов)
    ticker = normalize_symbol(ticker)
    return ticker.upper(), direction.lower(), threshold, exchange.lower()


@router.message(Command("add_alert"))
async def cmd_add_alert(message: types.Message) -> None:
    bot = message.bot
    db: Database = bot.db
    exchange_service: ExchangeService = bot.exchange_service

    if not message.text:
        await message.answer("Используйте: /add_alert [тикер] [up/down/both] [процент] [биржа]")
        return

    parsed = parse_alert_command(message.text)
    if not parsed:
        await message.answer(
            "❌ <b>Неверный формат.</b>\n"
            "Используйте: <code>/add_alert ETHUSDT up 0.5 binance</code>\n"
            "Где: тикер, направление (up/down/both), порог в %, биржа (binance/bybit/bit2c).",
            parse_mode="HTML",
        )
        return

    ticker, direction, threshold_percent, exchange_name = parsed

    exists = await exchange_service.validate_symbol(exchange_name, ticker)
    if not exists:
        await message.answer(
            f"❌ Пара <b>{ticker}</b> не найдена на бирже <b>{exchange_name}</b>.",
            parse_mode="HTML",
        )
        return

    price = await exchange_service.fetch_ticker(exchange_name, ticker)
    if price is None:
        await message.answer(
            f"⚠️ Не удалось получить текущую цену для <b>{ticker}</b>. Подписка не создана.",
            parse_mode="HTML",
        )
        return

    await db.add_alert(message.from_user.id, ticker, threshold_percent, exchange_name, price, direction)

    direction_text = {"up": "📈 Рост", "down": "📉 Падение", "both": "📊 Любое изменение"}.get(direction, direction)
    await message.answer(
        f"✅ <b>Алерт добавлен!</b>\n"
        f"Тикер: <b>{ticker}</b>\n"
        f"Биржа: <b>{exchange_name}</b>\n"
        f"Направление: <b>{direction_text}</b>\n"
        f"Порог: <b>{threshold_percent}%</b>\n"
        f"Базовая цена: <b>${price:,.2f}</b>",
        parse_mode="HTML",
    )


@router.message(Command("my_alerts"))
async def cmd_my_alerts(message: types.Message) -> None:
    db: Database = message.bot.db
    alerts = await db.get_active_alerts(message.from_user.id)
    if not alerts:
        await message.answer("У вас нет активных подписок. Добавьте через /add_alert.")
        return

    direction_text = {"up": "📈 Рост", "down": "📉 Падение", "both": "📊 Любое"}
    lines = ["📋 <b>Ваши активные подписки:</b>\n"]
    for alert_id, ticker, threshold, exchange, base_price, is_active, direction in alerts:
        d_text = direction_text.get(direction, direction)
        lines.append(
            f"<b>ID {alert_id}</b>: {ticker} на {exchange.upper()} "
            f"[{d_text}] порог {threshold}% | база ${base_price:,.2f}\n"
            f"Удалить: <code>/delete_alert {alert_id}</code>\n"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("delete_alert"))
async def cmd_delete_alert(message: types.Message) -> None:
    db: Database = message.bot.db

    if not message.text:
        await message.answer("Используйте: /delete_alert <id>")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Используйте: <code>/delete_alert <id></code>", parse_mode="HTML")
        return

    try:
        alert_id = int(parts[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом.", parse_mode="HTML")
        return

    alert = await db.get_alert_by_id(alert_id)
    if alert is None or alert[1] != message.from_user.id:
        await message.answer("❌ Подписка с таким ID не найдена.", parse_mode="HTML")
        return

    await db.delete_alert(alert_id)
    await message.answer(f"🗑 Подписка <b>ID {alert_id}</b> удалена.", parse_mode="HTML")


@router.message(Command("symbols"))
async def cmd_symbols(message: types.Message) -> None:
    """Показывает доступные торговые пары на бирже.
    Использование: /symbols [биржа] [фильтр1, фильтр2, ...]
    Примеры:
      /symbols binance
      /symbols kraken ETH
      /symbols bybit USDT
      /symbols kraken eth, usd
    """
    exchange_service: ExchangeService = message.bot.exchange_service

    if not message.text:
        await message.answer("Используйте: /symbols [биржа] [фильтр1, фильтр2, ...]")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Используйте: <code>/symbols binance ETH</code>", parse_mode="HTML")
        return

    exchange_name = parts[1].lower()
    search_filter = parts[2].upper() if len(parts) > 2 else ""

    try:
        exchange = exchange_service._get_exchange(exchange_name)
        if not exchange.markets:
            await exchange.load_markets()
    except Exception as e:
        await message.answer(f"❌ Биржа <b>{exchange_name}</b> не поддерживается или недоступна.", parse_mode="HTML")
        return

    all_symbols = list(exchange.markets.keys())

    if search_filter:
        # Поддержка нескольких фильтров через запятую (И-логика: все фильтры должны совпадать)
        filters = [f.strip() for f in search_filter.split(",")]
        filtered = [s for s in all_symbols if all(f in s.upper() for f in filters)]
    else:
        filtered = all_symbols

    if not filtered:
        await message.answer(f"🔍 На бирже <b>{exchange_name}</b> нет пар, содержащих '<b>{search_filter}</b>'.", parse_mode="HTML")
        return

    limit = 50
    displayed = filtered[:limit]

    lines = [
        f"📊 <b>Пары на {exchange_name.upper()}</b>"
        f"{f' (фильтр: {search_filter})' if search_filter else ''}:"
        f" (показано {len(displayed)} из {len(filtered)})\n"
    ]

    for sym in displayed:
        lines.append(f"<code>{sym}</code>")

    if len(filtered) > limit:
        lines.append(f"\n... и ещё {len(filtered) - limit} пар. Уточните фильтр.")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("exchanges"))
async def cmd_exchanges(message: types.Message) -> None:
    """Показывает список всех доступных бирж с пагинацией и поиском.
    Использование: /exchanges [поиск] [страница]
    Примеры:
      /exchanges
      /exchanges 2
      /exchanges bit
      /exchanges bit 2
      /exchanges kraken
    """
    if not message.text:
        await message.answer("Используйте: /exchanges [поиск] [страница]")
        return

    parts = message.text.split()
    search = ""
    page = 1

    # Parse arguments: /exchanges [search] [page]
    if len(parts) > 1:
        # Check if last part is a number (page)
        try:
            page = int(parts[-1])
            if page < 1:
                page = 1
            # If there's a middle part, it's the search term
            if len(parts) > 2:
                search = parts[1].lower()
        except ValueError:
            # Last part is not a number, treat as search
            search = parts[1].lower()

    all_exchanges = get_all_exchanges()

    # Apply search filter
    if search:
        filtered = [ex for ex in all_exchanges if search in ex.lower()]
    else:
        filtered = all_exchanges

    per_page = 20
    total_pages = (len(filtered) + per_page - 1) // per_page

    if page > total_pages:
        page = total_pages if total_pages > 0 else 1

    start = (page - 1) * per_page
    end = start + per_page
    displayed = filtered[start:end]

    lines = [
        f"🏪 <b>Доступные биржи (через ccxt)</b>",
    ]
    if search:
        lines.append(f"Поиск: <code>{search}</code> — найдено {len(filtered)} из {len(all_exchanges)}")
    lines.append(f"Страница {page} из {total_pages}:\n")

    for i, ex in enumerate(displayed, start=start + 1):
        lines.append(f"{i}. <code>{ex}</code>")

    if total_pages > 1:
        # Build next page command
        next_page = page + 1 if page < total_pages else 1
        if search:
            lines.append(f"\nИспользуйте: <code>/exchanges {search} {next_page}</code> для следующей страницы")
        else:
            lines.append(f"\nИспользуйте: <code>/exchanges {next_page}</code> для следующей страницы")

    await message.answer("\n".join(lines), parse_mode="HTML")