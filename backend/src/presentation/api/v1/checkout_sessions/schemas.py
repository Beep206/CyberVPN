from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.presentation.api.v1.payments.schemas import CheckoutQuoteResponse


class CreateCheckoutSessionRequest(BaseModel):
    quote_session_id: UUID = Field(..., description="Source quote session identifier")


class CheckoutSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    quote_session_id: UUID
    user_id: UUID
    auth_realm_id: UUID
    storefront_id: UUID
    storefront_key: str
    merchant_profile_id: UUID | None = None
    invoice_profile_id: UUID | None = None
    billing_descriptor_id: UUID | None = None
    pricebook_id: UUID | None = None
    pricebook_key: str | None = None
    pricebook_entry_id: UUID | None = None
    offer_id: UUID | None = None
    offer_key: str | None = None
    legal_document_set_id: UUID | None = None
    legal_document_set_key: str | None = None
    program_eligibility_policy_id: UUID | None = None
    subscription_plan_id: UUID | None = None
    sale_channel: str
    currency_code: str
    status: str
    idempotency_key: str
    expires_at: datetime
    quote: CheckoutQuoteResponse
    created_at: datetime
    updated_at: datetime
