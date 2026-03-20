"""
main.py — Entry point for the Telegram Bot.

Initializes logging, database, registers all handlers,
configures error handling and graceful shutdown.
"""

import asyncio
import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ── Load environment variables ────────────────────────────────────────────────
load_dotenv()

# ── Local imports ─────────────────────────────────────────────────────────────
from config import settings
from database import Database
from handlers import get_user_handlers, get_admin_handlers

# ── Ensure data/ directory exists ─────────────────────────────────────────────
Path("data").mkdir(exist_ok=True)
Path("logs").mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
#  LOGGING SETUP
# ══════════════════════════════════════════════════════════════════════════════

def setup_logging() -> logging.Logger:
    """
    Configure logging with both console and rotating file handlers.

    Log levels:
        - Console : INFO
        - File    : DEBUG  (rotates at 5 MB, keeps 3 backups)

    Returns:
        logging.Logger: Configured root logger.
    """
    log_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # ── Console handler ───────────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_formatter)

    # ── Rotating file handler ─────────────────────────────────────────────────
    file_handler = RotatingFileHandler(
        filename=settings.LOG_FILE,
        maxBytes=5 * 1024 * 1024,   # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram.vendor").setLevel(logging.WARNING)

    return root_logger


# ══════════════════════════════════════════════════════════════════════════════
#  ERROR HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Global error handler for all unhandled exceptions raised during updates.

    Logs the full traceback, notifies the user with a friendly message,
    and optionally notifies the admin chat.

    Args:
        update  : The incoming Telegram Update (may be None for job errors).
        context : The callback context containing the exception.
    """
    logger = logging.getLogger("ErrorHandler")
    logger.error("Unhandled exception:", exc_info=context.error)

    # Notify user
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ An unexpected error occurred. Please try again later.\n"
                "If the problem persists, contact support."
            )
        except Exception:
            pass  # If we can't even reply, move on silently

    # Notify admin chat
    if settings.ADMIN_CHAT_ID:
        try:
            error_text = (
                f"🚨 <b>Bot Error</b>\n\n"
                f"<b>Error:</b> <code>{type(context.error).__name__}: {context.error}</code>\n"
            )
            if isinstance(update, Update) and update.effective_user:
                user = update.effective_user
                error_text += (
                    f"<b>User:</b> {user.full_name} "
                    f"(<code>{user.id}</code>)\n"
                )
            await context.bot.send_message(
                chat_id=settings.ADMIN_CHAT_ID,
                text=error_text,
                parse_mode="HTML",
            )
        except Exception as notify_err:
            logger.warning("Could not notify admin about error: %s", notify_err)


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════

def register_handlers(app: Application, db: Database) -> None:
    """
    Register all conversation handlers, command handlers, and callback handlers.

    Order matters — more specific handlers must be registered before catch-alls.

    Args:
        app : The PTB Application instance.
        db  : The initialized Database instance.
    """
    logger = logging.getLogger("HandlerRegistry")

    user_handlers = get_user_handlers(db)
    admin_handlers = get_admin_handlers(db)

    for handler in user_handlers:
        app.add_handler(handler)
        logger.debug("Registered user handler: %s", type(handler).__name__)

    for handler in admin_handlers:
        app.add_handler(handler)
        logger.debug("Registered admin handler: %s", type(handler).__name__)

    # Global error handler
    app.add_error_handler(error_handler)

    logger.info("All handlers registered successfully (%d total).",
                len(user_handlers) + len(admin_handlers))


# ══════════════════════════════════════════════════════════════════════════════
#  POST-INIT HOOK  (runs after Application.initialize())
# ══════════════════════════════════════════════════════════════════════════════

async def post_init(application: Application) -> None:
    """
    Called once after the Application is initialized but before polling starts.

    Used to:
    - Open the database connection
    - Set bot commands visible in Telegram UI
    - Log startup information

    Args:
        application : The fully initialized PTB Application instance.
    """
    logger = logging.getLogger("PostInit")

    # Open DB connection stored in bot_data for global access
    db: Database = application.bot_data["db"]
    await db.connect()
    logger.info("Database connected: %s", settings.DB_PATH)

    # Register bot commands in Telegram's command menu
    await application.bot.set_my_commands([
        ("start",  "🏠 Main menu"),
        ("order",  "📋 Place an order"),
        ("faq",    "❓ Frequently asked questions"),
        ("admin",  "🔐 Admin panel"),
        ("cancel", "❌ Cancel current action"),
    ])
    logger.info("Bot commands registered.")

    # Fetch bot info for the startup log
    bot_info = await application.bot.get_me()
    logger.info("=" * 60)
    logger.info("  Bot started: @%s (ID: %s)", bot_info.username, bot_info.id)
    logger.info("  Environment : %s", os.getenv("ENV", "production"))
    logger.info("  Database    : %s", settings.DB_PATH)
    logger.info("  Log file    : %s", settings.LOG_FILE)
    logger.info("  Admin chat  : %s", settings.ADMIN_CHAT_ID or "Not configured")
    logger.info("=" * 60)


# ══════════════════════════════════════════════════════════════════════════════
#  POST-SHUTDOWN HOOK
# ══════════════════════════════════════════════════════════════════════════════

async def post_shutdown(application: Application) -> None:
    """
    Called once after polling has stopped and before the process exits.

    Gracefully closes the database connection.

    Args:
        application : The PTB Application instance being shut down.
    """
    logger = logging.getLogger("PostShutdown")
    db: Database = application.bot_data.get("db")
    if db:
        await db.close()
        logger.info("Database connection closed.")
    logger.info("Bot shut down gracefully.")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Application entry point.

    Steps:
    1. Setup logging
    2. Validate BOT_TOKEN
    3. Build PTB Application with post-init / post-shutdown hooks
    4. Create & inject Database instance
    5. Register all handlers
    6. Start long-polling

    Raises:
        SystemExit: If BOT_TOKEN is missing or invalid.
    """
    logger = setup_logging()
    logger.info("Starting Telegram Bot...")

    # ── Validate token ────────────────────────────────────────────────────────
    token = settings.BOT_TOKEN
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        logger.critical(
            "BOT_TOKEN is not set. Copy .env.example → .env and fill in your token."
        )
        sys.exit(1)

    # ── Build application ─────────────────────────────────────────────────────
    app = (
        ApplicationBuilder()
        .token(token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .concurrent_updates(False)   # Keep sequential for SQLite safety
        .build()
    )

    # ── Inject shared database instance ───────────────────────────────────────
    db = Database(settings.DB_PATH)
    app.bot_data["db"] = db

    # ── Register handlers ─────────────────────────────────────────────────────
    register_handlers(app, db)

    # ── Graceful shutdown on SIGINT / SIGTERM ─────────────────────────────────
    logger.info("Bot is running. Press Ctrl+C to stop.")

    try:
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,       # Ignore messages sent while offline
        )
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt — shutting down...")
    except Exception as exc:
        logger.critical("Fatal error in polling loop: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
