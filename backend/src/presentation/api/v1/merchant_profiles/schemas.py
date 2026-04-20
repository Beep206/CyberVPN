from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MerchantProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_key: str
    legal_entity_name: str
    billing_descriptor: str
    invoice_profile_id: UUID | None
    settlement_reference: str | None
    supported_currencies: list[str]
    tax_behavior: dict
    refund_responsibility_model: str
    chargeback_liability_model: str
    status: str
    created_at: datetime
    updated_at: datetime


class CreateMerchantProfileRequest(BaseModel):
    profile_key: str = Field(..., min_length=1, max_length=50)
    legal_entity_name: str = Field(..., min_length=1, max_length=255)
    billing_descriptor: str = Field(..., min_length=1, max_length=64)
    invoice_profile_id: UUID | None = None
    settlement_reference: str | None = Field(None, max_length=120)
    supported_currencies: list[str] = Field(default_factory=list)
    tax_behavior: dict = Field(default_factory=dict)
    refund_responsibility_model: str = Field(default="merchant_of_record", min_length=1, max_length=50)
    chargeback_liability_model: str = Field(default="merchant_of_record", min_length=1, max_length=50)
    status: str = Field(default="active", min_length=1, max_length=20)
