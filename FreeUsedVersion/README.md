# FreeUsedVersion - Бот для мониторинга цен криптовалют

Упрощённая версия бота без системы админов и ключей доступа.

## Возможности

- `/add_alert` — создать алерт на изменение цены
- `/my_alerts` — список активных алертов
- `/delete_alert <id>` — удалить алерт
- `/symbols [биржа] [фильтры]` — список торговых пар
- `/exchanges [поиск] [страница]` — список доступных бирж

## Установка

```bash
# 1. Создайте виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# 2. Установите зависимости
pip install -r requirements.txt

# 3. Настройте .env файл
echo "TELEGRAM_TOKEN=your_token_here" > .env

# 4. Запустите
python main.py
```

## Требования

См. `requirements.txt`:
- aiogram 3.x
- aiohttp
- apscheduler
- ccxt
- aiosqlite
- python-dotenv

## Структура

```
FreeUsedVersion/
├── main.py                 # Точка входа
├── config.py               # Конфигурация
├── database.py             # База данных (только алерты)
├── handlers/
│   ├── start.py            # /start, /help
│   ├── alerts.py           # /add_alert, /my_alerts, /symbols, /exchanges
│   └── __init__.py
├── services/
│   ├── exchange.py         # Работа с биржами через ccxt
│   ├── monitor.py          # Фоновый мониторинг цен
│   └── __init__.py
└── requirements.txt
```

## Особенности

- ✅ Поддержка фьючерсов (суффикс `:USDT` для APEX и др.)
- ✅ Поддержка бирж с цифрами в названии (bit2c, bitmex и т.д.)
- ✅ Множественные фильтры для `/symbols` (И-логика)
- ✅ Поиск и пагинация для `/exchanges`
- ✅ Точные уведомления (до 0.0001%)
- ✅ Автообновление базовой цены после срабатывания