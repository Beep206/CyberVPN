from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.presentation.api.v1.payments.schemas import InvoiceResponse


class CreatePaymentAttemptRequest(BaseModel):
    order_id: UUID = Field(..., description="Canonical order identifier")


class PaymentAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    order_id: UUID
    payment_id: UUID | None = None
    supersedes_attempt_id: UUID | None = None
    attempt_number: int
    provider: str
    sale_channel: str
    currency_code: str
    status: str
    displayed_amount: float
    wallet_amount: float
    gateway_amount: float
    external_reference: str | None = None
    idempotency_key: str
    provider_snapshot: dict = Field(default_factory=dict)
    request_snapshot: dict = Field(default_factory=dict)
    invoice: InvoiceResponse | None = None
    terminal_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
