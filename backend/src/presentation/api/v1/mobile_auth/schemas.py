"""Pydantic schemas for mobile authentication API.

Request/response validation models for mobile-specific auth endpoints.
Maps to DTOs in src/application/dto/mobile_auth.py.
"""

import re  # noqa: F401
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Platform(StrEnum):
    """Mobile platform identifiers."""

    IOS = "ios"
    ANDROID = "android"


class SubscriptionStatus(StrEnum):
    """User subscription status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    TRIAL = "trial"
    CANCELLED = "cancelled"
    NONE = "none"


class DeviceInfo(BaseModel):
    """Device information for mobile authentication.

    Captures device fingerprint for session management and analytics.
    """

    model_config = ConfigDict(frozen=True)

    device_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="Unique device identifier (UUID generated client-side)",
    )
    platform: Platform = Field(
        ...,
        description="Mobile platform (ios/android)",
    )
    platform_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Platform-specific identifier (vendor ID for iOS, Android ID)",
    )
    os_version: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Operating system version (e.g., '17.2', '14.0')",
    )
    app_version: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="CyberVPN app version (e.g., '1.0.0')",
    )
    device_model: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Device model name (e.g., 'iPhone 15 Pro', 'Pixel 8')",
    )
    push_token: str | None = Field(
        default=None,
        max_length=512,
        description="Firebase Cloud Messaging token for push notifications",
    )


class RegisterRequest(BaseModel):
    """Request schema for mobile user registration.

    Used by POST /api/v1/mobile/auth/register endpoint.
    """

    model_config = ConfigDict(frozen=True)

    email: EmailStr = Field(
        ...,
        description="User email address (must be valid and unique)",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (minimum 8 characters, requires complexity)",
    )
    device: DeviceInfo = Field(
        ...,
        description="Device information for registration",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password complexity requirements.

        Requirements:
        - At least 8 characters
        - At least one letter
        - At least one digit
        """
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    """Request schema for mobile user login.

    Used by POST /api/v1/mobile/auth/login endpoint.
    """

    model_config = ConfigDict(frozen=True)

    email: EmailStr = Field(
        ...,
        description="User email address",
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="User password",
    )
    device: DeviceInfo = Field(
        ...,
        description="Device information for login",
    )
    remember_me: bool = Field(
        default=False,
        description="If True, extends refresh token TTL to 30 days (default: 7 days)",
    )


class SubscriptionInfo(BaseModel):
    """User subscription information.

    Included in authentication responses for mobile-optimized data loading.
    """

    model_config = ConfigDict(frozen=True)

    status: SubscriptionStatus = Field(
        ...,
        description="Current subscription status",
    )
    plan_name: str | None = Field(
        default=None,
        description="Name of the subscription plan (if active)",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Subscription expiration date (if applicable)",
    )
    traffic_limit_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Traffic limit in bytes (if applicable)",
    )
    used_traffic_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Used traffic in bytes (if applicable)",
    )
    auto_renew: bool = Field(
        default=False,
        description="Whether subscription auto-renews",
    )


class UserResponse(BaseModel):
    """Response schema for authenticated user profile.

    Used by GET /api/v1/mobile/auth/me and included in login/register responses.
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID = Field(
        ...,
        description="User UUID",
    )
    email: str = Field(
        ...,
        description="User email address",
    )
    username: str | None = Field(
        default=None,
        description="Optional username",
    )
    status: str = Field(
        default="active",
        description="User account status",
    )
    telegram_id: int | None = Field(
        default=None,
        description="Linked Telegram user ID (if connected)",
    )
    telegram_username: str | None = Field(
        default=None,
        description="Linked Telegram username (if connected)",
    )
    created_at: datetime | None = Field(
        default=None,
        description="Account creation timestamp",
    )
    subscription: SubscriptionInfo | None = Field(
        default=None,
        description="Subscription information (included in mobile responses)",
    )


class TokenResponse(BaseModel):
    """Response schema for authentication tokens.

    Returned by login, register, and refresh endpoints.
    """

    model_config = ConfigDict(frozen=True)

    access_token: str = Field(
        ...,
        description="JWT access token (TTL: 15 minutes)",
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token (TTL: 7 days or 30 days with remember_me)",
    )
    token_type: str = Field(
        default="Bearer",
        description="Token type for Authorization header",
    )
    expires_in: int = Field(
        default=900,
        ge=0,
        description="Access token expiration in seconds (default: 15 minutes)",
    )


class AuthResponse(BaseModel):
    """Combined authentication response with tokens and user data.

    Used by login and register endpoints for mobile-optimized single response.
    """

    model_config = ConfigDict(frozen=True)

    tokens: TokenResponse = Field(
        ...,
        description="Authentication tokens",
    )
    user: UserResponse = Field(
        ...,
        description="User profile data",
    )
    is_new_user: bool = Field(
        default=False,
        description="True if this is a new registration",
    )


class MobileAuthError(BaseModel):
    """Error response schema for mobile authentication.

    Standardized error format for mobile clients.
    """

    model_config = ConfigDict(frozen=True)

    code: str = Field(
        ...,
        description="Error code for client-side handling",
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
    )
    details: dict | None = Field(
        default=None,
        description="Additional error details (e.g., validation errors)",
    )
