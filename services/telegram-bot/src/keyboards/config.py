"""Configuration delivery keyboards for CyberVPN Telegram Bot.

Provides format selection keyboard for VPN configuration delivery
(link, QR code, or instructions).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from aiogram.types import InlineKeyboardMarkup


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


def _subscription_label(subscription: dict[str, object], index: int) -> str:
    name = (
        subscription.get("display_name")
        or subscription.get("plan_name")
        or subscription.get("planName")
        or subscription.get("kind")
        or "VPN"
    )
    status = subscription.get("status") or "active"
    expires_at = subscription.get("expires_at") or subscription.get("expiresAt")
    parts = [f"{index + 1}. {name}", str(status)]
    if isinstance(expires_at, str) and expires_at:
        parts.append(expires_at[:10])
    return " · ".join(parts)


def subscription_select_keyboard(
    subscriptions: Iterable[dict[str, object]],
    *,
    action: str,
    i18n: Callable[[str], str],
) -> InlineKeyboardMarkup:
    """Build selected-subscription keyboard with compact callback payloads.

    Telegram callback data is limited, so the callback stores only the list index.
    The handler fetches the list again and resolves the actual subscription key.
    """
    builder = InlineKeyboardBuilder()

    for index, subscription in enumerate(subscriptions):
        if not subscription.get("subscription_key"):
            continue
        builder.button(
            text=_subscription_label(subscription, index),
            callback_data=f"config:pick:{action}:{index}",
            style="primary",
        )

    builder.button(
        text=i18n("btn-back"),
        callback_data="config:menu",
        style="primary",
    )
    builder.adjust(1)
    return builder.as_markup()
