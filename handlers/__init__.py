"""
handlers package — aggregates user and admin handler factories.

Usage in main.py:
    from handlers import get_user_handlers, get_admin_handlers
"""

from handlers.user import get_user_handlers      # noqa: F401
from handlers.admin import get_admin_handlers    # noqa: F401
