from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class PaymentDispute:
    id: UUID
    order_id: UUID
    payment_attempt_id: UUID | None
    payment_id: UUID | None
    provider: str | None
    external_reference: str | None
    subtype: str
    outcome_class: str
    lifecycle_status: str
    disputed_amount: float
    fee_amount: float
    fee_status: str
    currency_code: str
    reason_code: str | None
    evidence_snapshot: dict[str, Any] = field(default_factory=dict)
    provider_snapshot: dict[str, Any] = field(default_factory=dict)
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
