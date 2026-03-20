"""
handlers/admin.py — Admin panel Telegram handlers.

Features:
- Password-protected login via /admin command
- Paginated order viewer (5 orders per page)
- Live statistics dashboard
- CSV export sent as a document
- Broadcast message to all users
"""

import io
import logging
from datetime import datetime
from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
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

# Orders displayed per page in the viewer
ORDERS_PER_PAGE = 5


# ══════════════════════════════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════════════════════════════

def _admin_panel_keyboard() -> InlineKeyboardMarkup:
    """
    Build the main admin panel keyboard.

    Returns:
        InlineKeyboardMarkup: Admin action buttons.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 All Orders",  callback_data="admin_orders_0"),
            InlineKeyboardButton("📊 Statistics",  callback_data="admin_stats"),
        ],
        [
            InlineKeyboardButton("📤 Export CSV",  callback_data="admin_export"),
            InlineKeyboardButton("📣 Broadcast",   callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton("🚪 Logout",      callback_data="admin_logout"),
        ],
    ])


def _orders_nav_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """
    Build a pagination keyboard for the order viewer.

    Args:
        page        (int): Current page index (0-based).
        total_pages (int): Total number of pages.

    Returns:
        InlineKeyboardMarkup: Navigation keyboard with prev/next and back buttons.
    """
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"admin_orders_{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"· {page + 1}/{total_pages} ·", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"admin_orders_{page + 1}"))

    return InlineKeyboardMarkup([
        nav_row,
        [InlineKeyboardButton("🔙 Admin Menu", callback_data="admin_back")],
    ])


def _stats_keyboard() -> InlineKeyboardMarkup:
    """
    Build the statistics page keyboard.

    Returns:
        InlineKeyboardMarkup: Refresh and back buttons.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh",     callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 Admin Menu",  callback_data="admin_back")],
    ])


def _back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """Single 'Back to Admin Menu' button."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Admin Menu", callback_data="admin_back")]
    ])


# ══════════════════════════════════════════════════════════════════════════════
#  AUTHENTICATION
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle the /admin command — entry point for the admin panel.

    If the user is already authenticated in this session, jumps straight
    to the admin panel. Otherwise prompts for the password.

    Args:
        update  : Incoming Telegram update.
        context : PTB callback context.

    Returns:
        int: ADMIN_WAIT_PASSWORD state or ConversationHandler.END if already logged in.
    """
    user = update.effective_user
    logger.info("User %s (%s) entered /admin", user.id, user.username)

    if context.user_data.get("is_admin"):
        await update.message.reply_text(
            text="✅ Already logged in.\n\n" + settings.TEXTS["admin_success"],
            parse_mode=ParseMode.HTML,
            reply_markup=_admin_panel_keyboard(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        text=settings.TEXTS["admin_welcome"],
        parse_mode=ParseMode.HTML,
    )
    return settings.ADMIN_WAIT_PASSWORD


async def admin_check_password(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Validate the password entered by the user.

    Increments a wrong-attempt counter and logs suspicious activity.
    Grants access and shows the admin panel on success.

    Args:
        update  : Incoming Telegram update with text message.
        context : PTB callback context.

    Returns:
        int: ConversationHandler.END on success, ADMIN_WAIT_PASSWORD on failure.
    """
    user = update.effective_user
    entered = update.message.text.strip()

    # Delete the message containing the password for security
    try:
        await update.message.delete()
    except Exception:
        pass

    if entered == settings.ADMIN_PASSWORD:
        context.user_data["is_admin"] = True
        context.user_data["wrong_attempts"] = 0
        logger.info("Admin login SUCCESS by user %s (%s)", user.id, user.username)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=settings.TEXTS["admin_success"],
            parse_mode=ParseMode.HTML,
            reply_markup=_admin_panel_keyboard(),
        )
        return ConversationHandler.END

    # Wrong password
    attempts = context.user_data.get("wrong_attempts", 0) + 1
    context.user_data["wrong_attempts"] = attempts
    logger.warning(
        "Admin login FAILED by user %s (%s) — attempt #%d",
        user.id, user.username, attempts
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{settings.TEXTS['admin_wrong_pwd']} (Attempt {attempts}/3)",
        parse_mode=ParseMode.HTML,
    )

    if attempts >= 3:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🚫 Too many wrong attempts. Session terminated.",
        )
        context.user_data["wrong_attempts"] = 0
        return ConversationHandler.END

    return settings.ADMIN_WAIT_PASSWORD


async def admin_logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle logout callback — clears admin session flag.

    Args:
        update  : Incoming Telegram update with callback query.
        context : PTB callback context.
    """
    query = update.callback_query
    await query.answer()
    context.user_data["is_admin"] = False
    logger.info("Admin user %s logged out.", update.effective_user.id)
    await query.edit_message_text("👋 Logged out from admin panel. Bye!")


async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Return to the admin panel main menu.

    Args:
        update  : Incoming Telegram update with callback query.
        context : PTB callback context.
    """
    query = update.callback_query
    await query.answer()

    if not context.user_data.get("is_admin"):
        await query.edit_message_text("🔒 Session expired. Use /admin to log in again.")
        return

    await query.edit_message_text(
        text=settings.TEXTS["admin_success"],
        parse_mode=ParseMode.HTML,
        reply_markup=_admin_panel_keyboard(),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ORDER VIEWER  (paginated)
# ══════════════════════════════════════════════════════════════════════════════

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Display a paginated list of all orders.

    Extracts the page number from the callback_data suffix (e.g. 'admin_orders_2').
    Fetches all orders from the DB and renders the requested page.

    Args:
        update  : Incoming Telegram update with callback query.
        context : PTB callback context.
    """
    query = update.callback_query
    await query.answer()

    if not context.user_data.get("is_admin"):
        await query.edit_message_text("🔒 Session expired. Use /admin to log in again.")
        return

    page = int(query.data.split("_")[-1])
    db: Database = context.bot_data["db"]

    try:
        orders = await db.get_all_orders()
    except Exception as exc:
        logger.error("Failed to fetch orders: %s", exc)
        await query.edit_message_text("⚠️ Failed to load orders.")
        return

    if not orders:
        await query.edit_message_text(
            text=settings.TEXTS["admin_no_orders"],
            reply_markup=_back_to_admin_keyboard(),
        )
        return

    total = len(orders)
    total_pages = max(1, (total + ORDERS_PER_PAGE - 1) // ORDERS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))

    start = page * ORDERS_PER_PAGE
    page_orders = orders[start: start + ORDERS_PER_PAGE]

    lines = [f"📋 <b>Orders ({total} total) — Page {page + 1}/{total_pages}</b>\n"]
    for order in page_orders:
        lines.append(
            f"━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>#{order['id']}</b> | {order['status'].upper()}\n"
            f"👤 {order['name']}\n"
            f"📧 {order['email']}\n"
            f"📱 {order['phone']}\n"
            f"📝 {order['description'][:80]}{'…' if len(order['description']) > 80 else ''}\n"
            f"🕐 {order['created_at'][:16]}"
        )

    await query.edit_message_text(
        text="\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=_orders_nav_keyboard(page, total_pages),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  STATISTICS
# ══════════════════════════════════════════════════════════════════════════════

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Display live statistics for users and orders.

    Fetches counts from the DB for multiple time ranges:
    today (1 day), this week (7 days), this month (30 days), all time.

    Args:
        update  : Incoming Telegram update with callback query.
        context : PTB callback context.
    """
    query = update.callback_query
    await query.answer("Loading statistics…")

    if not context.user_data.get("is_admin"):
        await query.edit_message_text("🔒 Session expired. Use /admin to log in again.")
        return

    db: Database = context.bot_data["db"]

    try:
        user_count     = await db.get_user_count()
        orders_today   = await db.get_order_count(days=1)
        orders_week    = await db.get_order_count(days=7)
        orders_month   = await db.get_order_count(days=30)
        orders_total   = await db.get_order_count()
        recent_orders  = await db.get_recent_orders(limit=3)
    except Exception as exc:
        logger.error("Stats fetch error: %s", exc)
        await query.edit_message_text("⚠️ Failed to load statistics.")
        return

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    recent_lines = ""
    for o in recent_orders:
        recent_lines += f"\n  • #{o['id']} {o['name']} ({o['created_at'][:10]})"

    text = (
        f"📊 <b>Bot Statistics</b>\n"
        f"<i>Updated: {now}</i>\n\n"
        f"👥 <b>Users</b>\n"
        f"  Total registered: <b>{user_count}</b>\n\n"
        f"📋 <b>Orders</b>\n"
        f"  Today (24 h): <b>{orders_today}</b>\n"
        f"  This week   : <b>{orders_week}</b>\n"
        f"  This month  : <b>{orders_month}</b>\n"
        f"  All time    : <b>{orders_total}</b>\n"
        f"\n🕐 <b>Latest 3 orders:</b>{recent_lines if recent_lines else ' —'}"
    )

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=_stats_keyboard(),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  CSV EXPORT
# ══════════════════════════════════════════════════════════════════════════════

async def admin_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Export all orders as a CSV file and send it as a document.

    The file is generated in-memory (no temp files) and sent with a
    timestamped filename.

    Args:
        update  : Incoming Telegram update with callback query.
        context : PTB callback context.
    """
    query = update.callback_query
    await query.answer("Generating CSV…")

    if not context.user_data.get("is_admin"):
        await query.edit_message_text("🔒 Session expired. Use /admin to log in again.")
        return

    db: Database = context.bot_data["db"]

    try:
        csv_content = await db.export_orders_csv()
    except Exception as exc:
        logger.error("CSV export error: %s", exc)
        await query.edit_message_text("⚠️ Failed to generate CSV.")
        return

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"orders_{timestamp}.csv"

    csv_bytes = io.BytesIO(csv_content.encode("utf-8"))
    csv_bytes.name = filename

    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=csv_bytes,
        filename=filename,
        caption=f"📤 Orders export — {timestamp}",
    )
    logger.info("CSV exported by admin %s", update.effective_user.id)


# ══════════════════════════════════════════════════════════════════════════════
#  BROADCAST
# ══════════════════════════════════════════════════════════════════════════════

async def admin_broadcast_prompt(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Prompt the admin to enter a broadcast message.

    Args:
        update  : Incoming Telegram update with callback query.
        context : PTB callback context.

    Returns:
        int: ADMIN_WAIT_BROADCAST conversation state.
    """
    query = update.callback_query
    await query.answer()

    if not context.user_data.get("is_admin"):
        await query.edit_message_text("🔒 Session expired. Use /admin to log in again.")
        return ConversationHandler.END

    await query.edit_message_text(
        text=settings.TEXTS["admin_broadcast_prompt"],
        parse_mode=ParseMode.HTML,
    )
    return settings.ADMIN_WAIT_BROADCAST


async def admin_broadcast_send(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Send a broadcast message to all registered users.

    Iterates all user IDs, attempts delivery, and tracks successes/failures.
    Handles blocked bots and deleted accounts gracefully.

    Args:
        update  : Incoming Telegram update with text message (the broadcast).
        context : PTB callback context.

    Returns:
        int: ConversationHandler.END.
    """
    if not context.user_data.get("is_admin"):
        await update.message.reply_text("🔒 Session expired.")
        return ConversationHandler.END

    message_text = update.message.text
    db: Database = context.bot_data["db"]

    try:
        user_ids = await db.get_all_user_ids()
    except Exception as exc:
        logger.error("Broadcast — failed to fetch user IDs: %s", exc)
        await update.message.reply_text("⚠️ Could not fetch users.")
        return ConversationHandler.END

    total = len(user_ids)
    if total == 0:
        await update.message.reply_text("📭 No users to broadcast to.")
        return ConversationHandler.END

    progress_msg = await update.message.reply_text(
        f"📣 Sending to {total} users… 0/{total}"
    )

    sent = 0
    failed = 0

    for i, uid in enumerate(user_ids, start=1):
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📣 <b>Announcement</b>\n\n{message_text}",
                parse_mode=ParseMode.HTML,
            )
            sent += 1
        except Exception as exc:
            failed += 1
            logger.debug("Broadcast to %s failed: %s", uid, exc)

        # Update progress every 10 users
        if i % 10 == 0 or i == total:
            try:
                await progress_msg.edit_text(f"📣 Sending… {i}/{total}")
            except Exception:
                pass

    summary = (
        f"✅ <b>Broadcast complete</b>\n\n"
        f"Sent    : {sent}/{total}\n"
        f"Failed  : {failed}/{total}"
    )
    await progress_msg.edit_text(summary, parse_mode=ParseMode.HTML)
    logger.info(
        "Broadcast by admin %s — sent: %d, failed: %d",
        update.effective_user.id, sent, failed,
    )
    return ConversationHandler.END


async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancel admin conversation (broadcast entry etc.).

    Args:
        update  : Incoming Telegram update.
        context : PTB callback context.

    Returns:
        int: ConversationHandler.END.
    """
    if update.message:
        await update.message.reply_text("❌ Action cancelled.", reply_markup=_admin_panel_keyboard())
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER FACTORY
# ══════════════════════════════════════════════════════════════════════════════

def get_admin_handlers(db: Database) -> list:
    """
    Build and return all admin-panel handlers.

    Includes a ConversationHandler for login + broadcast,
    and individual CallbackQueryHandlers for panel navigation.

    Args:
        db (Database): Shared database instance.

    Returns:
        list: PTB handler objects to register with the Application.
    """
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast_prompt, pattern="^admin_broadcast$")],
        states={
            settings.ADMIN_WAIT_BROADCAST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_send)
            ],
        },
        fallbacks=[CommandHandler("cancel", admin_cancel)],
        allow_reentry=True,
    )

    admin_login_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", cmd_admin)],
        states={
            settings.ADMIN_WAIT_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_check_password)
            ],
        },
        fallbacks=[CommandHandler("cancel", admin_cancel)],
        allow_reentry=True,
    )

    return [
        admin_login_conv,
        broadcast_conv,
        CallbackQueryHandler(admin_orders,  pattern=r"^admin_orders_\d+$"),
        CallbackQueryHandler(admin_stats,   pattern="^admin_stats$"),
        CallbackQueryHandler(admin_export,  pattern="^admin_export$"),
        CallbackQueryHandler(admin_logout,  pattern="^admin_logout$"),
        CallbackQueryHandler(admin_back,    pattern="^admin_back$"),
        CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^noop$"),
    ]
