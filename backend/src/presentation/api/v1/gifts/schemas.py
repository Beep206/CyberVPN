from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.presentation.api.v1.payments.schemas import CheckoutQuoteResponse, InvoiceResponse


class GiftPurchaseQuoteRequest(BaseModel):
    storefront_key: str | None = Field(None, min_length=1, max_length=50)
    plan_id: UUID
    use_wallet: float = Field(0, ge=0)
    currency: str = Field("USD", min_length=3, max_length=12)
    channel: str = Field("web", min_length=1, max_length=30)
    recipient_hint: str | None = Field(None, max_length=160)
    gift_message: str | None = Field(None, max_length=500)


class GiftPurchaseCommitRequest(GiftPurchaseQuoteRequest):
    pass


class GiftCodeResponse(BaseModel):
    id: UUID
    masked_code: str
    raw_code: str | None = None
    code_type: str = "gift"
    status: str
    issuer_type: str
    source_type: str | None = None
    plan_family: str | None = None
    duration_days: int | None = None
    recipient_hint: str | None = None
    gift_message: str | None = None
    expires_at: datetime | None = None
    created_at: datetime
    redeemed_at: datetime | None = None
    redeemed_by_user_id: UUID | None = None
    source_order_id: UUID | None = None
    source_payment_id: UUID | None = None


class GiftPurchaseQuoteResponse(BaseModel):
    quote: CheckoutQuoteResponse


class GiftPurchaseCommitResponse(BaseModel):
    quote: CheckoutQuoteResponse
    payment_id: UUID | None = None
    status: str
    invoice: InvoiceResponse | None = None
    gift_code: GiftCodeResponse | None = None


class GiftRedeemRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)


class GiftRedeemResponse(BaseModel):
    gift_code: GiftCodeResponse
    entitlement_grant_id: UUID
    entitlement_snapshot: dict
