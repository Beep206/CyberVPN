"""Admin broadcast keyboard for CyberVPN Telegram Bot.

Provides audience selection and broadcast confirmation keyboards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable


def broadcast_audience_keyboard(i18n: Callable[[str], str]) -> InlineKeyboardMarkup:
    """Build broadcast audience selection keyboard.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardMarkup with audience targeting options.
    """
    builder = InlineKeyboardBuilder()

    # Audience segments
    builder.button(
        text=i18n("broadcast-all-users"),
        callback_data="broadcast:audience:all",
        style="primary",
    )
    builder.button(
        text=i18n("broadcast-active-subscribers"),
        callback_data="broadcast:audience:active",
        style="primary",
    )
    builder.button(
        text=i18n("broadcast-expired-subscribers"),
        callback_data="broadcast:audience:expired",
        style="primary",
    )
    builder.button(
        text=i18n("broadcast-trial-users"),
        callback_data="broadcast:audience:trial",
        style="primary",
    )
    builder.button(
        text=i18n("broadcast-no-subscription"),
        callback_data="broadcast:audience:none",
        style="primary",
    )

    # Navigation
    builder.button(
        text=i18n("button-cancel"),
        callback_data="admin:main",
        style="danger",
    )

    # Layout: 1 audience per row for clarity
    builder.adjust(1)

    return builder.as_markup()
