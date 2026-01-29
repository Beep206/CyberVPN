"""Admin plan management keyboard for CyberVPN Telegram Bot.

Provides plan creation, editing, and configuration keyboards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

if TYPE_CHECKING:
    from collections.abc import Callable


def admin_plans_keyboard(i18n: Callable[[str], str]) -> InlineKeyboardMarkup:
    """Build plan management keyboard.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardMarkup with plan management options.
    """
    builder = InlineKeyboardBuilder()

    # Plan actions
    builder.button(
        text=i18n("plans-view-all"),
        callback_data="plans:list",
    )
    builder.button(
        text=i18n("plans-create-new"),
        callback_data="plans:create",
    )
    builder.button(
        text=i18n("plans-edit-existing"),
        callback_data="plans:edit",
    )
    builder.button(
        text=i18n("plans-toggle-active"),
        callback_data="plans:toggle",
    )

    # Pricing configuration
    builder.button(
        text=i18n("plans-pricing"),
        callback_data="plans:pricing",
    )
    builder.button(
        text=i18n("plans-durations"),
        callback_data="plans:durations",
    )

    # Navigation
    builder.button(
        text=i18n("button-back"),
        callback_data="admin:main",
    )

    # Layout: 2 buttons per row
    builder.adjust(2)

    return builder.as_markup()
