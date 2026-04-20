from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class PaymentAttempt:
    id: UUID
    order_id: UUID
    payment_id: UUID | None
    supersedes_attempt_id: UUID | None
    attempt_number: int
    provider: str
    sale_channel: str
    currency_code: str
    status: str
    displayed_amount: float
    wallet_amount: float
    gateway_amount: float
    external_reference: str | None
    idempotency_key: str
    provider_snapshot: dict[str, Any] = field(default_factory=dict)
    request_snapshot: dict[str, Any] = field(default_factory=dict)
    terminal_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
