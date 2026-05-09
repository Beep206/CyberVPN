"""Stage 1 Telegram notification contract.

This module keeps the S1 customer-critical Telegram notification set explicit:
subscription expiry, payment outcome and VPN provisioning outcome. The builder
returns queue rows only when Telegram notifications are enabled and a linked
Telegram chat is available.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from src.models.notification_queue import NotificationQueueModel
from src.utils.constants import (
    NOTIFICATION_TYPE_PAYMENT_FAILED,
    NOTIFICATION_TYPE_PAYMENT_RECEIVED,
    NOTIFICATION_TYPE_PROVISIONING_FAILED,
    NOTIFICATION_TYPE_PROVISIONING_READY,
    NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRED,
    NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRING,
    STATUS_PENDING,
)
from src.utils.formatting import (
    payment_failed,
    payment_received,
    provisioning_failed,
    provisioning_ready,
    subscription_expired,
    subscription_expiring,
)

Stage1TelegramNotificationType = Literal[
    "subscription_expiring",
    "subscription_expired",
    "payment_received",
    "payment_failed",
    "provisioning_ready",
    "provisioning_failed",
]

STAGE1_TELEGRAM_NOTIFICATION_TYPES: frozenset[Stage1TelegramNotificationType] = frozenset(
    {
        NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRING,
        NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRED,
        NOTIFICATION_TYPE_PAYMENT_RECEIVED,
        NOTIFICATION_TYPE_PAYMENT_FAILED,
        NOTIFICATION_TYPE_PROVISIONING_READY,
        NOTIFICATION_TYPE_PROVISIONING_FAILED,
    }
)


@dataclass(frozen=True, slots=True)
class Stage1TelegramNotification:
    """Queue-ready Telegram notification for the S1 beta path."""

    telegram_id: int
    notification_type: Stage1TelegramNotificationType
    message: str
    scheduled_at: datetime

    def to_queue_model(self) -> NotificationQueueModel:
        """Convert the S1 contract object to the durable notification queue model."""
        return NotificationQueueModel(
            telegram_id=self.telegram_id,
            message=self.message,
            notification_type=self.notification_type,
            status=STATUS_PENDING,
            scheduled_at=self.scheduled_at,
        )


def build_stage1_telegram_notification(
    *,
    telegram_id: int | None,
    notification_type: Stage1TelegramNotificationType,
    username: str,
    enabled: bool = True,
    scheduled_at: datetime | None = None,
    days_left: int | None = None,
    expire_at: str = "",
    renew_url: str = "",
    amount: float | None = None,
    currency: str = "USD",
    plan_name: str = "",
    plan_days: int | None = None,
    reason: str = "",
    cabinet_url: str = "",
    support_reference: str = "",
    retry_hint: str = "",
) -> Stage1TelegramNotification | None:
    """Build a queue-ready S1 Telegram notification when the channel is enabled."""
    if not enabled or telegram_id is None:
        return None
    if telegram_id <= 0:
        raise ValueError("telegram_id must be a positive integer")
    if notification_type not in STAGE1_TELEGRAM_NOTIFICATION_TYPES:
        raise ValueError(f"Unsupported Stage 1 Telegram notification type: {notification_type}")

    scheduled = scheduled_at or datetime.now(UTC)
    message = _build_stage1_message(
        notification_type=notification_type,
        username=username,
        days_left=days_left,
        expire_at=expire_at,
        renew_url=renew_url,
        amount=amount,
        currency=currency,
        plan_name=plan_name,
        plan_days=plan_days,
        reason=reason,
        cabinet_url=cabinet_url,
        support_reference=support_reference,
        retry_hint=retry_hint,
    )

    return Stage1TelegramNotification(
        telegram_id=telegram_id,
        notification_type=notification_type,
        message=message,
        scheduled_at=scheduled,
    )


def _build_stage1_message(
    *,
    notification_type: Stage1TelegramNotificationType,
    username: str,
    days_left: int | None,
    expire_at: str,
    renew_url: str,
    amount: float | None,
    currency: str,
    plan_name: str,
    plan_days: int | None,
    reason: str,
    cabinet_url: str,
    support_reference: str,
    retry_hint: str,
) -> str:
    if notification_type == NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRING:
        if days_left is None or not expire_at:
            raise ValueError("subscription_expiring requires days_left and expire_at")
        return subscription_expiring(username, days_left, expire_at, renew_url)

    if notification_type == NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRED:
        if not expire_at:
            raise ValueError("subscription_expired requires expire_at")
        return subscription_expired(username, expire_at)

    if notification_type == NOTIFICATION_TYPE_PAYMENT_RECEIVED:
        if amount is None or plan_days is None:
            raise ValueError("payment_received requires amount and plan_days")
        return payment_received(username, amount, currency, plan_name, plan_days)

    if notification_type == NOTIFICATION_TYPE_PAYMENT_FAILED:
        if amount is None:
            raise ValueError("payment_failed requires amount")
        return payment_failed(username, amount, currency, reason)

    if notification_type == NOTIFICATION_TYPE_PROVISIONING_READY:
        return provisioning_ready(username, plan_name, cabinet_url)

    if notification_type == NOTIFICATION_TYPE_PROVISIONING_FAILED:
        return provisioning_failed(username, support_reference, retry_hint)

    raise ValueError(f"Unsupported Stage 1 Telegram notification type: {notification_type}")
