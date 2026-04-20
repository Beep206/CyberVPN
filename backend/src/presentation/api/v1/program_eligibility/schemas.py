"""Pydantic schemas for explicit program eligibility policies."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProgramEligibilityPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_key: str
    subject_type: str
    subscription_plan_id: UUID | None
    plan_addon_id: UUID | None
    offer_id: UUID | None
    invite_allowed: bool
    referral_credit_allowed: bool
    creator_affiliate_allowed: bool
    performance_allowed: bool
    reseller_allowed: bool
    renewal_commissionable: bool
    addon_commissionable: bool
    version_status: str
    effective_from: datetime
    effective_to: datetime | None
    is_active: bool


class CreateProgramEligibilityPolicyRequest(BaseModel):
    policy_key: str = Field(..., min_length=1, max_length=60)
    subject_type: str = Field(..., min_length=1, max_length=20)
    subscription_plan_id: UUID | None = None
    plan_addon_id: UUID | None = None
    offer_id: UUID | None = None
    invite_allowed: bool = False
    referral_credit_allowed: bool = False
    creator_affiliate_allowed: bool = False
    performance_allowed: bool = False
    reseller_allowed: bool = False
    renewal_commissionable: bool = False
    addon_commissionable: bool = False
    version_status: str = "active"
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    is_active: bool = True
