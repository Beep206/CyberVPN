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

    @property
    def product_family_key(self) -> str:
        """Stable add-on family identifier independent of pricebook overlays."""

        return self.code

    @property
    def legacy_eligibility_overlay(self) -> dict[str, Any]:
        """Eligibility-like overlay fields still attached to the base add-on row."""

        return {
            "sale_channels": list(self.sale_channels),
            "requires_location": self.requires_location,
            "max_quantity_by_plan": dict(self.max_quantity_by_plan),
        }
