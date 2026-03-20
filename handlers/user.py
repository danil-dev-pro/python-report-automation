"""
handlers/user.py — All user-facing Telegram handlers.

Includes:
- /start command with inline menu
- Menu callbacks: Consultation, Order, FAQ, Contacts
- ConversationHandler for the 4-step order form (with validation)
- Rate limiting via sliding-window algorithm
"""

import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import settings
from database import Database

logger = logging.getLogger(__name__)

# ── Rate-limit store: user_id → list[timestamp] ────────────────────────────────
_rate_store: Dict[int, List[datetime]] = defaultdict(list)


# ══════════════════════════════════════════════════════════════════════════════
#  RATE LIMITING
# ══════════════════════════════════════════════════════════════════════════════

def _is_rate_limited(user_id: int) -> bool:
    """
    Sliding-window rate limiter.

    Keeps a list of timestamps for each user. Prunes old entries outside the
    current window, then checks if the message count exceeds the threshold.

    Args:
        user_id (int): Telegram user ID to check.

    Returns:
        bool: True if the user has exceeded the rate limit, False otherwise.
    """
    now = datetime.utcnow()
    window_start = now.timestamp() - settings.RATE_LIMIT_SEC
    timestamps = _rate_store[user_id]

    # Remove expired timestamps
    _rate_store[user_id] = [t for t in timestamps if t.timestamp() > window_start]

    if len(_rate_store[user_id]) >= settings.RATE_LIMIT_MSG:
        logger.warning("Rate limit hit for user %s", user_id)
        return True

    _rate_store[user_id].append(now)
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════════════════════════════

def _main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Build the main menu 2×2 inline keyboard.

    Returns:
        InlineKeyboardMarkup: The four-button main menu.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💼 Consultation",  callback_data="menu_consultation"),
            InlineKeyboardButton("📋 Order Service", callback_data="menu_order"),
        ],
        [
            InlineKeyboardButton("❓ FAQ",       callback_data="menu_faq"),
            InlineKeyboardButton("📬 Contacts",  callback_data="menu_contacts"),
        ],
    ])


def _back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Build a single 'Back to Menu' inline keyboard.

    Returns:
        InlineKeyboardMarkup: One-button keyboard.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="menu_back")]
    ])


def _order_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Build a cancel keyboard shown during order form steps.

    Returns:
        InlineKeyboardMarkup: One-button cancel keyboard.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel Order", callback_data="order_cancel")]
    ])


# ══════════════════════════════════════════════════════════════════════════════
#  VALIDATION HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _valid_name(text: str) -> bool:
    """
    Validate a person's full name.

    Rules: letters (any language), spaces, hyphens; min 2 characters.

    Args:
        text (str): Raw user input.

    Returns:
        bool: True if valid.
    """
    return bool(re.match(r"^[\w\s\-]{2,}$", text.strip(), re.UNICODE))


def _valid_email(text: str) -> bool:
    """
    Validate an email address using a robust regex pattern.

    Args:
        text (str): Raw user input.

    Returns:
        bool: True if valid.
    """
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, text.strip()))


def _valid_phone(text: str) -> bool:
    """
    Validate an international phone number.

    Rules: optional leading '+', 7–20 digits.

    Args:
        text (str): Raw user input.

    Returns:
        bool: True if valid.
    """
    cleaned = re.sub(r"[\s\-\(\)]", "", text.strip())
    return bool(re.match(r"^\+?\d{7,20}$", cleaned))


# ══════════════════════════════════════════════════════════════════════════════
#  COMMAND HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.

    Upserts the user into the database, applies rate limiting,
    and sends the welcome message with the main menu keyboard.

    Args:
        update  : Incoming Telegram update.
        context : PTB callback context containing bot_data (db).
    """
    user = update.effective_user
    if _is_rate_limited(user.id):
        await update.message.reply_text(settings.TEXTS["rate_limit"])
        return

    db: Database = context.bot_data["db"]
    try:
        await db.upsert_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
    except Exception as exc:
        logger.error("Failed to upsert user %s: %s", user.id, exc)

    logger.info("User %s (%s) triggered /start", user.id, user.username)

    await update.message.reply_text(
        text=settings.TEXTS["welcome"],
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  MENU CALLBACK HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

async def cb_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle 'Consultation' menu button callback.

    Edits the current message to display consultation information.

    Args:
        update  : Incoming Telegram update containing callback query.
        context : PTB callback context.
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text=settings.TEXTS["consultation"],
        parse_mode="HTML",
        reply_markup=_back_to_menu_keyboard(),
    )


async def cb_faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle 'FAQ' menu button callback.

    Displays frequently asked questions.

    Args:
        update  : Incoming Telegram update containing callback query.
        context : PTB callback context.
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text=settings.TEXTS["faq"],
        parse_mode="HTML",
        reply_markup=_back_to_menu_keyboard(),
    )


async def cb_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle 'Contacts' menu button callback.

    Displays contact information.

    Args:
        update  : Incoming Telegram update containing callback query.
        context : PTB callback context.
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text=settings.TEXTS["contacts"],
        parse_mode="HTML",
        reply_markup=_back_to_menu_keyboard(),
    )


async def cb_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle 'Back to Menu' callback — restores the welcome message.

    Args:
        update  : Incoming Telegram update containing callback query.
        context : PTB callback context.
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text=settings.TEXTS["welcome"],
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ORDER CONVERSATION HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point for the order ConversationHandler.

    Triggered by the 'Order Service' menu button. Clears any previous
    order data from user_data and asks for the user's name.

    Args:
        update  : Incoming Telegram update containing callback query.
        context : PTB callback context.

    Returns:
        int: Next conversation state (ASK_NAME).
    """
    query = update.callback_query
    await query.answer()

    # Clear leftover data from previous incomplete orders
    context.user_data.pop("order", None)

    await query.edit_message_text(
        text=settings.TEXTS["order_start"],
        parse_mode="HTML",
        reply_markup=_order_cancel_keyboard(),
    )
    return settings.ASK_NAME


async def ask_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle the user's name input (Step 1 of 4).

    Validates the name and either advances to ASK_EMAIL or asks again.

    Args:
        update  : Incoming Telegram update with text message.
        context : PTB callback context.

    Returns:
        int: ASK_EMAIL on success, ASK_NAME on validation failure.
    """
    user = update.effective_user
    if _is_rate_limited(user.id):
        await update.message.reply_text(settings.TEXTS["rate_limit"])
        return settings.ASK_NAME

    text = update.message.text.strip()
    if not _valid_name(text):
        await update.message.reply_text(
            settings.TEXTS["err_name"],
            reply_markup=_order_cancel_keyboard(),
        )
        return settings.ASK_NAME

    context.user_data.setdefault("order", {})["name"] = text
    await update.message.reply_text(
        settings.TEXTS["ask_email"],
        parse_mode="HTML",
        reply_markup=_order_cancel_keyboard(),
    )
    return settings.ASK_EMAIL


async def ask_email_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle the user's email input (Step 2 of 4).

    Validates the email and either advances to ASK_PHONE or asks again.

    Args:
        update  : Incoming Telegram update with text message.
        context : PTB callback context.

    Returns:
        int: ASK_PHONE on success, ASK_EMAIL on validation failure.
    """
    user = update.effective_user
    if _is_rate_limited(user.id):
        await update.message.reply_text(settings.TEXTS["rate_limit"])
        return settings.ASK_EMAIL

    text = update.message.text.strip()
    if not _valid_email(text):
        await update.message.reply_text(
            settings.TEXTS["err_email"],
            reply_markup=_order_cancel_keyboard(),
        )
        return settings.ASK_EMAIL

    context.user_data["order"]["email"] = text
    await update.message.reply_text(
        settings.TEXTS["ask_phone"],
        parse_mode="HTML",
        reply_markup=_order_cancel_keyboard(),
    )
    return settings.ASK_PHONE


async def ask_phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle the user's phone input (Step 3 of 4).

    Validates the phone number and either advances to ASK_DESCRIPTION or asks again.

    Args:
        update  : Incoming Telegram update with text message.
        context : PTB callback context.

    Returns:
        int: ASK_DESCRIPTION on success, ASK_PHONE on validation failure.
    """
    user = update.effective_user
    if _is_rate_limited(user.id):
        await update.message.reply_text(settings.TEXTS["rate_limit"])
        return settings.ASK_PHONE

    text = update.message.text.strip()
    if not _valid_phone(text):
        await update.message.reply_text(
            settings.TEXTS["err_phone"],
            reply_markup=_order_cancel_keyboard(),
        )
        return settings.ASK_PHONE

    context.user_data["order"]["phone"] = text
    await update.message.reply_text(
        settings.TEXTS["ask_description"],
        parse_mode="HTML",
        reply_markup=_order_cancel_keyboard(),
    )
    return settings.ASK_DESCRIPTION


async def ask_description_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle the task description input (Step 4 of 4).

    Validates the description, saves the order to the database,
    sends a confirmation to the user, and notifies the admin.

    Args:
        update  : Incoming Telegram update with text message.
        context : PTB callback context.

    Returns:
        int: ConversationHandler.END on success, ASK_DESCRIPTION on failure.
    """
    user = update.effective_user
    if _is_rate_limited(user.id):
        await update.message.reply_text(settings.TEXTS["rate_limit"])
        return settings.ASK_DESCRIPTION

    text = update.message.text.strip()
    if len(text) < 10:
        await update.message.reply_text(
            settings.TEXTS["err_description"],
            reply_markup=_order_cancel_keyboard(),
        )
        return settings.ASK_DESCRIPTION

    context.user_data["order"]["description"] = text
    order_data = context.user_data["order"]
    db: Database = context.bot_data["db"]

    try:
        order_id = await db.create_order(
            user_id=user.id,
            name=order_data["name"],
            email=order_data["email"],
            phone=order_data["phone"],
            description=order_data["description"],
        )
    except Exception as exc:
        logger.error("Failed to create order for user %s: %s", user.id, exc)
        await update.message.reply_text(
            "⚠️ Failed to save your order. Please try again later.",
            reply_markup=_back_to_menu_keyboard(),
        )
        return ConversationHandler.END

    # Confirmation to user
    confirm_text = settings.TEXTS["order_confirm"].format(
        order_id=order_id, **order_data
    )
    await update.message.reply_text(
        text=confirm_text,
        parse_mode="HTML",
        reply_markup=_back_to_menu_keyboard(),
    )

    # Notify admin
    if settings.ADMIN_CHAT_ID:
        try:
            admin_text = (
                f"🔔 <b>New Order #{order_id}</b>\n\n"
                f"👤 <b>User:</b> {user.full_name} (<code>{user.id}</code>)\n"
                f"📛 <b>Name:</b> {order_data['name']}\n"
                f"📧 <b>Email:</b> {order_data['email']}\n"
                f"📱 <b>Phone:</b> {order_data['phone']}\n"
                f"📝 <b>Task:</b> {order_data['description']}"
            )
            await context.bot.send_message(
                chat_id=settings.ADMIN_CHAT_ID,
                text=admin_text,
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("Could not notify admin: %s", exc)

    logger.info("Order #%s submitted by user %s", order_id, user.id)
    context.user_data.pop("order", None)
    return ConversationHandler.END


async def order_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle order cancellation (either /cancel command or inline button).

    Clears partial order data and returns to the main menu.

    Args:
        update  : Incoming Telegram update.
        context : PTB callback context.

    Returns:
        int: ConversationHandler.END.
    """
    context.user_data.pop("order", None)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=settings.TEXTS["order_cancelled"],
            reply_markup=_back_to_menu_keyboard(),
        )
    else:
        await update.message.reply_text(
            text=settings.TEXTS["order_cancelled"],
            reply_markup=_back_to_menu_keyboard(),
        )

    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER FACTORY
# ══════════════════════════════════════════════════════════════════════════════

def get_user_handlers(db: Database) -> list:
    """
    Build and return all user-facing handlers.

    Args:
        db (Database): The shared database instance (unused directly here,
                       accessed via context.bot_data["db"] inside handlers).

    Returns:
        list: PTB handler objects to be registered with the Application.
    """
    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(order_start, pattern="^menu_order$")],
        states={
            settings.ASK_NAME:        [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name_received)],
            settings.ASK_EMAIL:       [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email_received)],
            settings.ASK_PHONE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone_received)],
            settings.ASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_description_received)],
        },
        fallbacks=[
            CommandHandler("cancel", order_cancel),
            CallbackQueryHandler(order_cancel, pattern="^order_cancel$"),
        ],
        allow_reentry=True,
    )

    return [
        CommandHandler("start", cmd_start),
        order_conv,
        CallbackQueryHandler(cb_consultation, pattern="^menu_consultation$"),
        CallbackQueryHandler(cb_faq,          pattern="^menu_faq$"),
        CallbackQueryHandler(cb_contacts,     pattern="^menu_contacts$"),
        CallbackQueryHandler(cb_back_to_menu, pattern="^menu_back$"),
    ]
