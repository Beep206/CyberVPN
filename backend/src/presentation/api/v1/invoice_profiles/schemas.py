from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InvoiceProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_key: str
    display_name: str
    issuer_legal_name: str
    tax_identifier: str | None
    issuer_email: str | None
    tax_behavior: dict
    invoice_footer: str | None
    receipt_footer: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class CreateInvoiceProfileRequest(BaseModel):
    profile_key: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=120)
    issuer_legal_name: str = Field(..., min_length=1, max_length=255)
    tax_identifier: str | None = Field(None, max_length=64)
    issuer_email: str | None = Field(None, max_length=255)
    tax_behavior: dict = Field(default_factory=dict)
    invoice_footer: str | None = Field(None, max_length=500)
    receipt_footer: str | None = Field(None, max_length=500)
    status: str = Field(default="active", min_length=1, max_length=20)
