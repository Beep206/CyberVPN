"""Configuration delivery keyboards for CyberVPN Telegram Bot.

Provides format selection keyboard for VPN configuration delivery
(link, QR code, or instructions).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

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
        text=i18n("config-format-link"),
        callback_data="config:format:link",
    )
    builder.button(
        text=i18n("config-format-qr"),
        callback_data="config:format:qr",
    )
    builder.button(
        text=i18n("config-format-instructions"),
        callback_data="config:format:instructions",
    )
    builder.button(
        text=i18n("button-back"),
        callback_data="nav:back",
    )

    # Layout: 1 option per row for clarity
    builder.adjust(1)

    return builder.as_markup()
