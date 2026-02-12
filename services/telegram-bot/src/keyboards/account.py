"""Account management keyboards for CyberVPN Telegram Bot.

Provides profile, language, and support access keyboards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable


def account_keyboard(i18n: Callable[..., str]) -> InlineKeyboardMarkup:
    """Build account management keyboard.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardMarkup with account management options.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text=i18n("btn-profile"),
        callback_data="account:profile",
        style="primary",
    )
    builder.button(
        text=i18n("btn-language"),
        callback_data="account:language",
        style="primary",
    )
    builder.button(
        text=i18n("btn-support"),
        callback_data="menu:support",
        style="primary",
    )
    builder.button(
        text=i18n("btn-back"),
        callback_data="nav:menu",
        style="primary",
    )

    # Layout: 2 buttons per row, except menu button
    builder.adjust(2, 1, 1)

    return builder.as_markup()


def language_selection_keyboard(i18n: Callable[..., str]) -> InlineKeyboardMarkup:
    """Build language selection keyboard."""
    builder = InlineKeyboardBuilder()

    builder.button(text="RU", callback_data="language:ru", style="primary")
    builder.button(text="EN", callback_data="language:en", style="primary")
    builder.button(text=i18n("btn-back"), callback_data="nav:back", style="primary")

    builder.adjust(2, 1)
    return builder.as_markup()
