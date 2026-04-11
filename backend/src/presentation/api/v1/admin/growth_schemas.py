"""Admin schemas for growth-side mobile user analytics."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AdminGrowthUserSummary(BaseModel):
    id: UUID
    email: str
    username: str | None
    telegram_username: str | None
    referral_code: str | None
    is_partner: bool


class AdminReferralCommissionRecord(BaseModel):
    id: UUID
    referrer_user_id: UUID
    referred_user_id: UUID
    payment_id: UUID
    commission_rate: float
    base_amount: float
    commission_amount: float
    currency: str
    created_at: datetime
    referrer: AdminGrowthUserSummary | None = None
    referred_user: AdminGrowthUserSummary | None = None


class AdminReferralReferrerRow(BaseModel):
    user: AdminGrowthUserSummary
    commission_count: int
    referred_users: int
    total_earned: float
    last_commission_at: datetime | None


class AdminReferralOverviewResponse(BaseModel):
    total_commissions: int
    total_earned: float
    unique_referrers: int
    unique_referred_users: int
    recent_commissions: list[AdminReferralCommissionRecord]
    top_referrers: list[AdminReferralReferrerRow]


class AdminReferralUserDetailResponse(BaseModel):
    user: AdminGrowthUserSummary
    referred_by_user_id: UUID | None
    commission_count: int
    referred_users: int
    total_earned: float
    recent_commissions: list[AdminReferralCommissionRecord]


class AdminPartnerCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    markup_pct: float
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminPartnerEarningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_user_id: UUID
    payment_id: UUID
    base_price: float
    markup_amount: float
    commission_pct: float
    commission_amount: float
    total_earning: float
    currency: str
    created_at: datetime


class AdminPartnerListItemResponse(BaseModel):
    user: AdminGrowthUserSummary
    promoted_at: datetime | None
    code_count: int
    active_code_count: int
    total_clients: int
    total_earned: float
    last_activity_at: datetime | None


class AdminPartnersListResponse(BaseModel):
    items: list[AdminPartnerListItemResponse]
    total: int
    offset: int
    limit: int


class AdminPartnerDetailResponse(AdminPartnerListItemResponse):
    codes: list[AdminPartnerCodeResponse]
    recent_earnings: list[AdminPartnerEarningResponse]

