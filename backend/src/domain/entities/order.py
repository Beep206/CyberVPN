"""Canonical order domain entities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Order:
    id: UUID
    quote_session_id: UUID | None
    checkout_session_id: UUID
    user_id: UUID
    auth_realm_id: UUID
    storefront_id: UUID
    merchant_profile_id: UUID | None
    invoice_profile_id: UUID | None
    billing_descriptor_id: UUID | None
    pricebook_id: UUID | None
    pricebook_entry_id: UUID | None
    offer_id: UUID | None
    legal_document_set_id: UUID | None
    program_eligibility_policy_id: UUID | None
    subscription_plan_id: UUID | None
    promo_code_id: UUID | None
    partner_code_id: UUID | None
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
    merchant_snapshot: dict[str, Any]
    pricing_snapshot: dict[str, Any]
    policy_snapshot: dict[str, Any]
    entitlements_snapshot: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class OrderItem:
    id: UUID
    order_id: UUID
    item_type: str
    subject_id: UUID | None
    subject_code: str | None
    display_name: str
    quantity: int
    unit_price: float
    total_price: float
    currency_code: str
    item_snapshot: dict[str, Any]
    created_at: datetime
    updated_at: datetime
