from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext


def gateway_settings_keyboard(
    i18n: I18nContext,
    settings: dict,
) -> InlineKeyboardMarkup:
    """Create payment gateway settings keyboard."""
    builder = InlineKeyboardBuilder()

    # Telegram Stars
    stars_enabled = settings.get("telegram_stars_enabled", False)
    stars_status = "✅" if stars_enabled else "❌"
    builder.row(
        InlineKeyboardButton(
            text=f"{stars_status} {i18n.get('admin-gateway-telegram-stars')}",
            callback_data="admin:gateways:toggle_stars",
        )
    )

    # Cryptomus
    cryptomus_enabled = settings.get("cryptomus_enabled", False)
    cryptomus_status = "✅" if cryptomus_enabled else "❌"
    builder.row(
        InlineKeyboardButton(
            text=f"{cryptomus_status} {i18n.get('admin-gateway-cryptomus')}",
            callback_data="admin:gateways:toggle_cryptomus",
        )
    )

    if cryptomus_enabled:
        builder.row(
            InlineKeyboardButton(
                text="⚙️ " + i18n.get("admin-gateway-cryptomus-settings"),
                callback_data="admin:gateways:cryptomus_settings",
            )
        )

    # YooKassa
    yookassa_enabled = settings.get("yookassa_enabled", False)
    yookassa_status = "✅" if yookassa_enabled else "❌"
    builder.row(
        InlineKeyboardButton(
            text=f"{yookassa_status} {i18n.get('admin-gateway-yookassa')}",
            callback_data="admin:gateways:toggle_yookassa",
        )
    )

    if yookassa_enabled:
        builder.row(
            InlineKeyboardButton(
                text="⚙️ " + i18n.get("admin-gateway-yookassa-settings"),
                callback_data="admin:gateways:yookassa_settings",
            )
        )

    # Stripe
    stripe_enabled = settings.get("stripe_enabled", False)
    stripe_status = "✅" if stripe_enabled else "❌"
    builder.row(
        InlineKeyboardButton(
            text=f"{stripe_status} {i18n.get('admin-gateway-stripe')}",
            callback_data="admin:gateways:toggle_stripe",
        )
    )

    if stripe_enabled:
        builder.row(
            InlineKeyboardButton(
                text="⚙️ " + i18n.get("admin-gateway-stripe-settings"),
                callback_data="admin:gateways:stripe_settings",
            )
        )

    # Test mode toggle
    test_mode = settings.get("test_mode", False)
    test_status = "🧪" if test_mode else "🔴"
    builder.row(
        InlineKeyboardButton(
            text=f"{test_status} {i18n.get('admin-gateway-test-mode')}",
            callback_data="admin:gateways:toggle_test",
        )
    )

    # Back button
    builder.row(
        InlineKeyboardButton(
            text="🔙 " + i18n.get("button-back"),
            callback_data="admin:settings",
        )
    )

    return builder.as_markup()
