"""Pydantic schemas for mobile authentication API.

Request/response validation models for mobile-specific auth endpoints.
Maps to DTOs in src/application/dto/mobile_auth.py.

MED-001: Password requirements aligned with admin auth (12+ chars, complexity).
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.shared.validators.password import validate_password_strength


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
    MED-001: Password requirements aligned with admin auth.
    """

    model_config = ConfigDict(frozen=True)

    email: EmailStr = Field(
        ...,
        description="User email address (must be valid and unique)",
    )
    password: str = Field(
        ...,
        min_length=12,
        max_length=128,
        description="User password (minimum 12 characters, requires complexity)",
    )
    device: DeviceInfo = Field(
        ...,
        description="Device information for registration",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password complexity requirements (MED-001).

        Requirements aligned with admin auth:
        - Minimum 12 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        - Not in common password list
        """
        return validate_password_strength(v)


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
    is_email_verified: bool = Field(
        default=False,
        description="Whether the current email credential is considered verified in mobile auth",
    )
    is_2fa_enabled: bool = Field(
        default=False,
        description="Whether mobile TOTP protection is enabled",
    )
    linked_providers: list[str] = Field(
        default_factory=list,
        description="Linked external identity providers exposed to the mobile app",
    )
    created_at: datetime | None = Field(
        default=None,
        description="Account creation timestamp",
    )
    last_login_at: datetime | None = Field(
        default=None,
        description="Last successful login timestamp",
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

    tokens: TokenResponse | None = Field(
        default=None,
        description="Authentication tokens",
    )
    user: UserResponse | None = Field(
        default=None,
        description="User profile data",
    )
    is_new_user: bool = Field(
        default=False,
        description="True if this is a new registration",
    )
    requires_2fa: bool = Field(
        default=False,
        description="Whether the login is paused behind a pending 2FA challenge",
    )
    tfa_token: str | None = Field(
        default=None,
        description="Short-lived pending 2FA token returned when requires_2fa is true",
    )
    method: str | None = Field(
        default=None,
        description="2FA method identifier, currently `totp`",
    )


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh.

    Used by POST /api/v1/mobile/auth/refresh endpoint.
    """

    model_config = ConfigDict(frozen=True)

    refresh_token: str = Field(
        ...,
        min_length=1,
        description="Current refresh token to exchange for new tokens",
    )
    device_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="Device ID for session validation",
    )


class LogoutRequest(BaseModel):
    """Request schema for logout.

    Used by POST /api/v1/mobile/auth/logout endpoint.
    """

    model_config = ConfigDict(frozen=True)

    refresh_token: str = Field(
        ...,
        min_length=1,
        description="Refresh token to revoke",
    )
    device_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="Device ID for session revocation",
    )


class DeviceRegistrationRequest(BaseModel):
    """Request schema for device registration/update.

    Used by POST /api/v1/mobile/auth/device endpoint.
    """

    model_config = ConfigDict(frozen=True)

    device: DeviceInfo = Field(
        ...,
        description="Device information to register or update",
    )


class DeviceResponse(BaseModel):
    """Response schema for device registration.

    Returned by device registration endpoint.
    """

    model_config = ConfigDict(frozen=True)

    device_id: str = Field(
        ...,
        description="Registered device ID",
    )
    registered_at: datetime = Field(
        ...,
        description="Device registration timestamp",
    )
    last_active_at: datetime | None = Field(
        default=None,
        description="Last activity timestamp",
    )


class DeviceSessionResponse(BaseModel):
    """Response schema for mobile device/session listing."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Stable device/session identifier")
    name: str = Field(..., description="Human-readable device name")
    platform: str = Field(..., description="Platform identifier shown in the mobile UI")
    ip_address: str | None = Field(default=None, description="Last known IP address, if available")
    last_active_at: datetime | None = Field(default=None, description="Last activity timestamp")
    created_at: datetime | None = Field(default=None, description="Device registration timestamp")
    is_current: bool = Field(default=False, description="Whether this is the current device")


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


class TelegramAuthRequest(BaseModel):
    """Request schema for Telegram OAuth callback.

    Used by POST /api/v1/mobile/auth/telegram/callback endpoint.
    """

    model_config = ConfigDict(frozen=True)

    auth_data: str = Field(
        ...,
        min_length=1,
        description=(
            "Base64-encoded Telegram auth data. Contains: id, first_name, username, photo_url, auth_date, hash"
        ),
    )
    device: DeviceInfo = Field(
        ...,
        description="Device information for registration",
    )


class TelegramOIDCAuthRequest(BaseModel):
    """Request schema for Telegram OIDC ID token exchange.

    Used by POST /api/v1/mobile/auth/telegram/oidc endpoint.
    """

    model_config = ConfigDict(frozen=True)

    id_token: str = Field(
        ...,
        min_length=1,
        description="Telegram OIDC ID token returned by the native SDK",
    )
    device: DeviceInfo = Field(
        ...,
        description="Device information for registration",
    )


class MobileTwoFactorCompleteRequest(BaseModel):
    """Request schema for completing a mobile login paused behind TOTP."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="Six-digit TOTP verification code",
    )


class TelegramOIDCLinkRequest(BaseModel):
    """Request schema for authenticated Telegram account linking."""

    model_config = ConfigDict(frozen=True)

    id_token: str = Field(
        ...,
        min_length=1,
        description="Telegram OIDC ID token returned by the native SDK",
    )


class TelegramLinkResponse(BaseModel):
    """Response schema for authenticated Telegram account linking."""

    model_config = ConfigDict(frozen=True)

    linked: bool = Field(..., description="Whether the Telegram account is linked")
    provider: str = Field(..., description="External identity provider name")
    telegram_username: str | None = Field(
        default=None,
        description="Telegram username, if available",
    )
