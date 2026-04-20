"""Pydantic schemas for pricebook APIs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PricebookEntryRequest(BaseModel):
    offer_id: UUID
    visible_price: float = Field(..., ge=0)
    compare_at_price: float | None = Field(None, ge=0)
    included_addon_codes: list[str] = Field(default_factory=list)
    display_order: int = Field(default=0, ge=0)


class PricebookEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    offer_id: UUID
    visible_price: float
    compare_at_price: float | None
    included_addon_codes: list[str]
    display_order: int


class PricebookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pricebook_key: str
    display_name: str
    storefront_id: UUID
    merchant_profile_id: UUID | None
    currency_code: str
    region_code: str | None
    discount_rules: dict
    renewal_pricing_policy: dict
    version_status: str
    effective_from: datetime
    effective_to: datetime | None
    is_active: bool
    entries: list[PricebookEntryResponse]


class CreatePricebookRequest(BaseModel):
    pricebook_key: str = Field(..., min_length=1, max_length=60)
    display_name: str = Field(..., min_length=1, max_length=120)
    storefront_id: UUID
    merchant_profile_id: UUID | None = None
    currency_code: str = Field(default="USD", min_length=3, max_length=3)
    region_code: str | None = Field(None, min_length=2, max_length=16)
    discount_rules: dict = Field(default_factory=dict)
    renewal_pricing_policy: dict = Field(default_factory=dict)
    version_status: str = "active"
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    is_active: bool = True
    entries: list[PricebookEntryRequest] = Field(default_factory=list, min_length=1)
