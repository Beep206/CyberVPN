"""Keyboard modules for telegram bot."""

from __future__ import annotations

from .account import account_keyboard
from .admin_broadcast import broadcast_audience_keyboard
from .admin_main import admin_main_keyboard
from .admin_plans import admin_plans_keyboard
from .admin_stats import admin_stats_keyboard
from .admin_users import admin_users_keyboard
from .common import (
    back_button,
    cancel_button,
    confirm_button,
    main_menu_keyboard,
)
from .config import config_format_keyboard
from .menu import main_menu_kb, profile_kb
from .payment import payment_status_keyboard, payment_success_keyboard
from .referral import referral_keyboard
from .subscription import (
    duration_keyboard,
    payment_methods_keyboard,
    plans_keyboard,
)

__all__ = [
    # Common
    "back_button",
    "cancel_button",
    "confirm_button",
    "main_menu_keyboard",
    # Menu
    "main_menu_kb",
    "profile_kb",
    # Subscription
    "plans_keyboard",
    "duration_keyboard",
    "payment_methods_keyboard",
    # Payment
    "payment_status_keyboard",
    "payment_success_keyboard",
    # Config
    "config_format_keyboard",
    # Referral
    "referral_keyboard",
    # Account
    "account_keyboard",
    # Admin
    "admin_main_keyboard",
    "admin_stats_keyboard",
    "admin_users_keyboard",
    "broadcast_audience_keyboard",
    "admin_plans_keyboard",
]
