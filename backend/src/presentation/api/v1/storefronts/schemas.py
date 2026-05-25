from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StorefrontRouteContractResponse(BaseModel):
    storefront_key: str
    host: str
    preview_api_path: str
    customer_entry_path: str
    route_status: Literal["preview", "inactive"]
    public_launch_requires_stages: list[str] = Field(default_factory=list)
    checkout_side_effects: bool = False


class StorefrontBrandingBoundaryResponse(BaseModel):
    brand_id: UUID
    brand_key: str
    brand_display_name: str
    brand_status: str
    allowed_customizations: list[str] = Field(default_factory=list)
    prohibited_claims: list[str] = Field(default_factory=list)
    legal_copy_source: str


class StorefrontPricingOfferResponse(BaseModel):
    pricebook_id: UUID
    pricebook_key: str
    pricebook_display_name: str
    currency_code: str
    region_code: str | None = None
    offer_id: UUID
    offer_key: str
    offer_display_name: str
    plan_id: UUID
    visible_price: float
    compare_at_price: float | None = None
    sale_channels: list[str] = Field(default_factory=list)
    pricing_source: Literal["storefront_pricebook"] = "storefront_pricebook"


class StorefrontPricingBoundaryResponse(BaseModel):
    display_policy: str
    finance_policy: str
    offers: list[StorefrontPricingOfferResponse] = Field(default_factory=list)


class StorefrontAttributionContractResponse(BaseModel):
    owner_type: Literal["direct_store", "affiliate", "reseller"]
    owner_source: Literal["none", "explicit_code"]
    partner_account_id: UUID | None = None
    partner_account_key: str | None = None
    partner_account_status: str | None = None
    partner_code_id: UUID | None = None
    partner_code: str | None = None
    partner_code_required_for_reseller: bool
    touchpoint_policy: str


class StorefrontAnalyticsContractResponse(BaseModel):
    preview_records_touchpoint: bool = False
    checkout_records_storefront_origin: bool
    checkout_records_explicit_code: bool
    expected_dimensions: list[str] = Field(default_factory=list)


class StorefrontPreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    storefront_id: UUID
    storefront_key: str
    display_name: str
    status: str
    route_contract: StorefrontRouteContractResponse
    branding_boundary: StorefrontBrandingBoundaryResponse
    pricing_boundary: StorefrontPricingBoundaryResponse
    attribution_contract: StorefrontAttributionContractResponse
    analytics_contract: StorefrontAnalyticsContractResponse
    generated_at: datetime
