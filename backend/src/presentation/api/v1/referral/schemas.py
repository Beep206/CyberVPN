"""Pydantic v2 schemas for the referral API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReferralStatusResponse(BaseModel):
    enabled: bool
    commission_rate: float


class ReferralCodeResponse(BaseModel):
    referral_code: str


class ReferralStatsResponse(BaseModel):
    total_referrals: int
    total_earned: float
    commission_rate: float


class ReferralCommissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    referred_user_id: UUID
    commission_amount: float
    base_amount: float
    commission_rate: float
    created_at: datetime
