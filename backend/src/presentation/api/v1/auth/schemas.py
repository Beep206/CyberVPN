import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.domain.enums import AdminRole


class LoginRequest(BaseModel):
    login_or_email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class RegisterRequest(BaseModel):
    login: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    locale: str = Field(default="en-EN", max_length=10)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


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
    email: str
    is_active: bool = False
    is_email_verified: bool = False
    message: str = "Verification email sent. Check your inbox."
