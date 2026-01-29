"""Subscription DTO models for telegram-bot service.

This module contains Pydantic models for subscription plans, durations,
and purchase contexts.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

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


class ResetStrategy(StrEnum):
    """Traffic reset strategy enumeration."""

    NO_RESET = "no_reset"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


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
