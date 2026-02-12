"""Admin user management keyboard for CyberVPN Telegram Bot.

Provides user search, filtering, and individual user action keyboards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable


def admin_users_keyboard(i18n: Callable[[str], str]) -> InlineKeyboardMarkup:
    """Build admin user management keyboard.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardMarkup with user management options.
    """
    builder = InlineKeyboardBuilder()

    # User filters
    builder.button(
        text=i18n("users-all"),
        callback_data="users:filter:all",
        style="primary",
    )
    builder.button(
        text=i18n("users-active"),
        callback_data="users:filter:active",
        style="primary",
    )
    builder.button(
        text=i18n("users-expired"),
        callback_data="users:filter:expired",
        style="primary",
    )
    builder.button(
        text=i18n("users-trial"),
        callback_data="users:filter:trial",
        style="primary",
    )

    # Actions
    builder.button(
        text=i18n("users-search"),
        callback_data="users:search",
        style="primary",
    )
    builder.button(
        text=i18n("users-export"),
        callback_data="users:export",
        style="primary",
    )

    # Navigation
    builder.button(
        text=i18n("button-back"),
        callback_data="admin:main",
        style="primary",
    )

    # Layout: 2 filters per row, 2 actions per row, back button alone
    builder.adjust(2, 2, 2, 1)

    return builder.as_markup()
