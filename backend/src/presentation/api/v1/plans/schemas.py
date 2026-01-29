"""Subscription plan API schemas for Remnawave proxy."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CreatePlanRequest(BaseModel):
    """Request schema for creating a subscription plan."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Premium Monthly",
                "price": 9.99,
                "currency": "USD",
                "duration_days": 30,
                "data_limit_gb": 100,
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=100, description="Plan name")
    price: float = Field(..., ge=0, description="Plan price")
    currency: str = Field(
        ..., min_length=3, max_length=3, description="Currency code (ISO 4217)"
    )
    duration_days: int = Field(
        ..., gt=0, le=3650, description="Plan duration in days"
    )
    data_limit_gb: Optional[int] = Field(None, ge=0, description="Data limit in GB")
    max_devices: Optional[int] = Field(
        None, ge=1, le=100, description="Max simultaneous devices"
    )
    features: Optional[list[str]] = Field(None, description="List of plan features")
    is_active: bool = Field(True, description="Whether plan is active")


class UpdatePlanRequest(BaseModel):
    """Request schema for updating a subscription plan."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    duration_days: Optional[int] = Field(None, gt=0, le=3650)
    data_limit_gb: Optional[int] = Field(None, ge=0)
    max_devices: Optional[int] = Field(None, ge=1, le=100)
    features: Optional[list[str]] = None
    is_active: Optional[bool] = None


class PlanResponse(BaseModel):
    """Expected response from Remnawave plans API."""

    model_config = ConfigDict(from_attributes=True)

    uuid: str = Field(..., description="Plan UUID")
    name: str = Field(..., max_length=100, description="Plan name")
    price: float = Field(..., description="Plan price")
    currency: str = Field(..., max_length=3, description="Currency code")
    duration_days: int = Field(..., description="Plan duration in days")
    data_limit_gb: Optional[int] = Field(None, description="Data limit in GB")
    max_devices: Optional[int] = Field(None, description="Max simultaneous devices")
    features: Optional[list[str]] = Field(None, description="Plan features")
    is_active: bool = Field(..., description="Whether plan is active")
