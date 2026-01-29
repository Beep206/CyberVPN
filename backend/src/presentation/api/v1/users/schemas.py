"""User API schemas for Remnawave VPN users."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.domain.enums import UserStatus


class CreateUserRequest(BaseModel):
    """Request schema for creating a new VPN user."""

    username: str = Field(..., min_length=3, max_length=50)
    password: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    data_limit: Optional[int] = Field(None, ge=0, le=1_099_511_627_776)  # max 1 TB
    expire_at: Optional[datetime] = None


class UpdateUserRequest(BaseModel):
    """Request schema for updating a VPN user."""

    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    data_limit: Optional[int] = Field(None, ge=0, le=1_099_511_627_776)
    expire_at: Optional[datetime] = None


class UserResponse(BaseModel):
    """Response schema for a single VPN user."""

    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    username: str
    status: UserStatus
    short_uuid: str
    created_at: datetime
    updated_at: datetime
    subscription_uuid: Optional[UUID] = None
    expire_at: Optional[datetime] = None
    traffic_limit_bytes: Optional[int] = None
    used_traffic_bytes: Optional[int] = None
    email: Optional[str] = None
    telegram_id: Optional[int] = None


class UserListResponse(BaseModel):
    """Response schema for a list of VPN users."""

    model_config = ConfigDict(from_attributes=True)

    users: list[UserResponse]
    total: int
    page: int
    page_size: int


class BulkUserActionRequest(BaseModel):
    """Request schema for bulk user actions."""

    user_ids: list[UUID] = Field(..., min_length=1, max_length=100)
