"""Canonical customer growth notification keys and categories."""

from __future__ import annotations

from uuid import UUID

GROWTH_NOTIFICATION_CATEGORY_INVITES = "invites"
GROWTH_NOTIFICATION_CATEGORY_REFERRAL_REWARDS = "referral_rewards"
GROWTH_NOTIFICATION_CATEGORY_GIFTS = "gifts"
GROWTH_NOTIFICATION_CATEGORY_ADMIN_UPDATES = "admin_updates"

_KIND_TO_CATEGORY = {
    "invite_issued": GROWTH_NOTIFICATION_CATEGORY_INVITES,
    "invite_redeemed": GROWTH_NOTIFICATION_CATEGORY_INVITES,
    "invite_expired": GROWTH_NOTIFICATION_CATEGORY_INVITES,
    "invite_expiring_soon": GROWTH_NOTIFICATION_CATEGORY_INVITES,
    "referral_reward_pending": GROWTH_NOTIFICATION_CATEGORY_REFERRAL_REWARDS,
    "referral_reward_available": GROWTH_NOTIFICATION_CATEGORY_REFERRAL_REWARDS,
    "referral_reward_reversed": GROWTH_NOTIFICATION_CATEGORY_REFERRAL_REWARDS,
    "gift_purchased": GROWTH_NOTIFICATION_CATEGORY_GIFTS,
    "gift_available": GROWTH_NOTIFICATION_CATEGORY_GIFTS,
    "gift_redeemed": GROWTH_NOTIFICATION_CATEGORY_GIFTS,
    "gift_expired": GROWTH_NOTIFICATION_CATEGORY_GIFTS,
    "gift_expiring_soon": GROWTH_NOTIFICATION_CATEGORY_GIFTS,
    "admin_manual_update": GROWTH_NOTIFICATION_CATEGORY_ADMIN_UPDATES,
}


def normalize_growth_notification_key(notification_key: str) -> str:
    return notification_key.strip().lower()


def category_for_growth_notification_kind(kind: str) -> str:
    return _KIND_TO_CATEGORY.get(kind, GROWTH_NOTIFICATION_CATEGORY_ADMIN_UPDATES)


def invite_issued_notification_key(invite_id: UUID) -> str:
    return f"invite-issued:{invite_id}"


def invite_redeemed_notification_key(invite_id: UUID) -> str:
    return f"invite-used:{invite_id}"


def invite_expired_notification_key(invite_id: UUID) -> str:
    return f"invite-expired:{invite_id}"


def invite_expiring_notification_key(invite_id: UUID) -> str:
    return f"invite-expiring:{invite_id}"


def referral_pending_notification_key(allocation_id: UUID) -> str:
    return f"referral-pending:{allocation_id}"


def referral_available_notification_key(allocation_id: UUID) -> str:
    return f"referral-available:{allocation_id}"


def referral_reversed_notification_key(allocation_id: UUID) -> str:
    return f"referral-reversed:{allocation_id}"


def gift_issued_notification_key(code_id: UUID) -> str:
    return f"gift-issued:{code_id}"


def gift_redeemed_notification_key(code_id: UUID) -> str:
    return f"gift-redeemed:{code_id}"


def gift_expired_notification_key(code_id: UUID) -> str:
    return f"gift-expired:{code_id}"


def gift_expiring_notification_key(code_id: UUID) -> str:
    return f"gift-expiring:{code_id}"


def admin_manual_notification_key(notification_id: UUID) -> str:
    return f"admin-manual:{notification_id}"
