from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Refund:
    id: UUID
    order_id: UUID
    payment_attempt_id: UUID | None
    payment_id: UUID | None
    refund_status: str
    amount: float
    currency_code: str
    provider: str | None
    reason_code: str | None
    reason_text: str | None
    external_reference: str | None
    idempotency_key: str
    provider_snapshot: dict[str, Any] = field(default_factory=dict)
    request_snapshot: dict[str, Any] = field(default_factory=dict)
    submitted_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
