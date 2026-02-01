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
    created_at: datetime
