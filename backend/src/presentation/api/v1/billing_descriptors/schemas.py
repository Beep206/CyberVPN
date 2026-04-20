from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BillingDescriptorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    descriptor_key: str
    merchant_profile_id: UUID
    invoice_profile_id: UUID | None
    statement_descriptor: str
    soft_descriptor: str | None
    support_phone: str | None
    support_url: str | None
    is_default: bool
    status: str
    created_at: datetime
    updated_at: datetime


class CreateBillingDescriptorRequest(BaseModel):
    descriptor_key: str = Field(..., min_length=1, max_length=50)
    merchant_profile_id: UUID
    invoice_profile_id: UUID | None = None
    statement_descriptor: str = Field(..., min_length=1, max_length=64)
    soft_descriptor: str | None = Field(None, max_length=64)
    support_phone: str | None = Field(None, max_length=32)
    support_url: str | None = Field(None, max_length=255)
    is_default: bool = False
    status: str = Field(default="active", min_length=1, max_length=20)
