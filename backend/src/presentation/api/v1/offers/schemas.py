"""Pydantic schemas for offer-layer APIs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    offer_key: str
    display_name: str
    subscription_plan_id: UUID
    included_addon_codes: list[str]
    sale_channels: list[str]
    visibility_rules: dict
    invite_bundle: dict
    trial_eligible: bool
    gift_eligible: bool
    referral_eligible: bool
    renewal_incentives: dict
    version_status: str
    effective_from: datetime
    effective_to: datetime | None
    is_active: bool


class CreateOfferRequest(BaseModel):
    offer_key: str = Field(..., min_length=1, max_length=60)
    display_name: str = Field(..., min_length=1, max_length=120)
    subscription_plan_id: UUID
    included_addon_codes: list[str] = Field(default_factory=list)
    sale_channels: list[str] = Field(default_factory=list)
    visibility_rules: dict = Field(default_factory=dict)
    invite_bundle: dict = Field(default_factory=dict)
    trial_eligible: bool = False
    gift_eligible: bool = False
    referral_eligible: bool = False
    renewal_incentives: dict = Field(default_factory=dict)
    version_status: str = "active"
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    is_active: bool = True
