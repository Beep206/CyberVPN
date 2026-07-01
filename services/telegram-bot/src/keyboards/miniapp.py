"""Mini App buttons for Telegram Bot surfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

from aiogram.types import InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable

    from aiogram.types import InlineKeyboardMarkup

    from src.config import BotSettings


def _canonical_miniapp_base(raw_url: str) -> str:
    parsed = urlsplit(raw_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    try:
        miniapp_index = path_parts.index("miniapp")
    except ValueError:
        path = parsed.path.rstrip("/") or "/"
    else:
        path = "/" + "/".join(path_parts[: miniapp_index + 1])
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", "")).rstrip("/")


def build_miniapp_url(settings: BotSettings | None, path: str = "") -> str | None:
    """Build a Mini App URL for a nested Mini App path.

    ``settings.miniapp_url`` is expected to point at the Mini App root, for
    example ``https://example.com/ru-RU/miniapp``. Production config has
    historically used concrete pages with cache-busting query params, so the
    builder normalizes the value back to the Mini App root before appending
    nested paths.
    """
    if settings is None or settings.miniapp_url is None:
        return None

    base = _canonical_miniapp_base(str(settings.miniapp_url))
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
        )

    return InlineKeyboardButton(
        text=i18n(text_key),
        web_app=WebAppInfo(url=url),
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
    builder.button(text=i18n("btn-back"), callback_data="nav:menu")
    builder.adjust(1)
    return builder.as_markup()


def miniapp_onboarding_keyboard(
    i18n: Callable[..., str],
    settings: BotSettings | None,
    *,
    url: str | None = None,
) -> InlineKeyboardMarkup:
    """Build onboarding actions for users who must enter an invite/gift/promo code."""
    builder = InlineKeyboardBuilder()
    resolved_url = url or build_miniapp_url(settings, "onboarding/code")
    if resolved_url is None:
        builder.button(
            text=i18n("btn-miniapp-open"),
            callback_data="miniapp:unavailable",
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=i18n("btn-miniapp-open"),
                web_app=WebAppInfo(url=resolved_url),
            )
        )
    builder.button(text=i18n("btn-enter-code"), callback_data="growth:code")
    builder.button(text=i18n("btn-support"), callback_data="menu:support")
    builder.adjust(1)
    return builder.as_markup()
