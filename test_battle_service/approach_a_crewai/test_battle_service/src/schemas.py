"""Pydantic v2 request / response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class UserRegisterRequest(BaseModel):
    """Body for POST /auth/register."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"email": "user@example.com", "password": "strongpass123"}
            ]
        }
    }


class UserLoginRequest(BaseModel):
    """Body for POST /auth/login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"email": "user@example.com", "password": "strongpass123"}
            ]
        }
    }


class RefreshTokenRequest(BaseModel):
    """Body for POST /auth/refresh."""
    refresh_token: str = Field(..., description="Valid refresh JWT")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
            ]
        }
    }


class TokenVerifyRequest(BaseModel):
    """Body for POST /auth/token/verify."""
    token: str = Field(..., description="JWT to verify")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
            ]
        }
    }


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    """Public user profile (never includes password)."""
    id: int
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenPairResponse(BaseModel):
    """Access + refresh token pair returned on login."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    """Single access token returned on refresh."""
    access_token: str
    token_type: str = "bearer"


class TokenVerifyResponse(BaseModel):
    """Result of token verification."""
    valid: bool
    email: Optional[str] = None
    exp: Optional[int] = None
