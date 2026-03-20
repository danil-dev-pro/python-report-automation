# 🤖 ServiceBot — Production Telegram Bot

A fully-featured, production-ready Telegram bot for managing service orders,
built with **python-telegram-bot 20.x** (async/await), **aiosqlite**, and **SQLite**.

---

## ✨ Features

### 👤 User Panel
| Feature | Description |
|---------|-------------|
| `/start` | Welcome message with 2×2 inline menu |
| 💼 Consultation | Service catalog with pricing |
| 📋 Order Service | 4-step form with live validation |
| ❓ FAQ | 5 Q&A pairs |
| 📬 Contacts | Email, Telegram, WhatsApp, website |

### 🔐 Admin Panel (`/admin`)
| Feature | Description |
|---------|-------------|
| Password login | Hardcoded password, auto-deletes password message |
| 📋 All Orders | Paginated viewer (5 per page) with navigation |
| 📊 Statistics | Users & orders by day / week / month / all-time |
| 📤 Export CSV | Download all orders as timestamped `.csv` |
| 📣 Broadcast | Send HTML message to all registered users |
| 🚪 Logout | Clears admin session |

### 🛡️ Production-Ready
- Rate limiting: 5 messages / 60 seconds per user (sliding window)
- Rotating log file (`logs/bot.log`, max 5 MB × 3 backups)
- Global error handler with admin notification
- Graceful shutdown (SIGINT / SIGTERM)
- WAL-mode SQLite for concurrent reads
- Input validation: name, email (regex), phone (E.164), description length

---

## 📁 Project Structure

```
telegram-bot/
├── main.py                  # Entry point
├── requirements.txt
├── .env.example             # Environment variable template
├── README.md
│
├── config/
│   ├── __init__.py
│   └── settings.py          # All constants, states, UI texts
│
├── database/
│   ├── __init__.py
│   └── db.py                # Async SQLite CRUD manager
│
├── handlers/
│   ├── __init__.py
│   ├── user.py              # User commands, menu, order form
│   └── admin.py             # Admin panel, stats, CSV, broadcast
│
├── data/
│   └── bot.db               # SQLite database (auto-created)
│
└── logs/
    └── bot.log              # Rotating log file (auto-created)
```

---

## 🚀 Quick Start

### 1. Clone & install dependencies
```bash
git clone https://github.com/yourname/telegram-bot.git
cd telegram-bot

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
nano .env                       # Fill in BOT_TOKEN and ADMIN_CHAT_ID
```

### 3. Run the bot
```bash
python main.py
```

The database and log file are created automatically on first run.

---

## ⚙️ Configuration

All settings are in `config/settings.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `ADMIN_PASSWORD` | `admin2024secure` | Admin panel password |
| `RATE_LIMIT_MSG` | `5` | Max messages per window |
| `RATE_LIMIT_SEC` | `60` | Rate limit window (seconds) |
| `DB_PATH` | `data/bot.db` | SQLite database path |
| `LOG_FILE` | `logs/bot.log` | Log file path |

---

## 🗄️ Database Schema

### `users`
| Column | Type | Notes |
|--------|------|-------|
| `user_id` | INTEGER PK | Telegram user ID |
| `username` | TEXT | @username |
| `first_name` | TEXT | — |
| `last_name` | TEXT | — |
| `joined_at` | TEXT | Auto UTC timestamp |

### `orders`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `user_id` | INTEGER FK | → users |
| `name` | TEXT | Validated |
| `email` | TEXT | Regex validated |
| `phone` | TEXT | E.164 validated |
| `description` | TEXT | Min 10 chars |
| `status` | TEXT | Default `new` |
| `created_at` | TEXT | Auto UTC timestamp |

---

## 🔒 Security Notes

- The admin password message is **automatically deleted** after submission
- Wrong password attempts are logged with user ID and username
- After 3 wrong attempts, the session is terminated
- All user IDs are stored in SQLite (no plain-text files)
- Bot token is loaded from `.env` — never hardcoded
- Rate limiting prevents spam and brute-force

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `python-telegram-bot` | 20.7 | Async Telegram API |
| `aiosqlite` | 0.19.0 | Async SQLite driver |
| `python-dotenv` | 1.0.0 | `.env` file loader |

---

## 🧪 Admin Usage

1. Open the bot and send `/admin`
2. Enter the password: `admin2024secure`
3. Use the inline panel to manage orders, view stats, export CSV, or broadcast

> 💡 **Tip:** Set `ADMIN_CHAT_ID` in `.env` to receive instant notifications for every new order.

---

## 📄 License

MIT License — free to use and modify for commercial projects.
