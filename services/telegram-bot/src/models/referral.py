"""Referral DTO models for telegram-bot service.

This module contains Pydantic models for referral system data including
referral statistics and reward configurations.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class RewardType(StrEnum):
    """Referral reward type enumeration."""

    POINTS = "points"
    EXTRA_DAYS = "extra_days"


class RewardStrategy(StrEnum):
    """Referral reward strategy enumeration."""

    ON_FIRST_PAYMENT = "on_first_payment"
    ON_EACH_PAYMENT = "on_each_payment"


class RewardForm(StrEnum):
    """Referral reward form enumeration."""

    AMOUNT = "amount"
    PERCENT = "percent"


class ReferralUser(BaseModel):
    """Simplified referral user information.

    Attributes:
        telegram_id: Referred user's Telegram ID
        username: Referred user's username
        first_name: Referred user's first name
        joined_at: Timestamp when user joined via referral
        has_paid: Whether the referred user has made a payment
        total_payments: Total number of payments made by referred user
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    telegram_id: int = Field(..., description="Telegram ID")
    username: str | None = Field(None, description="Username")
    first_name: str | None = Field(None, description="First name")
    joined_at: datetime = Field(..., description="Join timestamp")
    has_paid: bool = Field(default=False, description="Payment status")
    total_payments: Annotated[int, Field(ge=0, description="Total payments count")]


class ReferralStats(BaseModel):
    """Referral statistics for a user.

    Attributes:
        total_invited: Total number of invited users
        total_paid: Number of invited users who made payments
        points_earned: Total loyalty points earned from referrals
        recent_referrals: List of recent referral users (limited to last N)
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    total_invited: Annotated[int, Field(ge=0, description="Total invited users")]
    total_paid: Annotated[int, Field(ge=0, description="Invited users who paid")]
    points_earned: Annotated[int, Field(ge=0, description="Total points earned from referrals")]
    recent_referrals: list[ReferralUser] = Field(default_factory=list, description="Recent referral users")


class ReferralReward(BaseModel):
    """Referral reward configuration.

    Attributes:
        reward_type: Type of reward (points or extra days)
        strategy: When reward is given (first payment or each payment)
        form: How reward value is calculated (fixed amount or percentage)
        value: Reward value (points amount, days, or percentage)
        description: Human-readable reward description
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    reward_type: RewardType = Field(..., description="Reward type")
    strategy: RewardStrategy = Field(..., description="Reward strategy")
    form: RewardForm = Field(..., description="Reward form (amount or percent)")
    value: Annotated[float, Field(gt=0, description="Reward value")]
    description: str | None = Field(None, description="Reward description")


class ReferralDTO(BaseModel):
    """Complete referral data transfer object.

    Attributes:
        user_uuid: UUID of the referrer
        telegram_id: Telegram ID of the referrer
        referral_code: Unique referral code
        stats: Referral statistics
        rewards: List of active reward configurations
        is_active: Whether referral program is active for this user
        created_at: Referral code creation timestamp
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    user_uuid: str = Field(..., description="Referrer UUID")
    telegram_id: int = Field(..., description="Referrer Telegram ID")
    referral_code: str = Field(..., min_length=4, description="Unique referral code")
    stats: ReferralStats = Field(..., description="Referral statistics")
    rewards: list[ReferralReward] = Field(default_factory=list, description="Active reward configurations")
    is_active: bool = Field(default=True, description="Referral program active status")
    created_at: datetime = Field(..., description="Creation timestamp")
