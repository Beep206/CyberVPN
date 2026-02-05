import re
from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.domain.enums import AdminRole


class LoginRequest(BaseModel):
    login_or_email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class RegisterRequest(BaseModel):
    """Registration request with strong password policy (MED-4)."""

    login: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)  # MED-4: Increased to 12 chars
    locale: str = Field(default="en-EN", max_length=10)

    # MED-4: Common passwords to reject (top 100 most common)
    COMMON_PASSWORDS: ClassVar[frozenset[str]] = frozenset({
        "password", "123456", "12345678", "qwerty", "abc123", "monkey", "1234567",
        "letmein", "trustno1", "dragon", "baseball", "iloveyou", "master", "sunshine",
        "ashley", "bailey", "shadow", "123123", "654321", "superman", "qazwsx",
        "michael", "football", "password1", "password123", "welcome", "welcome1",
        "admin", "login", "admin123", "root", "toor", "pass", "test", "guest",
        "changeme", "passw0rd", "12345", "123456789", "1234567890", "0987654321",
        "qwertyuiop", "password1!", "P@ssw0rd", "P@ssword1", "Password1",
    })

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets strong policy requirements (MED-4).

        Requirements:
        - Minimum 12 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        - Not in common passwords list
        """
        # Check minimum complexity
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/`~]", v):
            raise ValueError("Password must contain at least one special character")

        # Check against common passwords
        if v.lower() in cls.COMMON_PASSWORDS:
            raise ValueError("Password is too common, please choose a stronger password")

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


class LogoutAllResponse(BaseModel):
    """Response for logout-all-devices operation (HIGH-6)."""

    message: str = "All sessions terminated"
    sessions_revoked: int = 0
