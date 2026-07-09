"""Referral program keyboards for CyberVPN Telegram Bot.

Provides referral link sharing, stats viewing, and promotional tools.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable

    from aiogram.types import InlineKeyboardMarkup


def referral_keyboard(i18n: Callable[[str], str], _stats: dict[str, Any] | None = None) -> InlineKeyboardMarkup:
    """Build referral program main keyboard.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardMarkup with referral actions.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text=i18n("btn-referral-share"),
        callback_data="referral:share",
    )
    builder.button(
        text=i18n("btn-referral-link"),
        callback_data="referral:link",
    )
    builder.button(
        text=i18n("btn-referral-stats"),
        callback_data="referral:stats",
    )
    builder.button(
        text=i18n("btn-back"),
        callback_data="nav:back",
    )

    # Layout: 2 buttons per row, except back button
    builder.adjust(2, 1, 1)

    return builder.as_markup()


def invite_codes_keyboard(i18n: Callable[[str], str]) -> InlineKeyboardMarkup:
    """Build keyboard for manually issued invite codes."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text=i18n("btn-my-invites"),
        callback_data="referral:invites",
    )
    builder.button(
        text=i18n("btn-refresh"),
        callback_data="referral:invites",
    )
    builder.button(
        text=i18n("btn-back"),
        callback_data="nav:menu",
    )
    builder.adjust(2, 1)

    return builder.as_markup()
