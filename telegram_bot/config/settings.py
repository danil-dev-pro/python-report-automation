"""
Application settings and constants.

Loads sensitive data from .env file and defines
all configuration variables used across the bot.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ──────────────────────────────────────────────
# Load .env from the project root
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ──────────────────────────────────────────────
# Telegram
# ──────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))

# ──────────────────────────────────────────────
# Admin panel password (hardcoded as requested)
# ──────────────────────────────────────────────
ADMIN_PASSWORD: str = "admin2024secure"

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
DATABASE_PATH: str = str(BASE_DIR / "data" / "bot.db")

# ──────────────────────────────────────────────
# Rate limiting
# ──────────────────────────────────────────────
RATE_LIMIT_MESSAGES: int = 5          # max messages
RATE_LIMIT_WINDOW_SECONDS: int = 60   # per this many seconds

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
LOG_FILE: str = str(BASE_DIR / "bot.log")
LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# ──────────────────────────────────────────────
# Conversation state IDs
# ──────────────────────────────────────────────
(
    STATE_ORDER_NAME,
    STATE_ORDER_EMAIL,
    STATE_ORDER_PHONE,
    STATE_ORDER_DESCRIPTION,
    STATE_ADMIN_PASSWORD,
    STATE_BROADCAST_MESSAGE,
) = range(6)

# ──────────────────────────────────────────────
# UI texts (English)
# ──────────────────────────────────────────────
TEXTS = {
    "welcome": (
        "👋 <b>Welcome to ServiceBot!</b>\n\n"
        "I can help you book a consultation, place a service order, "
        "answer frequently asked questions, or share our contact details.\n\n"
        "Choose an option below to get started:"
    ),
    "consultation": (
        "📋 <b>Consultation</b>\n\n"
        "We offer free 30-minute consultations to discuss your project.\n\n"
        "To book one, tap <b>Place an Order</b> and describe what you need — "
        "our team will get back to you within 24 hours."
    ),
    "faq": (
        "❓ <b>Frequently Asked Questions</b>\n\n"
        "1️⃣ <b>How long does a typical project take?</b>\n"
        "→ Most projects are completed within 2–4 weeks.\n\n"
        "2️⃣ <b>What payment methods do you accept?</b>\n"
        "→ Bank transfer, PayPal, and major credit cards.\n\n"
        "3️⃣ <b>Do you offer revisions?</b>\n"
        "→ Yes — every package includes 2 free revision rounds.\n\n"
        "4️⃣ <b>Can I cancel my order?</b>\n"
        "→ Orders can be cancelled within 24 hours of placement."
    ),
    "contacts": (
        "📞 <b>Contact Us</b>\n\n"
        "🌐 Website: <a href='https://example.com'>example.com</a>\n"
        "📧 Email: support@example.com\n"
        "📱 Phone: +1 (555) 123-4567\n"
        "🕐 Working hours: Mon–Fri, 9 AM – 6 PM (UTC)"
    ),
    "order_start": "📝 Let's create your order!\n\nPlease enter your <b>full name</b>:",
    "order_email": "Great! Now enter your <b>email address</b>:",
    "order_phone": "Enter your <b>phone number</b> (international format, e.g. +1234567890):",
    "order_description": "Finally, <b>describe your task</b> in a few sentences:",
    "order_success": (
        "✅ <b>Order submitted successfully!</b>\n\n"
        "Order #{order_id}\n"
        "Our team will review it and contact you shortly.\n\n"
        "Thank you for choosing us!"
    ),
    "order_cancelled": "❌ Order cancelled. You can start a new one anytime from the menu.",
    "validation_name": "⚠️ Name must be 2–100 characters and contain only letters and spaces. Try again:",
    "validation_email": "⚠️ Please enter a valid email address (e.g. user@example.com):",
    "validation_phone": "⚠️ Please enter a valid phone number in international format (e.g. +1234567890):",
    "admin_prompt": "🔐 Enter the admin password:",
    "admin_wrong_password": "❌ Wrong password. Access denied.",
    "admin_welcome": (
        "🛠 <b>Admin Panel</b>\n\n"
        "Choose an action:"
    ),
    "broadcast_prompt": "📢 Enter the message to broadcast to all users:",
    "broadcast_done": "✅ Broadcast sent to {count} user(s).",
    "rate_limited": "⏳ You're sending messages too fast. Please wait a moment.",
}
