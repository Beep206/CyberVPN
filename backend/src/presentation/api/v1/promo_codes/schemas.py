"""Pydantic schemas for promo code endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ValidatePromoRequest(BaseModel):
    """Request body for validating / calculating a promo code discount."""

    code: str = Field(..., min_length=1, max_length=64, description="Promo code to validate")
    plan_id: UUID | None = Field(None, description="Plan the promo is applied to")
    amount: float | None = Field(None, ge=0, description="Order amount for discount calculation")


class ValidatePromoResponse(BaseModel):
    """Response for a successful promo code validation."""

    promo_code_id: UUID
    discount_type: str
    discount_value: float
    discount_amount: float
    code: str


class CreatePromoRequest(BaseModel):
    """Request body for creating a promo code (admin)."""

    code: str = Field(..., min_length=1, max_length=64, description="Unique promo code string")
    discount_type: str = Field(..., description="Discount type (percent or fixed)")
    discount_value: float = Field(..., gt=0, description="Discount value")
    max_uses: int | None = Field(None, ge=1, description="Maximum number of redemptions")
    is_single_use: bool = Field(False, description="Whether a user can use it only once")
    plan_ids: list[UUID] | None = Field(None, description="Restrict to specific plans")
    min_amount: float | None = Field(None, ge=0, description="Minimum order amount")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    description: str | None = Field(None, max_length=500, description="Admin description")
    currency: str = Field("USD", min_length=3, max_length=3, description="Currency code (ISO 4217)")


class PromoCodeResponse(BaseModel):
    """Full promo code representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    discount_type: str
    discount_value: float
    currency: str
    max_uses: int | None
    current_uses: int
    is_single_use: bool
    is_active: bool
    expires_at: datetime | None
    created_at: datetime


class UpdatePromoRequest(BaseModel):
    """Request body for updating an existing promo code (admin)."""

    is_active: bool | None = Field(None, description="Toggle active status")
    max_uses: int | None = Field(None, ge=1, description="Update max uses")
    expires_at: datetime | None = Field(None, description="Update expiration")
    description: str | None = Field(None, max_length=500, description="Update description")
    discount_value: float | None = Field(None, gt=0, description="Update discount value")
