from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateRefundRequest(BaseModel):
    order_id: UUID
    payment_attempt_id: UUID | None = None
    amount: float = Field(..., gt=0)
    reason_code: str | None = Field(default=None, max_length=80)
    reason_text: str | None = Field(default=None, max_length=500)


class UpdateRefundRequest(BaseModel):
    refund_status: str = Field(..., min_length=1, max_length=20)
    external_reference: str | None = Field(default=None, max_length=255)
    provider_snapshot: dict = Field(default_factory=dict)


class RefundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    order_id: UUID
    payment_attempt_id: UUID | None = None
    payment_id: UUID | None = None
    refund_status: str
    amount: float
    currency_code: str
    provider: str | None = None
    reason_code: str | None = None
    reason_text: str | None = None
    external_reference: str | None = None
    idempotency_key: str
    provider_snapshot: dict = Field(default_factory=dict)
    request_snapshot: dict = Field(default_factory=dict)
    submitted_at: datetime
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
