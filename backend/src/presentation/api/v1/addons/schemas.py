"""Schemas for pricing add-on catalog."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AddonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    code: str
    display_name: str
    duration_mode: str
    is_stackable: bool
    quantity_step: int
    price_usd: float
    price_rub: float | None = None
    max_quantity_by_plan: dict[str, int]
    delta_entitlements: dict[str, Any]
    requires_location: bool
    sale_channels: list[str]
    is_active: bool


class CreateAddonRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    duration_mode: str = Field(default="inherits_subscription", min_length=1, max_length=30)
    is_stackable: bool = True
    quantity_step: int = Field(default=1, ge=1, le=100)
    price_usd: float = Field(..., ge=0)
    price_rub: float | None = Field(None, ge=0)
    max_quantity_by_plan: dict[str, int] = Field(default_factory=dict)
    delta_entitlements: dict[str, Any] = Field(default_factory=dict)
    requires_location: bool = False
    sale_channels: list[str] = Field(default_factory=lambda: ["web", "miniapp", "telegram_bot", "admin"])
    is_active: bool = True


class UpdateAddonRequest(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=100)
    duration_mode: str | None = Field(None, min_length=1, max_length=30)
    is_stackable: bool | None = None
    quantity_step: int | None = Field(None, ge=1, le=100)
    price_usd: float | None = Field(None, ge=0)
    price_rub: float | None = Field(None, ge=0)
    max_quantity_by_plan: dict[str, int] | None = None
    delta_entitlements: dict[str, Any] | None = None
    requires_location: bool | None = None
    sale_channels: list[str] | None = None
    is_active: bool | None = None
