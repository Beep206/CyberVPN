"""Checkout session domain entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class CheckoutSession:
    id: UUID
    quote_session_id: UUID
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
    currency_code: str
    sale_channel: str
    checkout_status: str
    idempotency_key: str
    request_snapshot: dict[str, Any]
    checkout_snapshot: dict[str, Any]
    context_snapshot: dict[str, Any]
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    promo_code_id: UUID | None = None
    partner_code_id: UUID | None = None
