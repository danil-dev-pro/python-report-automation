# 🤖 ServiceBot — Telegram Order Management Bot

A production-ready Telegram bot built with **python-telegram-bot 20.x** and **SQLite**.  
Customers can browse services, submit orders, and read FAQs.  
Administrators can review orders, export them to CSV, broadcast messages, and view statistics.

---

## ✨ Features

### User-Facing
| Feature | Description |
|---------|-------------|
| `/start` | Welcome message with an inline menu |
| Consultation | Info about free consultations |
| Place an Order | Multi-step form with name / email / phone / description validation |
| FAQ | Frequently asked questions |
| Contacts | Company contact details |

### Admin Panel (`/admin`)
| Feature | Description |
|---------|-------------|
| Password-protected access | Hardcoded password in `config/settings.py` |
| View Orders | Browse all submitted orders |
| Export CSV | Download orders as a `.csv` file |
| Broadcast | Send a message to every registered user |
| Statistics | Users count, orders today / this week |

### Technical
- **SQLite** database with automatic initialization
- **Rate limiting** — max 5 messages per minute per user
- **Logging** — all actions written to `bot.log`
- **Error handling** — graceful `try/except` wrappers
- Clean modular structure

---

## 📁 Project Structure

```
telegram_bot/
├── config/
│   ├── __init__.py
│   └── settings.py          # All settings & constants
├── database/
│   ├── __init__.py
│   └── db.py                # SQLite async helpers
├── handlers/
│   ├── __init__.py
│   ├── user.py              # User-facing handlers
│   └── admin.py             # Admin panel handlers
├── data/
│   └── bot.db               # SQLite database (auto-created)
├── main.py                  # Entry point
├── .env                     # Your secrets (not committed)
├── .env.example             # Template for .env
├── requirements.txt
├── bot.log                  # Log file (auto-created)
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/yourname/service-bot.git
cd service-bot/telegram_bot
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
```
Open `.env` and fill in:
- `BOT_TOKEN` — obtain from [@BotFather](https://t.me/BotFather)
- `ADMIN_CHAT_ID` — your Telegram user ID (use [@userinfobot](https://t.me/userinfobot))

### 5. Run the bot
```bash
python main.py
```

The bot will automatically create the `data/` directory and the SQLite database on first launch.

---

## 🔑 Admin Access

1. Send `/admin` to the bot.
2. Enter the password defined in `config/settings.py` (`ADMIN_PASSWORD`).
3. Use the inline buttons to manage orders and users.

> **Tip:** Change the default password before deploying to production.

---

## 🛡️ Rate Limiting

Each user is limited to **5 messages per 60 seconds**.  
If the limit is exceeded, the bot replies with a cooldown notice and ignores further input until the window resets.

---

## 📄 License

MIT © 2024
