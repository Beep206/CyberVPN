from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# --- Request Schemas ---

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenVerifyRequest(BaseModel):
    token: str


# --- Response Schemas ---

class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenVerifyResponse(BaseModel):
    valid: bool
    email: Optional[str] = None
    exp: Optional[int] = None
