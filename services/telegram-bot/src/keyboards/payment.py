"""Payment-related keyboards for CyberVPN Telegram Bot.

Provides keyboards for payment status checking and post-payment actions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

if TYPE_CHECKING:
    from collections.abc import Callable


def payment_status_keyboard(i18n: Callable[[str], str]) -> InlineKeyboardMarkup:
    """Build payment status checking keyboard.

    Displayed during pending payments to allow users to check status
    or cancel the operation.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardMarkup with check/cancel options.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text=i18n("payment-check-status"),
        callback_data="payment:check",
    )
    builder.button(
        text=i18n("payment-cancel"),
        callback_data="payment:cancel",
    )

    # Layout: 1 button per row for clarity
    builder.adjust(1)

    return builder.as_markup()


def payment_success_keyboard(i18n: Callable[[str], str]) -> InlineKeyboardMarkup:
    """Build post-payment success keyboard.

    Displayed after successful payment to guide user to next actions.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardMarkup with connection and menu options.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text=i18n("payment-get-config"),
        callback_data="config:get",
    )
    builder.button(
        text=i18n("payment-view-subscription"),
        callback_data="sub:status",
    )
    builder.button(
        text=i18n("button-main-menu"),
        callback_data="nav:menu",
    )

    # Layout: 1 button per row
    builder.adjust(1)

    return builder.as_markup()
