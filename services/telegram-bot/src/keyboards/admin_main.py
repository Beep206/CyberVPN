"""Admin panel main keyboard for CyberVPN Telegram Bot.

Provides navigation to all admin features: stats, user management,
broadcasts, plans, and system configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable


def admin_main_keyboard(i18n: Callable[[str], str]) -> InlineKeyboardMarkup:
    """Build admin panel main menu keyboard.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardMarkup with admin navigation options.
    """
    builder = InlineKeyboardBuilder()

    # Analytics section
    builder.button(
        text=i18n("admin-stats"),
        callback_data="admin:stats",
    )
    builder.button(
        text=i18n("admin-revenue"),
        callback_data="admin:revenue",
    )

    # User management
    builder.button(
        text=i18n("admin-users"),
        callback_data="admin:users",
    )
    builder.button(
        text=i18n("admin-search-user"),
        callback_data="admin:search",
    )

    # Content and engagement
    builder.button(
        text=i18n("admin-broadcast"),
        callback_data="admin:broadcast",
    )

    # Configuration
    builder.button(
        text=i18n("admin-plans"),
        callback_data="admin:plans",
    )
    builder.button(
        text=i18n("admin-settings"),
        callback_data="admin:settings",
    )

    # Navigation
    builder.button(
        text=i18n("button-main-menu"),
        callback_data="nav:menu",
    )

    # Layout: 2 buttons per row
    builder.adjust(2)

    return builder.as_markup()
