from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class PlanAddon:
    uuid: UUID
    code: str
    display_name: str
    duration_mode: str
    is_stackable: bool
    quantity_step: int
    price_usd: Decimal
    price_rub: Decimal | None
    max_quantity_by_plan: dict[str, int]
    delta_entitlements: dict[str, Any]
    requires_location: bool
    sale_channels: list[str]
    is_active: bool
