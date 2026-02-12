"""Keyboard helper utilities for styled buttons and custom emoji."""

from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardButton


def custom_emoji(emoji_id: str | None, fallback: str) -> str:
    """Wrap a custom emoji ID in the tg-emoji tag.

    Args:
        emoji_id: Telegram custom emoji ID, or None to use fallback.
        fallback: Plain-text fallback emoji.

    Returns:
        HTML string with custom emoji tag, or plain fallback.
    """
    if emoji_id:
        return f'<tg-emoji emoji_id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback


def icon_button(
    text: str,
    callback_data: str,
    icon_emoji_id: str | None = None,
    **kwargs: Any,
) -> InlineKeyboardButton:
    """Create an InlineKeyboardButton with optional custom icon emoji.

    Args:
        text: Button label text.
        callback_data: Callback data string.
        icon_emoji_id: Optional custom emoji ID displayed before text.
        **kwargs: Extra keyword arguments forwarded to InlineKeyboardButton.

    Returns:
        Configured InlineKeyboardButton instance.
    """
    params: dict[str, Any] = {"text": text, "callback_data": callback_data, **kwargs}
    if icon_emoji_id:
        params["icon_custom_emoji_id"] = icon_emoji_id
    return InlineKeyboardButton(**params)
