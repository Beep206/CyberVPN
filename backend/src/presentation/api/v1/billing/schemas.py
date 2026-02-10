"""Billing API schemas for Remnawave proxy."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreatePaymentRequest(BaseModel):
    """Request schema for creating a billing payment."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "amount": 9.99,
                "currency": "USD",
                "payment_method": "cryptobot",
            }
        }
    )

    user_uuid: str = Field(..., max_length=255, description="User UUID")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(..., min_length=3, max_length=3, description="Currency code (ISO 4217)")
    payment_method: str | None = Field(None, max_length=50, description="Payment method")
    metadata: dict[str, Any] | None = Field(None, description="Additional payment metadata")


class BillingRecordResponse(BaseModel):
    """Expected response from Remnawave billing API."""

    model_config = ConfigDict(from_attributes=True)

    uuid: str = Field(..., description="Billing record UUID")
    user_uuid: str = Field(..., description="User UUID")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(..., max_length=3, description="Currency code")
    status: str = Field(..., max_length=50, description="Payment status")
    payment_method: str | None = Field(None, max_length=50, description="Payment method")
    created_at: str | None = Field(None, description="Creation timestamp")
