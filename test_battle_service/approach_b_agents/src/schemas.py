from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(
        ..., min_length=8, description="Password must be at least 8 characters"
    )


class UserLoginRequest(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user data returned in responses. Password is never included."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_active: bool
    created_at: datetime


class TokenPairResponse(BaseModel):
    """Schema for login response containing both access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    """Schema for refresh response containing only a new access token."""

    access_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str


class TokenVerifyRequest(BaseModel):
    """Schema for token verification request."""

    token: str


class TokenVerifyResponse(BaseModel):
    """Schema for token verification response."""

    valid: bool
    email: str | None = None
    exp: int | None = None
