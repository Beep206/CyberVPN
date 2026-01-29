from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.domain.enums import PlanTier


@dataclass(frozen=True)
class SubscriptionPlan:
    uuid: UUID
    name: str
    tier: PlanTier
    duration_days: int
    traffic_limit_bytes: int | None  # None = unlimited
    device_limit: int
    price_usd: Decimal
    price_rub: Decimal | None
    features: dict[str, Any]
    is_active: bool
    sort_order: int
