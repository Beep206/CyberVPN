"""Mini App buttons for Telegram Bot surfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable

    from aiogram.types import InlineKeyboardMarkup

    from src.config import BotSettings


def build_miniapp_url(settings: BotSettings | None, path: str = "") -> str | None:
    """Build a Mini App URL for a nested Mini App path.

    ``settings.miniapp_url`` is expected to point at the Mini App root, for
    example ``https://example.com/ru-RU/miniapp``.
    """
    if settings is None or settings.miniapp_url is None:
        return None

    base = str(settings.miniapp_url).rstrip("/")
    suffix = path.strip("/")
    if not suffix:
        return base
    return f"{base}/{suffix}"


def miniapp_button(
    i18n: Callable[..., str],
    settings: BotSettings | None,
    *,
    text_key: str = "btn-miniapp",
    path: str = "",
    fallback_callback: str = "miniapp:unavailable",
) -> InlineKeyboardButton:
    """Create a WebApp button when configured, otherwise a safe fallback callback."""
    url = build_miniapp_url(settings, path)
    if url is None:
        return InlineKeyboardButton(
            text=i18n(text_key),
            callback_data=fallback_callback,
            style="primary",
        )

    return InlineKeyboardButton(
        text=i18n(text_key),
        web_app=WebAppInfo(url=url),
        style="primary",
    )


def miniapp_open_keyboard(
    i18n: Callable[..., str],
    settings: BotSettings | None,
    *,
    path: str = "",
    text_key: str = "btn-miniapp-open",
) -> InlineKeyboardMarkup:
    """Build a small keyboard with a Mini App entry point and back button."""
    builder = InlineKeyboardBuilder()
    builder.row(miniapp_button(i18n, settings, text_key=text_key, path=path))
    builder.button(text=i18n("btn-back"), callback_data="nav:menu", style="primary")
    builder.adjust(1)
    return builder.as_markup()
