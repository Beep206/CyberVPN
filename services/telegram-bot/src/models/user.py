"""User DTO models for telegram-bot service.

This module contains Pydantic models for user-related data transfer objects
that match the Backend API responses.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class UserStatus(StrEnum):
    """User account status enumeration."""

    ACTIVE = "active"
    EXPIRED = "expired"
    LIMITED = "limited"
    DISABLED = "disabled"
    NONE = "none"


class UserDTO(BaseModel):
    """Base user data transfer object matching Backend API responses.

    Attributes:
        uuid: Unique user identifier (UUID string)
        telegram_id: Telegram user ID
        username: Telegram username (optional)
        first_name: User's first name (optional)
        language: User's language preference (ISO code)
        status: Current user account status
        is_admin: Whether user has admin privileges
        personal_discount: Personal discount percentage (0-100)
        next_purchase_discount: Next purchase discount percentage (0-100)
        referrer_id: Telegram ID of the user who referred this user (optional)
        points: User's accumulated loyalty points
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    uuid: str = Field(..., description="Unique user identifier")
    telegram_id: int = Field(..., description="Telegram user ID")
    username: str | None = Field(None, description="Telegram username")
    first_name: str | None = Field(None, description="User's first name")
    language: str = Field(default="en", description="User's language preference")
    status: UserStatus = Field(default=UserStatus.NONE, description="User account status")
    is_admin: bool = Field(default=False, description="Admin privileges flag")
    personal_discount: float = Field(default=0.0, ge=0, le=100, description="Personal discount percentage")
    next_purchase_discount: float = Field(default=0.0, ge=0, le=100, description="Next purchase discount percentage")
    referrer_id: int | None = Field(None, description="Referrer's Telegram ID")
    points: int = Field(default=0, ge=0, description="Loyalty points")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class UserProfile(BaseModel):
    """Extended user profile with subscription details.

    Extends UserDTO with additional subscription and usage information.

    Attributes:
        All fields from UserDTO plus:
        plan_name: Current subscription plan name (optional)
        traffic_used_bytes: Total traffic used in bytes
        traffic_limit_bytes: Traffic limit in bytes (-1 for unlimited)
        days_remaining: Days remaining in current subscription (optional)
        device_count: Number of connected devices
        device_limit: Maximum allowed devices (-1 for unlimited)
        subscription_status: Current subscription status
        reset_strategy: Traffic reset strategy (optional)
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    # User base fields
    uuid: str = Field(..., description="Unique user identifier")
    telegram_id: int = Field(..., description="Telegram user ID")
    username: str | None = Field(None, description="Telegram username")
    first_name: str | None = Field(None, description="User's first name")
    language: str = Field(default="en", description="User's language preference")
    status: UserStatus = Field(default=UserStatus.NONE, description="User account status")
    is_admin: bool = Field(default=False, description="Admin privileges flag")
    personal_discount: float = Field(default=0.0, ge=0, le=100, description="Personal discount percentage")
    next_purchase_discount: float = Field(default=0.0, ge=0, le=100, description="Next purchase discount percentage")
    referrer_id: int | None = Field(None, description="Referrer's Telegram ID")
    points: int = Field(default=0, ge=0, description="Loyalty points")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Subscription fields
    plan_name: str | None = Field(None, description="Current subscription plan name")
    traffic_used_bytes: int = Field(default=0, ge=0, description="Total traffic used in bytes")
    traffic_limit_bytes: int = Field(default=-1, ge=-1, description="Traffic limit in bytes (-1 for unlimited)")
    days_remaining: int | None = Field(None, ge=0, description="Days remaining in subscription")
    device_count: int = Field(default=0, ge=0, description="Number of connected devices")
    device_limit: int = Field(default=-1, ge=-1, description="Maximum allowed devices (-1 for unlimited)")
    subscription_status: UserStatus = Field(default=UserStatus.NONE, description="Subscription status")
    reset_strategy: str | None = Field(None, description="Traffic reset strategy")
