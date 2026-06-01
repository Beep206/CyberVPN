"""Common keyboard components for CyberVPN Telegram Bot.

Provides reusable button builders and the main menu keyboard with
dynamic content based on user status and subscription state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.keyboards.miniapp import miniapp_button

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.config import BotSettings


def back_button(i18n: Callable[[str], str]) -> InlineKeyboardButton:
    """Create a 'Back' navigation button.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardButton with callback "nav:back".
    """
    return InlineKeyboardButton(
        text=i18n("btn-back"),
        callback_data="nav:back",
        style="primary",
    )


def cancel_button(i18n: Callable[[str], str]) -> InlineKeyboardButton:
    """Create a 'Cancel' action button.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardButton with callback "nav:cancel".
    """
    return InlineKeyboardButton(
        text=i18n("btn-cancel"),
        callback_data="nav:cancel",
        style="danger",
    )


def confirm_button(i18n: Callable[[str], str]) -> InlineKeyboardButton:
    """Create a 'Confirm' action button.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardButton with callback "nav:confirm".
    """
    return InlineKeyboardButton(
        text=i18n("btn-confirm"),
        callback_data="nav:confirm",
        style="success",
    )


def main_menu_keyboard(
    i18n: Callable[..., str],
    is_admin: bool = False,
    has_subscription: bool = False,
    trial_available: bool = True,
    *,
    settings: BotSettings | None = None,
) -> InlineKeyboardMarkup:
    """Build the main menu keyboard with dynamic options.

    Args:
        i18n: Fluent translator function for localization.
        is_admin: Whether user has admin privileges.
        has_subscription: Whether user has an active subscription.
        trial_available: Whether free trial is available for this user.

    Returns:
        InlineKeyboardMarkup with appropriate menu buttons.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text=i18n("btn-vpn"), callback_data="menu:vpn", style="primary")
    builder.button(text=i18n("btn-subscription"), callback_data="menu:subscription", style="primary")
    builder.button(text=i18n("btn-finance"), callback_data="menu:finance", style="primary")
    builder.button(text=i18n("btn-rewards"), callback_data="menu:growth", style="primary")
    builder.button(text=i18n("btn-profile"), callback_data="account:profile", style="primary")
    builder.button(text=i18n("btn-support"), callback_data="menu:support", style="primary")
    builder.row(miniapp_button(i18n, settings))

    if not has_subscription and trial_available:
        builder.button(text=i18n("btn-trial"), callback_data="trial:activate", style="success")

    # Admin section
    if is_admin:
        builder.button(
            text=i18n("btn-admin-panel"),
            callback_data="admin:menu",
        )

    builder.adjust(2, 2, 2, 1, 1)

    return builder.as_markup()
