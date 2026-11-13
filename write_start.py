lt_entity = chr(38) + "lt;"
gt_entity = chr(38) + "gt;"

content = '''from aiogram import Router, types
from aiogram.filters import CommandStart, Command

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message) -> None:
    text = (
        "👋 <b>Привет!</b> Я бот для мониторинга цен криптовалют.\\n\\n"
        "📋 <b>Доступные команды:</b>\\n"
        "/add_alert [тикер] [процент] [биржа] — добавить алерт\\n"
        "   Пример: /add_alert BTCUSDT 0.5 binance\\n"
        "/my_alerts — список ваших активных подписок\\n"
        "/delete_alert <code>''' + lt_entity + '''id''' + gt_entity + '''</code> — удалить подписку по ID\\n\\n"
        "🔧 <b>Поддерживаемые биржи:</b> binance, bybit (и другие через ccxt)\\n"
        "⚡ Проверка цен каждую минуту."
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    await cmd_start(message)
'''

with open('handlers/start.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')