"""Common keyboard components for CyberVPN Telegram Bot.

Provides reusable button builders and the main menu keyboard with
dynamic content based on user status and subscription state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

if TYPE_CHECKING:
    from collections.abc import Callable


def back_button(i18n: Callable[[str], str]) -> InlineKeyboardButton:
    """Create a 'Back' navigation button.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardButton with callback "nav:back".
    """
    return InlineKeyboardButton(
        text=i18n("button-back"),
        callback_data="nav:back",
    )


def cancel_button(i18n: Callable[[str], str]) -> InlineKeyboardButton:
    """Create a 'Cancel' action button.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardButton with callback "nav:cancel".
    """
    return InlineKeyboardButton(
        text=i18n("button-cancel"),
        callback_data="nav:cancel",
    )


def confirm_button(i18n: Callable[[str], str]) -> InlineKeyboardButton:
    """Create a 'Confirm' action button.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardButton with callback "nav:confirm".
    """
    return InlineKeyboardButton(
        text=i18n("button-confirm"),
        callback_data="nav:confirm",
    )


def main_menu_keyboard(
    i18n: Callable[[str], str],
    is_admin: bool = False,
    has_subscription: bool = False,
    trial_available: bool = True,
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

    # Subscription/Connection section
    if has_subscription:
        builder.button(
            text=i18n("menu-connect"),
            callback_data="menu:connect",
        )
        builder.button(
            text=i18n("menu-renew"),
            callback_data="menu:renew",
        )
    else:
        builder.button(
            text=i18n("menu-subscribe"),
            callback_data="menu:subscribe",
        )
        if trial_available:
            builder.button(
                text=i18n("menu-trial"),
                callback_data="menu:trial",
            )

    # Account section
    builder.button(
        text=i18n("menu-profile"),
        callback_data="menu:profile",
    )
    builder.button(
        text=i18n("menu-referral"),
        callback_data="menu:referral",
    )

    # Support
    builder.button(
        text=i18n("menu-support"),
        callback_data="menu:support",
    )

    # Admin section
    if is_admin:
        builder.button(
            text=i18n("menu-admin"),
            callback_data="menu:admin",
        )

    # Adjust layout: 2 buttons per row
    builder.adjust(2)

    return builder.as_markup()
