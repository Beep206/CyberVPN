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
    refresh_token: str = Field(..., min_length=1, max_length=1000)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, max_length=1000)


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


class MagicLinkResponse(BaseModel):
    """Response for magic link request (always same to prevent email enumeration)."""

    message: str = "If this email is registered, a login link has been sent."
