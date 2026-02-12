from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext


def referral_settings_keyboard(
    i18n: I18nContext,
    settings: dict,
) -> InlineKeyboardMarkup:
    """Create referral system settings keyboard."""
    builder = InlineKeyboardBuilder()

    # Referral system toggle
    enabled = settings.get("referral_enabled", False)
    status = "✅" if enabled else "❌"
    builder.row(
        InlineKeyboardButton(
            text=f"{status} {i18n.get('admin-referral-enabled')}",
            callback_data="admin:referral:toggle_enabled",
            style="primary",
        )
    )

    if enabled:
        # Reward amount
        reward_amount = settings.get("referral_reward", 0)
        builder.row(
            InlineKeyboardButton(
                text=f"💰 {i18n.get('admin-referral-reward')}: {reward_amount}",
                callback_data="admin:referral:set_reward",
                style="primary",
            )
        )

        # Reward type (percentage or fixed)
        reward_type = settings.get("referral_reward_type", "fixed")
        builder.row(
            InlineKeyboardButton(
                text=f"📊 {i18n.get('admin-referral-type')}: {reward_type.upper()}",
                callback_data="admin:referral:toggle_type",
                style="primary",
            )
        )

        # Minimum withdrawal
        min_withdrawal = settings.get("min_withdrawal", 0)
        builder.row(
            InlineKeyboardButton(
                text=f"💵 {i18n.get('admin-referral-min-withdrawal')}: {min_withdrawal}",
                callback_data="admin:referral:set_min_withdrawal",
                style="primary",
            )
        )

        # Referrer bonus for first purchase
        first_purchase_bonus = settings.get("first_purchase_bonus", False)
        bonus_status = "✅" if first_purchase_bonus else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{bonus_status} {i18n.get('admin-referral-first-purchase-bonus')}",
                callback_data="admin:referral:toggle_first_purchase",
                style="primary",
            )
        )

        # Lifetime referrals
        lifetime_enabled = settings.get("lifetime_referrals", False)
        lifetime_status = "✅" if lifetime_enabled else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{lifetime_status} {i18n.get('admin-referral-lifetime')}",
                callback_data="admin:referral:toggle_lifetime",
                style="primary",
            )
        )

        # View referral stats
        builder.row(
            InlineKeyboardButton(
                text="📊 " + i18n.get("admin-referral-stats"),
                callback_data="admin:referral:stats",
                style="primary",
            )
        )

    # Back button
    builder.row(
        InlineKeyboardButton(
            text="🔙 " + i18n.get("button-back"),
            callback_data="admin:settings",
            style="primary",
        )
    )

    return builder.as_markup()
