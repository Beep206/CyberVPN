"""Pydantic v2 schemas for the referral API."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReferralAttributionCaptureRequest(BaseModel):
    referral_code: str = Field(..., min_length=4, max_length=64)
    source_host: str | None = Field(default=None, max_length=255)
    source_path: str | None = Field(default=None, max_length=500)
    campaign_params: dict[str, Any] = Field(default_factory=dict)


class ReferralAttributionCaptureResponse(BaseModel):
    status: Literal["captured"] = "captured"
    attribution_id: UUID
    captured_at: datetime
    expires_at: datetime
    masked_code: str


class ReferralAttributionClaimRequest(BaseModel):
    fallback_referral_code: str | None = Field(default=None, min_length=4, max_length=64)


class ReferralAttributionClaimResponse(BaseModel):
    status: Literal["claimed", "already_claimed", "no_pending"]
    referrer_user_id: UUID | None = None
    claimed_at: datetime | None = None


class ReferralStatusResponse(BaseModel):
    enabled: bool
    commission_rate: float
    friend_discount_pct: float | None = None
    reward_hold_days: int | None = None


class ReferralCodeResponse(BaseModel):
    referral_code: str


class ReferralStatsResponse(BaseModel):
    total_referrals: int
    total_earned: float
    commission_rate: float
    pending_rewards_usd: float = 0
    available_rewards_usd: float = 0
    reversed_rewards_usd: float = 0
    monthly_cap_used_usd: float = 0
    lifetime_cap_used_usd: float = 0
    qualifying_orders: int = 0


class ReferralCommissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    referred_user_id: UUID
    commission_amount: float
    base_amount: float
    commission_rate: float
    currency: str = "USD"
    reward_status: str | None = None
    hold_until: datetime | None = None
    available_at: datetime | None = None
    reversed_at: datetime | None = None
    source_model: str = "legacy_commission"
    created_at: datetime


class ReferralRewardResponse(BaseModel):
    id: UUID
    referred_user_id: UUID | None = None
    reward_amount: float
    currency: str = "USD"
    reward_status: str
    hold_until: datetime | None = None
    available_at: datetime | None = None
    reversed_at: datetime | None = None
    created_at: datetime
