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
    expires_at: datetime | None = Field(
        None, description="Subscription expiration date"
    )
    subscription_url: str = Field(
        ..., max_length=5000, description="VPN subscription configuration URL"
    )


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

    plan_name: str = Field(
        ..., max_length=100, description="Name of the subscription plan"
    )
    duration_days: int = Field(
        ..., gt=0, le=3650, description="Subscription duration in days"
    )


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

    config_string: str = Field(
        ..., max_length=5000, description="VPN configuration string"
    )
    client_type: str = Field(
        ..., max_length=50, description="VPN client type (vless, vmess, etc.)"
    )


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
    message: str = Field(
        ..., min_length=1, max_length=4096, description="Notification message"
    )
    notification_type: str | None = Field(
        None,
        max_length=50,
        description="Type of notification (info, warning, error)",
    )
