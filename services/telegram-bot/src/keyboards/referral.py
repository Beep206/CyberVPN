"""Referral program keyboards for CyberVPN Telegram Bot.

Provides referral link sharing, stats viewing, and promotional tools.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

if TYPE_CHECKING:
    from collections.abc import Callable


def referral_keyboard(i18n: Callable[[str], str]) -> InlineKeyboardMarkup:
    """Build referral program main keyboard.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardMarkup with referral actions.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text=i18n("referral-my-link"),
        callback_data="referral:link",
    )
    builder.button(
        text=i18n("referral-stats"),
        callback_data="referral:stats",
    )
    builder.button(
        text=i18n("referral-share"),
        callback_data="referral:share",
    )
    builder.button(
        text=i18n("button-back"),
        callback_data="nav:back",
    )

    # Layout: 2 buttons per row, except back button
    builder.adjust(2, 1, 1)

    return builder.as_markup()
