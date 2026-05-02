"""Customer growth notification preference helpers."""

from __future__ import annotations

from typing import Any

from .catalog import (
    GROWTH_NOTIFICATION_CATEGORY_ADMIN_UPDATES,
    GROWTH_NOTIFICATION_CATEGORY_GIFTS,
    GROWTH_NOTIFICATION_CATEGORY_INVITES,
    GROWTH_NOTIFICATION_CATEGORY_REFERRAL_REWARDS,
)

GROWTH_NOTIFICATION_CHANNEL_IN_APP = "in_app"
GROWTH_NOTIFICATION_CHANNEL_EMAIL = "email"
GROWTH_NOTIFICATION_CHANNEL_TELEGRAM = "telegram"

DEFAULT_CUSTOMER_GROWTH_NOTIFICATION_PREFS: dict[str, bool] = {
    "growth_in_app_invites": True,
    "growth_email_invites": False,
    "growth_telegram_invites": True,
    "growth_in_app_referral_rewards": True,
    "growth_email_referral_rewards": True,
    "growth_telegram_referral_rewards": True,
    "growth_in_app_gifts": True,
    "growth_email_gifts": True,
    "growth_telegram_gifts": True,
    "growth_in_app_admin_updates": True,
    "growth_email_admin_updates": True,
    "growth_telegram_admin_updates": True,
}

_CATEGORY_KEYS = (
    GROWTH_NOTIFICATION_CATEGORY_INVITES,
    GROWTH_NOTIFICATION_CATEGORY_REFERRAL_REWARDS,
    GROWTH_NOTIFICATION_CATEGORY_GIFTS,
    GROWTH_NOTIFICATION_CATEGORY_ADMIN_UPDATES,
)
_CHANNEL_KEYS = (
    GROWTH_NOTIFICATION_CHANNEL_IN_APP,
    GROWTH_NOTIFICATION_CHANNEL_EMAIL,
    GROWTH_NOTIFICATION_CHANNEL_TELEGRAM,
)


def build_customer_growth_notification_preferences(raw_prefs: dict[str, Any] | None) -> dict[str, bool]:
    prefs = dict(DEFAULT_CUSTOMER_GROWTH_NOTIFICATION_PREFS)
    if isinstance(raw_prefs, dict):
        for key in DEFAULT_CUSTOMER_GROWTH_NOTIFICATION_PREFS:
            if key in raw_prefs:
                prefs[key] = bool(raw_prefs[key])
    return prefs


def growth_notification_pref_key(*, category: str, channel: str) -> str:
    normalized_category = category.strip().lower()
    normalized_channel = channel.strip().lower()
    if normalized_category not in _CATEGORY_KEYS:
        raise ValueError(f"Unsupported growth notification category: {category}")
    if normalized_channel not in _CHANNEL_KEYS:
        raise ValueError(f"Unsupported growth notification channel: {channel}")
    return f"growth_{normalized_channel}_{normalized_category}"


def growth_notification_pref_enabled(
    prefs: dict[str, Any] | None,
    *,
    category: str,
    channel: str,
) -> bool:
    merged = build_customer_growth_notification_preferences(prefs if isinstance(prefs, dict) else None)
    return bool(merged.get(growth_notification_pref_key(category=category, channel=channel), False))
