"""
database/db.py — Async SQLite database manager.

Provides all CRUD operations for the `users` and `orders` tables.
Uses aiosqlite for non-blocking I/O compatible with python-telegram-bot's
asyncio event loop.
"""

import csv
import io
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class Database:
    """
    Async SQLite database manager.

    All public methods are coroutines and must be awaited.
    Call `await db.connect()` before use and `await db.close()` on shutdown.

    Args:
        db_path (str): Absolute or relative path to the .db file.
    """

    # ── DDL ────────────────────────────────────────────────────────────────────
    _CREATE_USERS = """
    CREATE TABLE IF NOT EXISTS users (
        user_id     INTEGER PRIMARY KEY,
        username    TEXT,
        first_name  TEXT,
        last_name   TEXT,
        joined_at   TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """

    _CREATE_ORDERS = """
    CREATE TABLE IF NOT EXISTS orders (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL REFERENCES users(user_id),
        name        TEXT NOT NULL,
        email       TEXT NOT NULL,
        phone       TEXT NOT NULL,
        description TEXT NOT NULL,
        status      TEXT NOT NULL DEFAULT 'new',
        created_at  TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """

    _CREATE_IDX_ORDERS_USER = """
    CREATE INDEX IF NOT EXISTS idx_orders_user_id
    ON orders(user_id);
    """

    _CREATE_IDX_ORDERS_DATE = """
    CREATE INDEX IF NOT EXISTS idx_orders_created_at
    ON orders(created_at);
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    # ══════════════════════════════════════════════════════════════════════════
    #  CONNECTION LIFECYCLE
    # ══════════════════════════════════════════════════════════════════════════

    async def connect(self) -> None:
        """
        Open the SQLite connection, enable WAL mode, and create tables.

        WAL (Write-Ahead Logging) allows concurrent reads without blocking.
        Must be called once before any other method.
        """
        try:
            self._conn = await aiosqlite.connect(self._db_path)
            self._conn.row_factory = aiosqlite.Row  # dict-like rows

            await self._conn.execute("PRAGMA journal_mode=WAL;")
            await self._conn.execute("PRAGMA foreign_keys=ON;")
            await self._conn.execute(self._CREATE_USERS)
            await self._conn.execute(self._CREATE_ORDERS)
            await self._conn.execute(self._CREATE_IDX_ORDERS_USER)
            await self._conn.execute(self._CREATE_IDX_ORDERS_DATE)
            await self._conn.commit()

            logger.info("Database initialised: %s", self._db_path)
        except Exception as exc:
            logger.critical("Failed to connect to database: %s", exc)
            raise

    async def close(self) -> None:
        """Gracefully close the database connection."""
        if self._conn:
            await self._conn.close()
            logger.info("Database connection closed.")

    def _ensure_connected(self) -> None:
        """Raise RuntimeError if connect() has not been called yet."""
        if self._conn is None:
            raise RuntimeError("Database not connected. Call await db.connect() first.")

    # ══════════════════════════════════════════════════════════════════════════
    #  USERS
    # ══════════════════════════════════════════════════════════════════════════

    async def upsert_user(
        self,
        user_id: int,
        username: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
    ) -> None:
        """
        Insert a new user or update their profile if they already exist.

        Args:
            user_id    : Telegram user ID (primary key).
            username   : Telegram @username (may be None).
            first_name : User's first name.
            last_name  : User's last name (may be None).
        """
        self._ensure_connected()
        await self._conn.execute(
            """
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name,
                last_name  = excluded.last_name
            """,
            (user_id, username, first_name, last_name),
        )
        await self._conn.commit()
        logger.debug("Upserted user: %s (@%s)", user_id, username)

    async def get_user_count(self) -> int:
        """
        Return the total number of unique users in the database.

        Returns:
            int: Count of rows in the users table.
        """
        self._ensure_connected()
        async with self._conn.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

    async def get_all_user_ids(self) -> List[int]:
        """
        Return a list of all user IDs (for broadcast).

        Returns:
            List[int]: All user_id values from the users table.
        """
        self._ensure_connected()
        async with self._conn.execute("SELECT user_id FROM users") as cur:
            rows = await cur.fetchall()
            return [row[0] for row in rows]

    # ══════════════════════════════════════════════════════════════════════════
    #  ORDERS
    # ══════════════════════════════════════════════════════════════════════════

    async def create_order(
        self,
        user_id: int,
        name: str,
        email: str,
        phone: str,
        description: str,
    ) -> int:
        """
        Insert a new order and return its auto-generated ID.

        Args:
            user_id     : Telegram user ID of the requester.
            name        : Customer's full name.
            email       : Customer's email address.
            phone       : Customer's phone number.
            description : Task / service description.

        Returns:
            int: The newly created order's ID.
        """
        self._ensure_connected()
        async with self._conn.execute(
            """
            INSERT INTO orders (user_id, name, email, phone, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, name, email, phone, description),
        ) as cur:
            order_id = cur.lastrowid
        await self._conn.commit()
        logger.info("Order #%s created by user %s", order_id, user_id)
        return order_id

    async def get_all_orders(self) -> List[aiosqlite.Row]:
        """
        Fetch all orders ordered by creation date (newest first).

        Returns:
            List[aiosqlite.Row]: All rows from the orders table.
        """
        self._ensure_connected()
        async with self._conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC"
        ) as cur:
            return await cur.fetchall()

    async def get_recent_orders(self, limit: int = 5) -> List[aiosqlite.Row]:
        """
        Fetch the N most recent orders.

        Args:
            limit (int): Maximum number of rows to return. Default 5.

        Returns:
            List[aiosqlite.Row]: Most recent orders, newest first.
        """
        self._ensure_connected()
        async with self._conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cur:
            return await cur.fetchall()

    async def get_order_count(self, days: Optional[int] = None) -> int:
        """
        Return the total number of orders, optionally within the last N days.

        Args:
            days (int | None): If provided, count only orders from the last N days.
                               If None, count all orders.

        Returns:
            int: Order count.
        """
        self._ensure_connected()
        if days is not None:
            since = (datetime.utcnow() - timedelta(days=days)).isoformat(sep=" ")
            async with self._conn.execute(
                "SELECT COUNT(*) FROM orders WHERE created_at >= ?", (since,)
            ) as cur:
                row = await cur.fetchone()
        else:
            async with self._conn.execute("SELECT COUNT(*) FROM orders") as cur:
                row = await cur.fetchone()
        return row[0] if row else 0

    # ══════════════════════════════════════════════════════════════════════════
    #  CSV EXPORT
    # ══════════════════════════════════════════════════════════════════════════

    async def export_orders_csv(self) -> str:
        """
        Serialise all orders to a CSV string.

        The CSV includes a header row and uses comma delimiters.
        Suitable for sending as a Telegram document (in-memory, no temp files).

        Returns:
            str: Full CSV content as a string.
        """
        self._ensure_connected()
        orders = await self.get_all_orders()

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        # Header
        writer.writerow(["id", "user_id", "name", "email", "phone",
                          "description", "status", "created_at"])

        # Rows
        for order in orders:
            writer.writerow([
                order["id"],
                order["user_id"],
                order["name"],
                order["email"],
                order["phone"],
                order["description"],
                order["status"],
                order["created_at"],
            ])

        csv_content = output.getvalue()
        logger.info("Exported %d orders to CSV.", len(orders))
        return csv_content
