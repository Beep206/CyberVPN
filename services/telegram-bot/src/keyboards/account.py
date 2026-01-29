"""Account management keyboards for CyberVPN Telegram Bot.

Provides profile, language, and support access keyboards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

if TYPE_CHECKING:
    from collections.abc import Callable


def account_keyboard(i18n: Callable[[str], str]) -> InlineKeyboardMarkup:
    """Build account management keyboard.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardMarkup with account management options.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text=i18n("account-profile"),
        callback_data="account:profile",
    )
    builder.button(
        text=i18n("account-language"),
        callback_data="account:language",
    )
    builder.button(
        text=i18n("account-support"),
        callback_data="account:support",
    )
    builder.button(
        text=i18n("button-main-menu"),
        callback_data="nav:menu",
    )

    # Layout: 2 buttons per row, except menu button
    builder.adjust(2, 1, 1)

    return builder.as_markup()
