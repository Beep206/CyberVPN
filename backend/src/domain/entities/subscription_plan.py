from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.domain.enums import CatalogVisibility, PlanCode


@dataclass(frozen=True)
class SubscriptionPlan:
    uuid: UUID
    name: str
    plan_code: PlanCode | str
    display_name: str
    catalog_visibility: CatalogVisibility | str
    duration_days: int
    traffic_limit_bytes: int | None  # None = unlimited
    device_limit: int
    price_usd: Decimal
    price_rub: Decimal | None
    traffic_policy: dict[str, Any]
    connection_modes: list[str]
    server_pool: list[str]
    support_sla: str
    dedicated_ip: dict[str, Any]
    sale_channels: list[str]
    invite_bundle: dict[str, Any]
    trial_eligible: bool
    features: dict[str, Any]
    is_active: bool
    sort_order: int

    @property
    def product_family_key(self) -> str:
        """Stable product-family identifier independent of commercial overlays."""

        return str(self.plan_code or self.name)

    @property
    def legacy_offer_overlay(self) -> dict[str, Any]:
        """Commercial overlay fields that still live on the base catalog row."""

        return {
            "catalog_visibility": str(self.catalog_visibility),
            "sale_channels": list(self.sale_channels),
            "invite_bundle": dict(self.invite_bundle),
            "trial_eligible": self.trial_eligible,
        }
