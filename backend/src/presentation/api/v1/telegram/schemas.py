"""Telegram API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TelegramUserResponse(BaseModel):
    """Response schema for Telegram user information."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "uuid": "550e8400-e29b-41d4-a716-446655440000",
                "username": "user123",
                "status": "active",
                "data_usage": 5368709120,
                "data_limit": 107374182400,
                "expires_at": "2024-12-31T23:59:59",
                "subscription_url": "vless://config-string-here",
            }
        },
    )

    uuid: UUID = Field(..., description="User unique identifier")
    username: str = Field(..., max_length=100, description="Username")
    status: str = Field(..., max_length=50, description="User account status")
    data_usage: int = Field(..., description="Current data usage in bytes")
    data_limit: int | None = Field(None, description="Data limit in bytes")
    expires_at: datetime | None = Field(None, description="Subscription expiration date")
    subscription_url: str | None = Field(None, max_length=5000, description="VPN subscription configuration URL")


class CreateSubscriptionRequest(BaseModel):
    """Request schema for creating a subscription."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "plan_name": "Premium Monthly",
                "duration_days": 30,
            }
        }
    )

    plan_name: str = Field(..., max_length=100, description="Name of the subscription plan")
    duration_days: int = Field(..., gt=0, le=3650, description="Subscription duration in days")


class CreateSubscriptionResponse(BaseModel):
    """Response schema for a created Telegram user subscription."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(default="success", description="Operation status")
    subscription_id: str | int | None = Field(None, description="Created subscription identifier")
    expires_at: datetime | None = Field(None, description="Subscription expiration date")


class ConfigResponse(BaseModel):
    """Response schema for VPN configuration."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "config_string": "vless://uuid@server:port?encryption=none&security=tls",
                "client_type": "vless",
            }
        }
    )

    config_string: str = Field(..., max_length=5000, description="VPN configuration string")
    client_type: str = Field(..., max_length=50, description="VPN client type (vless, vmess, etc.)")


class NotifyRequest(BaseModel):
    """Request schema for sending notifications to Telegram users."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "telegram_id": 123456789,
                "message": "Your subscription will expire in 3 days",
                "notification_type": "warning",
            }
        }
    )

    telegram_id: int = Field(..., description="Telegram user ID")
    message: str = Field(..., min_length=1, max_length=4096, description="Notification message")
    notification_type: str | None = Field(
        None,
        max_length=50,
        description="Type of notification (info, warning, error)",
    )


class TelegramBotUserCreateRequest(BaseModel):
    """Internal bot request to create or bootstrap a Telegram user."""

    telegram_id: int = Field(..., gt=0)
    username: str | None = Field(default=None, max_length=255)
    first_name: str | None = Field(default=None, max_length=255)
    language_code: str = Field(default="en", max_length=16)
    referrer_id: int | None = Field(default=None, gt=0)


class TelegramBotUserUpdateRequest(BaseModel):
    """Internal bot request to update Telegram-side profile details."""

    username: str | None = Field(default=None, max_length=255)
    first_name: str | None = Field(default=None, max_length=255)
    language_code: str | None = Field(default=None, max_length=16)


class TelegramBotUserResponse(BaseModel):
    """Telegram bot-facing user payload compatible with the bot service DTO."""

    uuid: str
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    language_code: str = "en"
    status: str = "none"
    is_admin: bool = False
    personal_discount: float = 0.0
    next_purchase_discount: float = 0.0
    referrer_id: int | None = None
    points: int = 0
    subscription: dict | None = None
    subscriptions: list[dict] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TelegramBotAccessSettingsResponse(BaseModel):
    """Bot access settings returned to the Telegram bot service."""

    access_mode: str = "open"
    rules_url: str | None = None
    channel_id: str | None = None


class TelegramBotSubscriptionResponse(BaseModel):
    """Bot-facing subscription summary."""

    status: str
    plan_name: str | None = None
    expires_at: datetime | None = None
    traffic_limit_bytes: int | None = None
    used_traffic_bytes: int | None = None
    auto_renew: bool = False


class TelegramBotTrialStatusResponse(BaseModel):
    """Bot-facing trial status and eligibility."""

    eligible: bool
    reason: str | None = None
    is_trial_active: bool = False
    trial_start: datetime | None = None
    trial_end: datetime | None = None
    days_remaining: int = 0


class TelegramBotReferralStatsResponse(BaseModel):
    """Bot-facing referral summary."""

    total_referrals: int = 0
    bonus_days: int = 0
    referral_link: str | None = None
