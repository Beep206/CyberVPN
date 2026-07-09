from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.presentation.api.v1.payments.schemas import (
    CheckoutAddonRequest,
    CheckoutQuoteResponse,
)


class QuoteCodeBasketItemRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    client_slot_id: str | None = Field(default=None, min_length=1, max_length=80)


class CreateQuoteSessionRequest(BaseModel):
    storefront_key: str | None = Field(default=None, min_length=1, max_length=50)
    pricebook_key: str | None = Field(default=None, min_length=1, max_length=60)
    offer_key: str | None = Field(default=None, min_length=1, max_length=60)
    plan_id: UUID
    addons: list[CheckoutAddonRequest] = Field(default_factory=list)
    code_input: str | None = Field(default=None, max_length=64)
    promo_code: str | None = Field(default=None, max_length=50)
    partner_code: str | None = Field(default=None, max_length=30)
    codes: list["QuoteCodeBasketItemRequest"] = Field(default_factory=list, max_length=5)
    private_catalog_grant_id: UUID | None = None
    use_wallet: float = Field(0, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=12)
    channel: str = Field(default="web", min_length=1, max_length=30)

    @field_validator("currency")
    @classmethod
    def validate_currency_uppercase(cls, value: str) -> str:
        if not value.isupper():
            raise ValueError("Currency code must be uppercase")
        return value

    @model_validator(mode="after")
    def validate_code_inputs_are_not_mixed(self) -> "CreateQuoteSessionRequest":
        if self.codes and (self.code_input or self.promo_code or self.partner_code):
            raise ValueError("codes cannot be combined with code_input, promo_code, or partner_code")
        return self


class QuoteSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
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
    expires_at: datetime
    quote: CheckoutQuoteResponse
    created_at: datetime
    updated_at: datetime
