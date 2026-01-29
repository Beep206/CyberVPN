"""Payment API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.enums import PaymentProvider, PaymentStatus


class CreateInvoiceRequest(BaseModel):
    """Request schema for creating a payment invoice."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "plan_id": "premium_monthly",
                "currency": "USD",
            }
        }
    )

    user_uuid: UUID = Field(..., description="User UUID")
    plan_id: str = Field(
        ..., max_length=100, description="Subscription plan identifier"
    )
    currency: str = Field(
        ..., min_length=3, max_length=3, description="Currency code (ISO 4217)"
    )

    @field_validator("currency")
    @classmethod
    def validate_currency_uppercase(cls, v: str) -> str:
        if not v.isupper():
            raise ValueError("Currency code must be uppercase (e.g. USD, EUR)")
        return v


class InvoiceResponse(BaseModel):
    """Response schema for payment invoice."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "invoice_id": "inv_1234567890",
                "payment_url": "https://payment.provider.com/pay/inv_1234567890",
                "amount": 9.99,
                "currency": "USD",
                "status": "pending",
                "expires_at": "2024-01-29T12:00:00",
            }
        }
    )

    invoice_id: str = Field(..., description="Unique invoice identifier")
    payment_url: str = Field(
        ..., max_length=2000, description="URL for payment processing"
    )
    amount: float = Field(..., gt=0, description="Invoice amount")
    currency: str = Field(..., description="Currency code (ISO 4217)")
    status: str = Field(..., description="Invoice status (pending, paid, expired)")
    expires_at: datetime = Field(..., description="Invoice expiration timestamp")


class PaymentHistoryResponse(BaseModel):
    """Response schema for payment history."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "amount": 9.99,
                "currency": "USD",
                "status": "completed",
                "provider": "stripe",
                "created_at": "2024-01-15T10:30:00",
            }
        }
    )

    id: UUID = Field(..., description="Payment record unique identifier")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(..., description="Currency code (ISO 4217)")
    status: PaymentStatus = Field(..., description="Payment status")
    provider: PaymentProvider = Field(..., description="Payment provider name")
    created_at: datetime = Field(..., description="Payment creation timestamp")
