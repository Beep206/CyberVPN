from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.domain.enums import PaymentProvider, PaymentStatus


@dataclass(frozen=True)
class Payment:
    uuid: UUID
    user_uuid: UUID
    amount: Decimal
    currency: str
    status: PaymentStatus
    provider: PaymentProvider
    subscription_days: int
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] | None = None
