from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.domain.enums import AdminRole
from src.shared.validators.password import validate_password_strength


class LoginRequest(BaseModel):
    login_or_email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class RegisterRequest(BaseModel):
    """Registration request with strong password policy (MED-001).

    Uses shared password validator for consistency with mobile auth.
    Supports email+password or login+password (username-only) registration.
    """

    login: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr | None = None
    password: str = Field(..., min_length=12, max_length=128)
    locale: str = Field(default="en-EN", max_length=10)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password using shared validator (MED-001)."""
        return validate_password_strength(v)


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = Field(None, min_length=1, max_length=1000)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(None, min_length=1, max_length=1000)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    login: str
    email: str | None = None
    role: AdminRole
    telegram_id: int | None = None
    is_active: bool
    is_email_verified: bool = False
    created_at: datetime


# OTP Verification schemas
class VerifyOtpRequest(BaseModel):
    """Request to verify OTP code."""

    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendOtpRequest(BaseModel):
    """Request to resend OTP code."""

    email: EmailStr


class VerifyOtpResponse(BaseModel):
    """Response for successful OTP verification with auto-login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0
    user: AdminUserResponse


class OtpErrorResponse(BaseModel):
    """Error response for OTP operations."""

    detail: str
    code: str | None = None
    attempts_remaining: int | None = None
    next_resend_available_at: datetime | None = None


class ResendOtpResponse(BaseModel):
    """Response for successful OTP resend."""

    message: str
    resends_remaining: int
    next_resend_available_at: datetime | None = None


class RegisterResponse(BaseModel):
    """Response for successful registration."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    login: str
    email: str | None = None
    is_active: bool = False
    is_email_verified: bool = False
    message: str = "Registration successful."


class LogoutAllResponse(BaseModel):
    """Response for logout-all-devices operation (HIGH-6)."""

    message: str = "All sessions terminated"
    sessions_revoked: int = 0


class MagicLinkRequest(BaseModel):
    """Request for magic link email."""

    email: EmailStr


class MagicLinkVerifyRequest(BaseModel):
    """Request to verify magic link token."""

    token: str = Field(..., min_length=1, max_length=200)


class MagicLinkVerifyOtpRequest(BaseModel):
    """Request to verify magic link via 6-digit OTP code."""

    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class MagicLinkVerifyResponse(BaseModel):
    """Response for successful magic link verification with auto-login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0
    user: AdminUserResponse


class MagicLinkResponse(BaseModel):
    """Response for magic link request (always same to prevent email enumeration)."""

    message: str = "If this email is registered, a login link has been sent."


class TelegramMiniAppRequest(BaseModel):
    """Request for Telegram Mini App authentication."""

    init_data: str = Field(..., min_length=1, max_length=4096)


class TelegramMiniAppResponse(BaseModel):
    """Response for Telegram Mini App authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0
    user: AdminUserResponse
    is_new_user: bool = False


class TelegramBotLinkRequest(BaseModel):
    """Request for Telegram bot deep-link authentication."""

    token: str = Field(..., min_length=1, max_length=200)


class TelegramBotLinkResponse(BaseModel):
    """Response for Telegram bot deep-link authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0
    user: AdminUserResponse


class GenerateLoginLinkRequest(BaseModel):
    """Request to generate a Telegram bot login link (admin/bot-only)."""

    telegram_id: int = Field(..., gt=0)


class GenerateLoginLinkResponse(BaseModel):
    """Response with the generated Telegram bot login link."""

    token: str
    url: str
    expires_at: datetime


class ForgotPasswordRequest(BaseModel):
    """Request for password reset OTP."""

    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Response for forgot-password (always same to prevent email enumeration)."""

    message: str = "If this email is registered, a password reset code has been sent."


class ResetPasswordRequest(BaseModel):
    """Request to reset password using OTP code."""

    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(..., min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate new password using shared validator (MED-001)."""
        return validate_password_strength(v)


class ResetPasswordResponse(BaseModel):
    """Response for successful password reset."""

    message: str = "Password has been reset successfully. Please login with your new password."


class DeleteAccountResponse(BaseModel):
    """Response for successful account deletion (FEAT-03)."""

    message: str = "Account has been deleted"


class ChangePasswordRequest(BaseModel):
    """Request to change user password."""

    current_password: str = Field(..., min_length=1, max_length=255)
    new_password: str = Field(..., min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate new password using shared validator (MED-001)."""
        return validate_password_strength(v)


class ChangePasswordResponse(BaseModel):
    """Response for successful password change."""

    message: str = "Password changed successfully"


class DeviceSessionResponse(BaseModel):
    """Response schema for active device session (BF2-4)."""

    model_config = ConfigDict(from_attributes=True)

    device_id: str | None = Field(None, description="Unique device identifier")
    ip_address: str | None = Field(None, description="Last known IP address")
    user_agent: str | None = Field(None, description="Browser/device user agent string")
    last_used_at: datetime = Field(..., description="Last time this session was used")
    created_at: datetime = Field(..., description="When this session was created")
    is_current: bool = Field(False, description="Whether this is the current session")


class DeviceSessionListResponse(BaseModel):
    """Response schema for list of active sessions (BF2-4)."""

    devices: list[DeviceSessionResponse] = Field(..., description="List of active sessions")
    total: int = Field(..., description="Total number of active sessions")


class RevokeDeviceResponse(BaseModel):
    """Response for successful device session revocation (BF2-4)."""

    message: str = "Device session revoked successfully"
    device_id: str = Field(..., description="ID of the revoked device")
