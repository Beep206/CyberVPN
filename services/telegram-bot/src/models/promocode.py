"""Promocode DTO models for telegram-bot service.

This module contains Pydantic models for promotional codes and their
configurations.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from .subscription import PlanAvailability


class PromocodeType(StrEnum):
    """Promocode type enumeration."""

    DURATION = "duration"
    TRAFFIC = "traffic"
    DEVICES = "devices"
    SUBSCRIPTION = "subscription"
    PERSONAL_DISCOUNT = "personal_discount"
    PURCHASE_DISCOUNT = "purchase_discount"


class PromocodeDTO(BaseModel):
    """Promocode data transfer object.

    Attributes:
        id: Unique promocode identifier
        code: The promocode string (case-insensitive)
        type: Type of promocode benefit
        availability: Who can use this promocode
        is_active: Whether promocode is currently active
        reward_value: The reward value (interpretation depends on type)
        expires_at: Expiration timestamp (None for no expiration)
        max_activations: Maximum total activations allowed (None for unlimited)
        current_activations: Current number of activations
        allowed_users: List of allowed Telegram IDs (empty for availability-based)
        min_purchase_amount: Minimum purchase amount to use code
        allowed_plans: List of plan IDs this code can be used with (empty for all)
        description: Admin-facing description
        created_at: Creation timestamp
        created_by: Telegram ID of admin who created it
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str = Field(..., description="Unique promocode identifier")
    code: str = Field(..., min_length=3, max_length=50, description="Promocode string")
    type: PromocodeType = Field(..., description="Promocode type")
    availability: PlanAvailability = Field(default=PlanAvailability.ALL, description="Usage availability")
    is_active: bool = Field(default=True, description="Active status")
    reward_value: Annotated[float, Field(gt=0, description="Reward value")]
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    max_activations: int | None = Field(None, ge=1, description="Maximum activations (None for unlimited)")
    current_activations: Annotated[int, Field(ge=0, description="Current activation count")]
    allowed_users: list[int] = Field(default_factory=list, description="Allowed Telegram IDs")
    min_purchase_amount: Annotated[float, Field(ge=0, description="Minimum purchase amount")] = 0.0
    allowed_plans: list[str] = Field(default_factory=list, description="Allowed plan IDs (empty for all)")
    description: str | None = Field(None, description="Admin description")
    created_at: datetime = Field(..., description="Creation timestamp")
    created_by: int = Field(..., description="Creator Telegram ID")


class PromocodeActivation(BaseModel):
    """Promocode activation record.

    Attributes:
        id: Unique activation identifier
        promocode_id: ID of the promocode used
        user_uuid: UUID of user who activated
        telegram_id: Telegram ID of user who activated
        activated_at: Activation timestamp
        benefit_applied: What benefit was applied
        payment_id: Associated payment ID if applicable
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str = Field(..., description="Unique activation identifier")
    promocode_id: str = Field(..., description="Promocode ID")
    user_uuid: str = Field(..., description="User UUID")
    telegram_id: int = Field(..., description="User Telegram ID")
    activated_at: datetime = Field(..., description="Activation timestamp")
    benefit_applied: str = Field(..., description="Benefit description")
    payment_id: str | None = Field(None, description="Associated payment ID")
