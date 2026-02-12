"""Configuration delivery keyboards for CyberVPN Telegram Bot.

Provides format selection keyboard for VPN configuration delivery
(link, QR code, or instructions).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable


def config_format_keyboard(i18n: Callable[[str], str]) -> InlineKeyboardMarkup:
    """Build configuration format selection keyboard.

    Allows users to choose how they want to receive their VPN config:
    - Direct link (one-click import)
    - QR code (for mobile devices)
    - Text instructions (manual setup)

    Args:
        i18n: Fluent translator function for localization.

    Returns:
        InlineKeyboardMarkup with format selection buttons.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text=i18n("btn-config-link"),
        callback_data="config:link",
        style="primary",
    )
    builder.button(
        text=i18n("btn-config-qr"),
        callback_data="config:qr",
        style="primary",
    )
    builder.button(
        text=i18n("btn-config-instruction"),
        callback_data="config:instructions",
        style="primary",
    )
    builder.button(
        text=i18n("btn-back"),
        callback_data="nav:back",
        style="primary",
    )

    # Layout: 1 option per row for clarity
    builder.adjust(1)

    return builder.as_markup()


def config_delivery_keyboard(i18n: Callable[[str], str]) -> InlineKeyboardMarkup:
    return config_format_keyboard(i18n)
