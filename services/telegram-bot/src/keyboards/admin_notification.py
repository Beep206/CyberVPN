from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext


def notification_settings_keyboard(
    i18n: I18nContext,
    settings: dict[str, Any],
) -> InlineKeyboardMarkup:
    """Create notification settings keyboard."""
    builder = InlineKeyboardBuilder()

    # Expiry warnings
    expiry_enabled = settings.get("expiry_notifications", True)
    expiry_status = "✅" if expiry_enabled else "❌"
    builder.row(
        InlineKeyboardButton(
            text=f"{expiry_status} {i18n.get('admin-notif-expiry-enabled')}",
            callback_data="admin:notifications:toggle_expiry",
        )
    )

    if expiry_enabled:
        # Days before expiry
        expiry_days = settings.get("expiry_days_before", 3)
        builder.row(
            InlineKeyboardButton(
                text=f"📅 {i18n.get('admin-notif-expiry-days')}: {expiry_days}",
                callback_data="admin:notifications:set_expiry_days",
            )
        )

    # Payment notifications
    payment_enabled = settings.get("payment_notifications", True)
    payment_status = "✅" if payment_enabled else "❌"
    builder.row(
        InlineKeyboardButton(
            text=f"{payment_status} {i18n.get('admin-notif-payment-enabled')}",
            callback_data="admin:notifications:toggle_payment",
        )
    )

    # Referral notifications
    referral_enabled = settings.get("referral_notifications", True)
    referral_status = "✅" if referral_enabled else "❌"
    builder.row(
        InlineKeyboardButton(
            text=f"{referral_status} {i18n.get('admin-notif-referral-enabled')}",
            callback_data="admin:notifications:toggle_referral",
        )
    )

    # System notifications (admin only)
    system_enabled = settings.get("system_notifications", True)
    system_status = "✅" if system_enabled else "❌"
    builder.row(
        InlineKeyboardButton(
            text=f"{system_status} {i18n.get('admin-notif-system-enabled')}",
            callback_data="admin:notifications:toggle_system",
        )
    )

    # Notification time window
    builder.row(
        InlineKeyboardButton(
            text="🕐 " + i18n.get("admin-notif-time-window"),
            callback_data="admin:notifications:set_time_window",
        )
    )

    # Test notification
    builder.row(
        InlineKeyboardButton(
            text="🧪 " + i18n.get("admin-notif-test"),
            callback_data="admin:notifications:test",
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
