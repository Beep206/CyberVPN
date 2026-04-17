"""Subscription DTO models for telegram-bot service.

This module contains Pydantic models for subscription plans, durations,
and purchase contexts.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PlanType(StrEnum):
    """Subscription plan type enumeration."""

    TRAFFIC = "traffic"
    DEVICES = "devices"
    BOTH = "both"
    UNLIMITED = "unlimited"


class PlanAvailability(StrEnum):
    """Plan availability enumeration for different user types."""

    ALL = "all"
    NEW = "new"
    EXISTING = "existing"
    INVITED = "invited"
    ALLOWED = "allowed"
    TRIAL = "trial"


class CatalogVisibility(StrEnum):
    """Canonical catalog visibility for pricing plans."""

    PUBLIC = "public"
    HIDDEN = "hidden"


class ResetStrategy(StrEnum):
    """Traffic reset strategy enumeration."""

    NO_RESET = "no_reset"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class CatalogPlanDuration(BaseModel):
    """Canonical duration row returned by the pricing catalog."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    plan_id: str = Field(..., description="Concrete plan UUID/SKU row")
    duration_days: Annotated[int, Field(gt=0, description="Duration in days")]
    price_usd: Annotated[float | None, Field(default=None, ge=0)]
    price_rub: Annotated[float | None, Field(default=None, ge=0)]

    @property
    def prices(self) -> dict[str, float]:
        prices: dict[str, float] = {}
        if self.price_usd is not None:
            prices["USD"] = float(self.price_usd)
        if self.price_rub is not None:
            prices["RUB"] = float(self.price_rub)
        return prices


class CatalogPlan(BaseModel):
    """Canonical Telegram pricing catalog row/group representation."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str = Field(..., description="Plan UUID or canonical group identifier")
    plan_code: str = Field(..., description="Canonical plan code")
    display_name: str = Field(..., description="Human-readable plan name")
    catalog_visibility: CatalogVisibility = Field(default=CatalogVisibility.PUBLIC)
    is_active: bool = Field(default=True)
    devices_included: int | None = Field(default=None, ge=1)
    duration_days: int | None = Field(default=None, gt=0)
    durations: list[CatalogPlanDuration] = Field(default_factory=list)
    sale_channels: list[str] = Field(default_factory=list)
    traffic_policy: dict[str, Any] = Field(default_factory=dict)
    connection_modes: list[str] = Field(default_factory=list)
    server_pool: list[str] = Field(default_factory=list)
    support_sla: str | None = None
    dedicated_ip: dict[str, Any] = Field(default_factory=dict)
    invite_bundle: dict[str, Any] = Field(default_factory=dict)
    features: dict[str, Any] = Field(default_factory=dict)


class EntitlementsSnapshot(BaseModel):
    """Effective subscription entitlements returned by the backend."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    plan_code: str | None = None
    display_name: str | None = None
    status: str = "none"
    period_days: int | None = Field(default=None, gt=0)
    expires_at: str | None = None
    effective_entitlements: dict[str, Any] = Field(default_factory=dict)
    addons: list[dict[str, Any]] = Field(default_factory=list)


class CheckoutAddonSelection(BaseModel):
    """Add-on quantity selected for a checkout quote/commit."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    code: str = Field(..., min_length=1, max_length=64)
    qty: Annotated[int, Field(default=1, ge=1)]


class CheckoutQuote(BaseModel):
    """Canonical checkout quote returned by the backend."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    plan_id: str
    currency: str = "USD"
    displayed_price: float = Field(default=0, ge=0)
    gateway_amount: float = Field(default=0, ge=0)
    addons: list[CheckoutAddonSelection] = Field(default_factory=list)
    effective_entitlements: dict[str, Any] = Field(default_factory=dict)


class PlanDuration(BaseModel):
    """Subscription plan duration with multi-currency pricing.

    Attributes:
        duration_days: Duration in days (-1 for unlimited)
        prices: Mapping of currency code to price (e.g., {"USD": 9.99, "EUR": 8.99})
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    duration_days: Annotated[int, Field(description="Duration in days (-1 for unlimited)")]
    prices: Annotated[
        dict[str, float],
        Field(description="Currency-to-price mapping", examples=[{"USD": 9.99, "EUR": 8.99, "RUB": 750.0}]),
    ]


class SubscriptionPlan(BaseModel):
    """Subscription plan model with full configuration.

    Attributes:
        id: Unique plan identifier
        name: Human-readable plan name
        description: Plan description
        tag: Short tag/label for the plan
        plan_type: Type of plan (traffic/devices/both/unlimited)
        availability: Who can access this plan
        is_active: Whether plan is currently available
        traffic_limit_gb: Traffic limit in GB (None for unlimited)
        device_limit: Maximum devices (None for unlimited)
        reset_strategy: When traffic limits reset
        durations: Available duration options with pricing
        squads: List of squad/group identifiers this plan belongs to
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str = Field(..., description="Unique plan identifier")
    name: str = Field(..., description="Plan name")
    description: str = Field(..., description="Plan description")
    tag: str = Field(..., description="Plan tag/label")
    plan_type: PlanType = Field(..., description="Plan type")
    availability: PlanAvailability = Field(..., description="Plan availability")
    is_active: bool = Field(default=True, description="Plan active status")
    traffic_limit_gb: float | None = Field(None, ge=0, description="Traffic limit in GB (None for unlimited)")
    device_limit: int | None = Field(None, ge=1, description="Device limit (None for unlimited)")
    reset_strategy: ResetStrategy = Field(default=ResetStrategy.NO_RESET, description="Traffic reset strategy")
    durations: list[PlanDuration] = Field(default_factory=list, description="Available duration options")
    squads: list[str] = Field(default_factory=list, description="Squad/group identifiers")


class Discount(BaseModel):
    """Discount information for purchase context.

    Attributes:
        type: Discount type (personal/next_purchase/promo)
        value: Discount percentage (0-100)
        code: Promocode if applicable
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    type: Literal["personal", "next_purchase", "promo"] = Field(..., description="Discount type")
    value: Annotated[float, Field(ge=0, le=100, description="Discount percentage")]
    code: str | None = Field(None, description="Promocode if applicable")


class PurchaseContext(BaseModel):
    """Context for a purchase/renewal operation.

    Attributes:
        plan: The subscription plan being purchased
        duration: Selected duration option
        gateway: Payment gateway identifier
        operation: Type of operation (purchase/renewal/change)
        discounts: List of applicable discounts
        original_price: Original price before discounts
        final_price: Final price after discounts
        currency: Currency code
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    plan: SubscriptionPlan = Field(..., description="Subscription plan")
    duration: PlanDuration = Field(..., description="Selected duration")
    gateway: str = Field(..., description="Payment gateway identifier")
    operation: Literal["purchase", "renewal", "change"] = Field(..., description="Operation type")
    discounts: list[Discount] = Field(default_factory=list, description="Applicable discounts")
    original_price: Annotated[float, Field(ge=0, description="Original price")]
    final_price: Annotated[float, Field(ge=0, description="Final price after discounts")]
    currency: str = Field(..., description="Currency code")


def subscription_plan_from_catalog(plan: CatalogPlan | dict[str, Any]) -> SubscriptionPlan:
    """Convert a canonical catalog row/group into the legacy SubscriptionPlan DTO."""

    source = plan.model_dump() if isinstance(plan, CatalogPlan) else dict(plan)
    durations_source = source.get("durations") or []

    if not durations_source and source.get("duration_days"):
        durations_source = [
            {
                "plan_id": source.get("uuid") or source.get("id"),
                "duration_days": source.get("duration_days"),
                "price_usd": source.get("price_usd"),
                "price_rub": source.get("price_rub"),
            }
        ]

    durations = [
        PlanDuration(
            duration_days=int(duration.get("duration_days") or 0),
            prices={
                key: value
                for key, value in {
                    "USD": duration.get("price_usd"),
                    "RUB": duration.get("price_rub"),
                }.items()
                if value is not None
            },
        )
        for duration in durations_source
        if int(duration.get("duration_days") or 0) > 0
    ]

    traffic_label = str((source.get("traffic_policy") or {}).get("display_label") or "").lower()
    traffic_limit_bytes = source.get("traffic_limit_bytes")
    if traffic_limit_bytes is None or "unlimited" in traffic_label:
        traffic_limit_gb = None
    else:
        traffic_limit_gb = round(float(traffic_limit_bytes) / (1024**3), 2)

    return SubscriptionPlan(
        id=str(source.get("uuid") or source.get("id") or source.get("plan_code") or "plan"),
        name=str(source.get("display_name") or source.get("name") or source.get("plan_code") or "Plan"),
        description=str(source.get("features", {}).get("marketing_badge") or source.get("plan_code") or ""),
        tag=str(source.get("plan_code") or source.get("display_name") or "PLAN").upper(),
        plan_type=PlanType.UNLIMITED if traffic_limit_gb is None else PlanType.BOTH,
        availability=PlanAvailability.ALL,
        is_active=bool(source.get("is_active", True)),
        traffic_limit_gb=traffic_limit_gb,
        device_limit=source.get("devices_included"),
        reset_strategy=ResetStrategy.NO_RESET,
        durations=durations,
        squads=list(source.get("server_pool") or []),
    )
