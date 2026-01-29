"""Notification DTO models for telegram-bot service.

This module contains Pydantic models for system notifications and alerts.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class NotificationType(StrEnum):
    """Notification type enumeration."""

    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    SUBSCRIPTION_ACTIVATED = "subscription_activated"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    SUBSCRIPTION_EXPIRING_SOON = "subscription_expiring_soon"
    TRAFFIC_LIMIT_WARNING = "traffic_limit_warning"
    TRAFFIC_LIMIT_REACHED = "traffic_limit_reached"
    DEVICE_LIMIT_REACHED = "device_limit_reached"
    REFERRAL_REGISTERED = "referral_registered"
    REFERRAL_PAID = "referral_paid"
    REFERRAL_REWARD = "referral_reward"
    PROMOCODE_ACTIVATED = "promocode_activated"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    SYSTEM_MAINTENANCE = "system_maintenance"
    ADMIN_ALERT = "admin_alert"


class NotificationPriority(StrEnum):
    """Notification priority enumeration."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationDTO(BaseModel):
    """Notification data transfer object.

    Attributes:
        id: Unique notification identifier
        type: Notification type
        priority: Notification priority level
        recipient_id: Telegram ID of recipient
        message: Notification message content
        metadata: Additional context data (JSON-serializable)
        is_read: Whether notification has been read
        is_sent: Whether notification has been sent via Telegram
        sent_at: Timestamp when notification was sent
        created_at: Notification creation timestamp
        expires_at: Expiration timestamp (for time-sensitive notifications)
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str = Field(..., description="Unique notification identifier")
    type: NotificationType = Field(..., description="Notification type")
    priority: NotificationPriority = Field(default=NotificationPriority.NORMAL, description="Priority level")
    recipient_id: int = Field(..., description="Recipient Telegram ID")
    message: str = Field(..., min_length=1, max_length=4096, description="Notification message")
    metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict, description="Additional context data"
    )
    is_read: bool = Field(default=False, description="Read status")
    is_sent: bool = Field(default=False, description="Sent status")
    sent_at: datetime | None = Field(None, description="Sent timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")


class NotificationStats(BaseModel):
    """Notification statistics.

    Attributes:
        total_notifications: Total notifications created
        unread_count: Number of unread notifications
        unsent_count: Number of unsent notifications
        sent_count: Number of sent notifications
        expired_count: Number of expired notifications
        by_type: Notification counts grouped by type
        by_priority: Notification counts grouped by priority
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    total_notifications: Annotated[int, Field(ge=0, description="Total notifications")]
    unread_count: Annotated[int, Field(ge=0, description="Unread notifications")]
    unsent_count: Annotated[int, Field(ge=0, description="Unsent notifications")]
    sent_count: Annotated[int, Field(ge=0, description="Sent notifications")]
    expired_count: Annotated[int, Field(ge=0, description="Expired notifications")]
    by_type: dict[NotificationType, int] = Field(default_factory=dict, description="Counts by type")
    by_priority: dict[NotificationPriority, int] = Field(default_factory=dict, description="Counts by priority")
