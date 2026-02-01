"""Payment-related keyboards for CyberVPN Telegram Bot.

Provides keyboards for payment status checking and post-payment actions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable


def payment_status_keyboard(i18n: Callable[..., str], payment_id: str | None = None) -> InlineKeyboardMarkup:
    """Build payment status checking keyboard.

    Displayed during pending payments to allow users to check status
    or cancel the operation.

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardMarkup with check/cancel options.
    """
    builder = InlineKeyboardBuilder()

    callback_data = f"payment:check:{payment_id}" if payment_id else "payment:check"
    builder.button(
        text=i18n("btn-refresh"),
        callback_data=callback_data,
    )
    builder.button(
        text=i18n("btn-cancel"),
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
        text=i18n("btn-connect"),
        callback_data="menu:connect",
    )
    builder.button(
        text=i18n("btn-subscription"),
        callback_data="sub:status",
    )
    builder.button(
        text=i18n("btn-back"),
        callback_data="nav:menu",
    )

    # Layout: 1 button per row
    builder.adjust(1)

    return builder.as_markup()
