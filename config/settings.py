"""
config/settings.py — Centralised configuration for the Telegram bot.

All constants, conversation states, UI strings, and environment-variable
loading live here so every other module can import from a single source
of truth.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

load_dotenv()

# ── Base directories ───────────────────────────────────────────────────────────
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
LOGS_DIR: Path = BASE_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SETTINGS DATACLASS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Settings:
    """
    Immutable settings object loaded once at import time.

    Attributes:
        BOT_TOKEN       : Telegram Bot API token from @BotFather.
        ADMIN_CHAT_ID   : Telegram chat ID for admin notifications.
        ADMIN_PASSWORD  : Hardcoded admin panel password.
        DB_PATH         : Absolute path to the SQLite database file.
        LOG_FILE        : Absolute path to the rotating log file.
        RATE_LIMIT_MSG  : Max messages allowed per rate window per user.
        RATE_LIMIT_SEC  : Duration (seconds) of the rate-limit window.
        TEXTS           : All user-facing UI strings.
        STATE_*         : Integer conversation state constants.
    """

    # ── Secrets ────────────────────────────────────────────────────────────────
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE"))
    ADMIN_CHAT_ID: str = field(default_factory=lambda: os.getenv("ADMIN_CHAT_ID", ""))

    # ── Admin credentials ──────────────────────────────────────────────────────
    ADMIN_PASSWORD: str = "admin2024secure"

    # ── Paths ──────────────────────────────────────────────────────────────────
    DB_PATH: str = field(default_factory=lambda: str(DATA_DIR / "bot.db"))
    LOG_FILE: str = field(default_factory=lambda: str(LOGS_DIR / "bot.log"))

    # ── Rate limiting ──────────────────────────────────────────────────────────
    RATE_LIMIT_MSG: int = 5    # max messages
    RATE_LIMIT_SEC: int = 60   # per N seconds

    # ── ConversationHandler states ─────────────────────────────────────────────
    # Order flow
    ASK_NAME: int = 0
    ASK_EMAIL: int = 1
    ASK_PHONE: int = 2
    ASK_DESCRIPTION: int = 3

    # Admin flow
    ADMIN_WAIT_PASSWORD: int = 10
    ADMIN_WAIT_BROADCAST: int = 11

    # ── UI Texts ───────────────────────────────────────────────────────────────
    TEXTS: Dict[str, str] = field(default_factory=lambda: {

        # ── /start ────────────────────────────────────────────────────────────
        "welcome": (
            "👋 <b>Welcome to ServiceBot!</b>\n\n"
            "We provide professional digital services:\n"
            "• Web & mobile development\n"
            "• Business consulting\n"
            "• Technical support & maintenance\n\n"
            "Choose an option below to get started:"
        ),

        # ── Consultation ──────────────────────────────────────────────────────
        "consultation": (
            "💼 <b>Consultation Services</b>\n\n"
            "Our experts are ready to help you with:\n\n"
            "🔹 <b>Business Analysis</b> — from $150 / session\n"
            "🔹 <b>Technical Audit</b> — from $200 / project\n"
            "🔹 <b>Strategy Planning</b> — from $300 / session\n"
            "🔹 <b>Code Review</b> — from $100 / hour\n\n"
            "📅 Sessions available Mon–Fri, 09:00–18:00 UTC\n\n"
            "Ready to book? Press <b>Order Service</b> below."
        ),

        # ── FAQ ───────────────────────────────────────────────────────────────
        "faq": (
            "❓ <b>Frequently Asked Questions</b>\n\n"
            "<b>Q: How do I place an order?</b>\n"
            "A: Tap 'Order Service', fill in the short form, and we'll reach out within 24 h.\n\n"
            "<b>Q: What payment methods do you accept?</b>\n"
            "A: Bank transfer, PayPal, Stripe, and crypto (USDT/BTC).\n\n"
            "<b>Q: How long does a project take?</b>\n"
            "A: Typical turnaround is 3–14 days depending on scope.\n\n"
            "<b>Q: Do you offer refunds?</b>\n"
            "A: Yes — full refund if work hasn't started; partial after kick-off.\n\n"
            "<b>Q: Can I request revisions?</b>\n"
            "A: Absolutely — 2 free revision rounds are included in every order."
        ),

        # ── Contacts ─────────────────────────────────────────────────────────
        "contacts": (
            "📬 <b>Contact Us</b>\n\n"
            "📧 <b>Email:</b> support@servicebot.io\n"
            "💬 <b>Telegram:</b> @ServiceBotSupport\n"
            "📱 <b>WhatsApp:</b> +1 (555) 000-1234\n"
            "🌐 <b>Website:</b> https://servicebot.io\n\n"
            "🕐 <b>Working hours:</b> Mon–Fri, 09:00–18:00 UTC\n\n"
            "We typically respond within <b>2 business hours</b>."
        ),

        # ── Order flow ────────────────────────────────────────────────────────
        "order_start": (
            "📋 <b>New Order Form</b>\n\n"
            "I'll ask you 4 quick questions.\n"
            "Type /cancel at any time to abort.\n\n"
            "Step 1 of 4 — <b>Your full name:</b>"
        ),
        "ask_email":       "Step 2 of 4 — <b>Your email address:</b>",
        "ask_phone":       "Step 3 of 4 — <b>Your phone number</b> (e.g. +12025550100):",
        "ask_description": "Step 4 of 4 — <b>Describe your task</b> (min 10 characters):",

        "order_confirm": (
            "✅ <b>Order submitted successfully!</b>\n\n"
            "📌 <b>Order #{order_id}</b>\n\n"
            "👤 Name: {name}\n"
            "📧 Email: {email}\n"
            "📱 Phone: {phone}\n"
            "📝 Task: {description}\n\n"
            "Our team will contact you within <b>24 hours</b>. Thank you! 🙏"
        ),
        "order_cancelled": "❌ Order cancelled. Returning to main menu.",

        # ── Validation errors ─────────────────────────────────────────────────
        "err_name":        "⚠️ Please enter your real name (letters only, min 2 characters).",
        "err_email":       "⚠️ Invalid email address. Example: john@example.com",
        "err_phone":       "⚠️ Invalid phone. Use international format: +12025550100",
        "err_description": "⚠️ Description too short. Please provide at least 10 characters.",

        # ── Admin ─────────────────────────────────────────────────────────────
        "admin_welcome":   "🔐 <b>Admin Panel</b>\n\nEnter the admin password:",
        "admin_wrong_pwd": "❌ Wrong password. Access denied.",
        "admin_success":   "✅ Access granted. Welcome, Admin!\n\nChoose an action:",
        "admin_no_orders": "📭 No orders in the database yet.",
        "admin_broadcast_prompt": (
            "📣 <b>Broadcast Message</b>\n\n"
            "Send the message you want to broadcast to all users.\n"
            "HTML formatting is supported.\n\n"
            "Type /cancel to abort."
        ),

        # ── Rate limit ────────────────────────────────────────────────────────
        "rate_limit": "⏳ You're sending messages too fast. Please wait a moment.",
    })


# ── Singleton instance ─────────────────────────────────────────────────────────
settings = Settings()
