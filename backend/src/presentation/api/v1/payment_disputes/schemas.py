from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UpsertPaymentDisputeRequest(BaseModel):
    order_id: UUID
    payment_attempt_id: UUID | None = None
    payment_id: UUID | None = None
    provider: str | None = Field(default=None, max_length=30)
    external_reference: str | None = Field(default=None, max_length=255)
    subtype: str = Field(..., min_length=1, max_length=40)
    outcome_class: str = Field(..., min_length=1, max_length=20)
    lifecycle_status: str = Field(..., min_length=1, max_length=40)
    disputed_amount: float = Field(..., gt=0)
    fee_amount: float = Field(default=0, ge=0)
    fee_status: str = Field(default="none", min_length=1, max_length=40)
    currency_code: str | None = Field(default=None, max_length=12)
    reason_code: str | None = Field(default=None, max_length=80)
    evidence_snapshot: dict = Field(default_factory=dict)
    provider_snapshot: dict = Field(default_factory=dict)
    opened_at: datetime | None = None
    closed_at: datetime | None = None


class PaymentDisputeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    order_id: UUID
    payment_attempt_id: UUID | None = None
    payment_id: UUID | None = None
    provider: str | None = None
    external_reference: str | None = None
    subtype: str
    outcome_class: str
    lifecycle_status: str
    disputed_amount: float
    fee_amount: float
    fee_status: str
    currency_code: str
    reason_code: str | None = None
    evidence_snapshot: dict = Field(default_factory=dict)
    provider_snapshot: dict = Field(default_factory=dict)
    opened_at: datetime
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
