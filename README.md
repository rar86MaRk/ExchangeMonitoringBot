# 📊 Exchange Monitoring Bot / Бот для мониторинга цен криптовалют

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![aiogram](https://img.shields.io/badge/aiogram-3.7-blue.svg)](https://docs.aiogram.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🇷🇺 Русская версия

### Описание

**Exchange Monitoring Bot** — это Telegram-бот для мониторинга цен криптовалют на различных биржах. Бот проверяет цены каждую минуту и отправляет уведомления при достижении заданного порога изменения.

### ✨ Возможности

#### Для пользователей:
- 📈 **Создание алертов** — `/add_alert` с поддержкой направлений: рост (`up`), падение (`down`), любое (`both`)
- 📋 **Список алертов** — `/my_alerts` с базовой ценой и порогом
- 🗑 **Удаление алертов** — `/delete_alert <id>`
- 🔍 **Поиск торговых пар** — `/symbols [биржа] [фильтры]` с И-логикой
- 🏪 **Список бирж** — `/exchanges [поиск] [страница]` с пагинацией

#### Для администраторов:
- 👑 **Панель управления** — `/admin`
- 👥 **Список пользователей** — `/users` (роли, статус бана)
- 🔨 **Бан/разбан** — `/ban <user_id>`, `/unban <user_id>`
- 🔑 **Создание ключей** — `/create_key [admin|user]`
- 📋 **Список ключей** — `/keys`
- ♻️ **Отзыв ключей** — `/revoke_key <key_id>`
- 📊 **Статистика** — `/stats`

### 🛠 Технологии

| Компонент | Технология |
|-----------|------------|
| **Язык** | Python 3.10+ |
| **Telegram API** | aiogram 3.x |
| **Биржи** | ccxt (100+ бирж) |
| **База данных** | SQLite (aiosqlite) |
| **Планировщик** | APScheduler |
| **HTTP клиент** | aiohttp |

### 📦 Установка

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/yourusername/ExchangeMonitoringBot.git
cd ExchangeMonitoringBot

# 2. Создайте виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Установите зависимости
pip install -r requirements.txt

# 4. Настройте переменные окружения
cp .env.example .env
# Отредактируйте .env и добавьте TELEGRAM_TOKEN
```

### ⚙️ Конфигурация

Создайте файл `.env`:

```env
TELEGRAM_TOKEN=your_bot_token_here
DATABASE_PATH=data/users.db
CHECK_INTERVAL_SECONDS=60
```

### 🚀 Запуск

```bash
# Обычный запуск
python main.py

# Как systemd сервис (Linux)
sudo cp exchange-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable exchange-bot
sudo systemctl start exchange-bot
sudo journalctl -u exchange-bot -f
```

### 🔑 Система доступа

Бот использует **ключи доступа** (24 случайных символа):

1. **Супер-админ** — первый созданный админский ключ (`created_by=0`)
   - Может банить других админов
   - Нельзя забанить супер-админа

2. **Админ** — может:
   - Банить пользователей
   - Создавать ключи (админ/пользователь)
   - Просматривать всех пользователей и ключи

3. **Пользователь** — обычный функционал бота

#### Создание первого админа:

```bash
python -m scripts.init_admin
# Сохраните показанный ключ!
```

#### Регистрация в боте:
```
/register YOUR_ADMIN_KEY
```

### 📖 Команды

| Команда | Описание | Доступ |
|---------|----------|--------|
| `/start` | Приветствие и справка | Все |
| `/help` | Справка | Все |
| `/register <key>` | Регистрация по ключу | Незарегистрированные |
| `/add_alert` | Создать алерт | Пользователи |
| `/my_alerts` | Мои алерты | Пользователи |
| `/delete_alert <id>` | Удалить алерт | Пользователи |
| `/symbols [биржа] [фильтры]` | Поиск пар | Пользователи |
| `/exchanges [поиск] [стр]` | Список бирж | Пользователи |
| `/admin` | Панель админа | Админы |
| `/users` | Список пользователей | Админы |
| `/ban <id>` | Бан пользователя | Админы* |
| `/unban <id>` | Разбан | Админы |
| `/create_key [admin\|user]` | Создать ключ | Админы |
| `/keys` | Список ключей | Админы |
| `/revoke_key <id>` | Отозвать ключ | Админы |
| `/stats` | Статистика | Админы |

*\* Супер-админ может банить админов, обычный админ — только пользователей*

### 💡 Примеры использования

```bash
# Создать алерт на рост BTC на 0.5% на Binance
/add_alert BTCUSDT up 0.5 binance

# Алерт на падение ETH на 1% на Bybit
/add_alert ETH/USDT down 1.0 bybit

# Алерт на любое изменение SOL на 0.3%
/add_alert SOLUSDT both 0.3 binance

# Фьючерсы на APEX (суффикс :USDT)
/add_alert BTC/USDT:USDT both 0.001 apex

# Биржа с цифрой в названии
/add_alert BTC/NIS both 0.001 bit2c

# Поиск пар: и BTC, и USDT
/symbols kraken btc, usdt

# Поиск бирж по "bit"
/exchanges bit

# Страница 2 поиска "kraken"
/exchanges kraken 2
```

### 🏗 Структура проекта

```
ExchangeMonitoringBot/
├── main.py                 # Точка входа
├── config.py               # Конфигурация
├── database.py             # База данных (SQLite + миграции)
├── requirements.txt        # Зависимости
├── .env.example            # Пример конфигурации
├── .gitignore
├── handlers/
│   ├── start.py            # /start, /help, /register
│   ├── alerts.py           # /add_alert, /my_alerts, /symbols, /exchanges
│   ├── admin.py            # Админ-команды
│   └── __init__.py
├── services/
│   ├── exchange.py         # Работа с биржами через ccxt
│   ├── monitor.py          # Фоновый мониторинг цен
│   └── __init__.py
├── middlewares/
│   └── access.py           # Контроль доступа
├── scripts/
│   └── init_admin.py       # Создание первого админа
├── data/                   # База данных (создается автоматически)
└── FreeUsedVersion/        # Упрощённая версия без админки
```

### 🔧 Особенности реализации

- **Поддержка фьючерсов** — суффикс `:USDT` для APEX и других
- **Биржи с цифрами** — bit2c, bitmex, bybit и др.
- **Множественные фильтры** — `/symbols kraken btc, usd` (И-логика)
- **Точные уведомления** — до 4 знаков после запятой (0.0001%)
- **Автообновление базы** — после срабатывания новая базовая цена
- **Миграции БД** — автоматическое добавление колонок
- **HTML-парсинг** — экранирование спецсимволов

### 📄 Лицензия

MIT License — см. файл [LICENSE](LICENSE)

---

## 🇺🇸 English Version

### Description

**Exchange Monitoring Bot** is a Telegram bot for monitoring cryptocurrency prices across multiple exchanges. The bot checks prices every minute and sends notifications when price changes reach specified thresholds.

### ✨ Features

#### For Users:
- 📈 **Create alerts** — `/add_alert` with directions: up (`up`), down (`down`), both (`both`)
- 📋 **List alerts** — `/my_alerts` with base price and threshold
- 🗑 **Delete alerts** — `/delete_alert <id>`
- 🔍 **Search trading pairs** — `/symbols [exchange] [filters]` with AND-logic
- 🏪 **List exchanges** — `/exchanges [search] [page]` with pagination

#### For Admins:
- 👑 **Admin panel** — `/admin`
- 👥 **User list** — `/users` (roles, ban status)
- 🔨 **Ban/unban** — `/ban <user_id>`, `/unban <user_id>`
- 🔑 **Create keys** — `/create_key [admin|user]`
- 📋 **List keys** — `/keys`
- ♻️ **Revoke keys** — `/revoke_key <key_id>`
- 📊 **Statistics** — `/stats`

### 🛠 Technologies

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.10+ |
| **Telegram API** | aiogram 3.x |
| **Exchanges** | ccxt (100+ exchanges) |
| **Database** | SQLite (aiosqlite) |
| **Scheduler** | APScheduler |
| **HTTP Client** | aiohttp |

### 📦 Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/ExchangeMonitoringBot.git
cd ExchangeMonitoringBot

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add TELEGRAM_TOKEN
```

### ⚙️ Configuration

Create `.env` file:

```env
TELEGRAM_TOKEN=your_bot_token_here
DATABASE_PATH=data/users.db
CHECK_INTERVAL_SECONDS=60
```

### 🚀 Running

```bash
# Direct run
python main.py

# As systemd service (Linux)
sudo cp exchange-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable exchange-bot
sudo systemctl start exchange-bot
sudo journalctl -u exchange-bot -f
```

### 🔑 Access System

Bot uses **access keys** (24 random characters):

1. **Super-admin** — first created admin key (`created_by=0`)
   - Can ban other admins
   - Cannot be banned

2. **Admin** — can:
   - Ban users
   - Create keys (admin/user)
   - View all users and keys

3. **User** — standard bot functionality

#### Create first admin:

```bash
python -m scripts.init_admin
# Save the displayed key!
```

#### Register in bot:
```
/register YOUR_ADMIN_KEY
```

### 📖 Commands

| Command | Description | Access |
|---------|-------------|--------|
| `/start` | Welcome and help | All |
| `/help` | Help | All |
| `/register <key>` | Register with key | Unregistered |
| `/add_alert` | Create alert | Users |
| `/my_alerts` | My alerts | Users |
| `/delete_alert <id>` | Delete alert | Users |
| `/symbols [exch] [filters]` | Search pairs | Users |
| `/exchanges [search] [page]` | List exchanges | Users |
| `/admin` | Admin panel | Admins |
| `/users` | User list | Admins |
| `/ban <id>` | Ban user | Admins* |
| `/unban <id>` | Unban | Admins |
| `/create_key [admin\|user]` | Create key | Admins |
| `/keys` | List keys | Admins |
| `/revoke_key <id>` | Revoke key | Admins |
| `/stats` | Statistics | Admins |

*\* Super-admin can ban admins, regular admin — only users*

### 💡 Usage Examples

```bash
# Alert on BTC rise 0.5% on Binance
/add_alert BTCUSDT up 0.5 binance

# Alert on ETH fall 1% on Bybit
/add_alert ETH/USDT down 1.0 bybit

# Alert on any SOL change 0.3%
/add_alert SOLUSDT both 0.3 binance

# Futures on APEX (:USDT suffix)
/add_alert BTC/USDT:USDT both 0.001 apex

# Exchange with digit in name
/add_alert BTC/NIS both 0.001 bit2c

# Search pairs: both BTC AND USDT
/symbols kraken btc, usdt

# Search exchanges with "bit"
/exchanges bit

# Page 2 of "kraken" search
/exchanges kraken 2
```

### 🏗 Project Structure

```
ExchangeMonitoringBot/
├── main.py                 # Entry point
├── config.py               # Configuration
├── database.py             # Database (SQLite + migrations)
├── requirements.txt        # Dependencies
├── .env.example            # Config example
├── .gitignore
├── handlers/
│   ├── start.py            # /start, /help, /register
│   ├── alerts.py           # /add_alert, /my_alerts, /symbols, /exchanges
│   ├── admin.py            # Admin commands
│   └── __init__.py
├── services/
│   ├── exchange.py         # Exchange integration via ccxt
│   ├── monitor.py          # Background price monitoring
│   └── __init__.py
├── middlewares/
│   └── access.py           # Access control
├── scripts/
│   └── init_admin.py       # First admin creation
├── data/                   # Database (auto-created)
└── FreeUsedVersion/        # Simplified version without admin
```

### 🔧 Implementation Details

- **Futures support** — `:USDT` suffix for APEX and others
- **Digit exchanges** — bit2c, bitmex, bybit, etc.
- **Multiple filters** — `/symbols kraken btc, usd` (AND-logic)
- **Precise alerts** — up to 4 decimal places (0.0001%)
- **Auto base price update** — after trigger, new base price set
- **DB migrations** — automatic column additions
- **HTML parsing** — special character escaping

### 📄 License

MIT License — see [LICENSE](LICENSE) file

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📞 Support

- Create an [Issue](https://github.com/yourusername/ExchangeMonitoringBot/issues)
- Check [Wiki](https://github.com/yourusername/ExchangeMonitoringBot/wiki) for docs

---

<div align="center">
<b>Made with ❤️ for crypto traders</b>
</div>