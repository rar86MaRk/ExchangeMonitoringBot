from aiogram import Router, types
from aiogram.filters import CommandStart, Command

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message) -> None:
    text = (
        "👋 <b>Привет!</b> Я бот для мониторинга цен криптовалют.\n\n"
        "📋 <b>Доступные команды:</b>\n"
        "/add_alert [тикер] [направление] [процент] [биржа] — добавить алерт\n"
        "   <b>Направление:</b> <code>up</code> (рост), <code>down</code> (падение), <code>both</code> (любое)\n"
        "   Примеры:\n"
        "   <code>/add_alert ETHUSDT up 0.5 binance</code> — алерт при росте на 0.5%\n"
        "   <code>/add_alert BTC/USDT down 1.0 bybit</code> — алерт при падении на 1%\n"
        "   <code>/add_alert SOLUSDT both 0.3 binance</code> — алерт при любом изменении на 0.3%\n"
        "   <code>/add_alert BTC/USDT:USDT both 0.001 apex</code> — фьючерсы (суффикс после :)\n"
        "   <code>/add_alert BTC/NIS both 0.001 bit2c</code> — биржи с цифрами в названии\n\n"
        "/my_alerts — список ваших активных подписок\n"
        "/delete_alert <code><id></code> — удалить подписку по ID\n"
        "/symbols [биржа] [<фильтр1>, <фильтр2>, ...] — список пар на бирже (все фильтры должны совпадать)\n"
        "   Пример: <code>/symbols kraken ETH</code>\n"
        "   Пример: <code>/symbols kraken eth, usd</code> — пары, где есть и ETH, и USD\n\n"
        "/exchanges [<поиск>] [<страница>] — список всех доступных бирж (по 20 на странице)\n"
        "   Пример: <code>/exchanges</code>\n"
        "   Пример: <code>/exchanges 2</code>\n"
        "   Пример: <code>/exchanges bit</code> — поиск бирж с 'bit'\n"
        "   Пример: <code>/exchanges kraken 2</code> — страница 2 поиска 'kraken'\n\n"
        "🔧 <b>Поддерживаемые биржи:</b> binance, bybit, kraken, okx, kucoin, apex, bit2c, bingx (и другие через ccxt)\n"
        "💡 <b>Тикеры:</b> ETHUSDT, BTC/USDT, ETH-USDT, BTC/USDT:USDT — все форматы работают\n"
        "⚡ Проверка цен каждую минуту. После срабатывания база обновляется."
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    await cmd_start(message)