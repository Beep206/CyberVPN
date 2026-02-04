"""Mobile authentication DTOs for CyberVPN mobile app.

These DTOs define the data transfer objects for mobile-specific authentication
endpoints following the Mobile-Backend Authentication Integration PRD.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


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


@dataclass(frozen=True)
class DeviceInfoDTO:
    """Device information for mobile authentication.

    Captures device fingerprint for session management and analytics.
    """

    device_id: str
    """Unique device identifier (UUID generated client-side)."""

    platform: Platform
    """Mobile platform (ios/android)."""

    platform_id: str
    """Platform-specific identifier (vendor ID for iOS, Android ID for Android)."""

    os_version: str
    """Operating system version (e.g., '17.2', '14.0')."""

    app_version: str
    """CyberVPN app version (e.g., '1.0.0')."""

    device_model: str
    """Device model name (e.g., 'iPhone 15 Pro', 'Pixel 8')."""

    push_token: str | None = None
    """Firebase Cloud Messaging token for push notifications."""


@dataclass(frozen=True)
class RegisterRequestDTO:
    """Request DTO for mobile user registration.

    Used by POST /api/v1/mobile/auth/register endpoint.
    """

    email: str
    """User email address (must be valid and unique)."""

    password: str
    """User password (minimum 8 characters, requires complexity)."""

    device: DeviceInfoDTO
    """Device information for registration."""


@dataclass(frozen=True)
class LoginRequestDTO:
    """Request DTO for mobile user login.

    Used by POST /api/v1/mobile/auth/login endpoint.
    """

    email: str
    """User email address."""

    password: str
    """User password."""

    device: DeviceInfoDTO
    """Device information for login."""

    remember_me: bool = False
    """If True, extends refresh token TTL to 30 days (default: 7 days)."""


@dataclass(frozen=True)
class RefreshTokenRequestDTO:
    """Request DTO for token refresh.

    Used by POST /api/v1/mobile/auth/refresh endpoint.
    """

    refresh_token: str
    """Current refresh token to exchange for new tokens."""

    device_id: str
    """Device ID for session validation."""


@dataclass(frozen=True)
class LogoutRequestDTO:
    """Request DTO for logout.

    Used by POST /api/v1/mobile/auth/logout endpoint.
    """

    refresh_token: str
    """Refresh token to revoke."""

    device_id: str
    """Device ID for session revocation."""


@dataclass(frozen=True)
class TokenResponseDTO:
    """Response DTO for authentication tokens.

    Returned by login, register, and refresh endpoints.
    """

    access_token: str
    """JWT access token (TTL: 15 minutes)."""

    refresh_token: str
    """JWT refresh token (TTL: 7 days or 30 days with remember_me)."""

    token_type: str = "Bearer"
    """Token type for Authorization header."""

    expires_in: int = 900
    """Access token expiration in seconds (default: 15 minutes)."""


@dataclass(frozen=True)
class SubscriptionInfoDTO:
    """User subscription information.

    Included in authentication responses for mobile-optimized data loading.
    """

    status: SubscriptionStatus
    """Current subscription status."""

    plan_name: str | None = None
    """Name of the subscription plan (if active)."""

    expires_at: datetime | None = None
    """Subscription expiration date (if applicable)."""

    traffic_limit_bytes: int | None = None
    """Traffic limit in bytes (if applicable)."""

    used_traffic_bytes: int | None = None
    """Used traffic in bytes (if applicable)."""

    auto_renew: bool = False
    """Whether subscription auto-renews."""


@dataclass(frozen=True)
class UserResponseDTO:
    """Response DTO for authenticated user profile.

    Used by GET /api/v1/mobile/auth/me and included in login/register responses.
    """

    id: UUID
    """User UUID."""

    email: str
    """User email address."""

    username: str | None = None
    """Optional username."""

    status: str = "active"
    """User account status."""

    telegram_id: int | None = None
    """Linked Telegram user ID (if connected)."""

    telegram_username: str | None = None
    """Linked Telegram username (if connected)."""

    created_at: datetime | None = None
    """Account creation timestamp."""

    subscription: SubscriptionInfoDTO | None = None
    """Subscription information (included in mobile responses)."""


@dataclass(frozen=True)
class AuthResponseDTO:
    """Combined authentication response with tokens and user data.

    Used by login and register endpoints for mobile-optimized single response.
    """

    tokens: TokenResponseDTO
    """Authentication tokens."""

    user: UserResponseDTO
    """User profile data."""

    is_new_user: bool = False
    """True if this is a new registration."""


@dataclass(frozen=True)
class DeviceRegistrationRequestDTO:
    """Request DTO for device registration/update.

    Used by POST /api/v1/mobile/auth/device endpoint.
    """

    device: DeviceInfoDTO
    """Device information to register or update."""


@dataclass(frozen=True)
class DeviceResponseDTO:
    """Response DTO for device registration.

    Returned by device registration endpoint.
    """

    device_id: str
    """Registered device ID."""

    registered_at: datetime
    """Device registration timestamp."""

    last_active_at: datetime | None = None
    """Last activity timestamp."""


@dataclass(frozen=True)
class TelegramAuthRequestDTO:
    """Request DTO for Telegram OAuth callback.

    Used by POST /api/v1/mobile/auth/telegram/callback endpoint.
    """

    auth_data: str
    """Base64-encoded Telegram auth data with HMAC signature."""

    device: DeviceInfoDTO
    """Device information for login."""


@dataclass(frozen=True)
class TelegramUserDataDTO:
    """Parsed Telegram user data from OAuth callback.

    Extracted from validated auth_data.
    """

    id: int
    """Telegram user ID."""

    first_name: str
    """Telegram first name."""

    last_name: str | None = None
    """Telegram last name (optional)."""

    username: str | None = None
    """Telegram username (optional)."""

    photo_url: str | None = None
    """Telegram profile photo URL (optional)."""

    auth_date: datetime | None = None
    """Authentication timestamp from Telegram."""


@dataclass(frozen=True)
class MobileAuthErrorDTO:
    """Error response DTO for mobile authentication.

    Standardized error format for mobile clients.
    """

    code: str
    """Error code for client-side handling.

    Possible values:
    - INVALID_CREDENTIALS: Wrong email/password
    - EMAIL_EXISTS: Email already registered
    - EMAIL_NOT_FOUND: Email not in database
    - INVALID_TOKEN: Token is invalid or malformed
    - TOKEN_EXPIRED: Token has expired
    - DEVICE_NOT_REGISTERED: Device ID not found
    - RATE_LIMITED: Too many requests
    - INVALID_TELEGRAM_AUTH: Invalid Telegram signature
    - TELEGRAM_AUTH_EXPIRED: Telegram auth_date too old
    - ACCOUNT_DISABLED: User account is disabled
    - VALIDATION_ERROR: Request validation failed
    """

    message: str
    """Human-readable error message."""

    details: dict | None = None
    """Additional error details (e.g., validation errors)."""
