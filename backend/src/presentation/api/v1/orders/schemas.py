from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateOrderFromCheckoutRequest(BaseModel):
    checkout_session_id: UUID = Field(..., description="Committed checkout session identifier")


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    order_id: UUID
    item_type: str
    subject_id: UUID | None = None
    subject_code: str | None = None
    display_name: str
    quantity: int
    unit_price: float
    total_price: float
    currency_code: str
    item_snapshot: dict
    created_at: datetime
    updated_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    quote_session_id: UUID | None = None
    checkout_session_id: UUID
    user_id: UUID
    auth_realm_id: UUID
    storefront_id: UUID
    merchant_profile_id: UUID | None = None
    invoice_profile_id: UUID | None = None
    billing_descriptor_id: UUID | None = None
    pricebook_id: UUID | None = None
    pricebook_entry_id: UUID | None = None
    offer_id: UUID | None = None
    legal_document_set_id: UUID | None = None
    program_eligibility_policy_id: UUID | None = None
    subscription_plan_id: UUID | None = None
    promo_code_id: UUID | None = None
    partner_code_id: UUID | None = None
    sale_channel: str
    currency_code: str
    order_status: str
    settlement_status: str
    base_price: float
    addon_amount: float
    displayed_price: float
    discount_amount: float
    wallet_amount: float
    gateway_amount: float
    partner_markup: float
    commission_base_amount: float
    merchant_snapshot: dict
    pricing_snapshot: dict
    policy_snapshot: dict
    entitlements_snapshot: dict
    items: list[OrderItemResponse]
    created_at: datetime
    updated_at: datetime
