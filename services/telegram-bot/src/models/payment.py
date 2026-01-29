"""Payment DTO models for telegram-bot service.

This module contains Pydantic models for payments, invoices, and related
payment gateway integrations.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class PaymentGateway(StrEnum):
    """Payment gateway enumeration."""

    CRYPTOBOT = "cryptobot"
    YOOKASSA = "yookassa"
    TELEGRAM_STARS = "telegram_stars"


class PaymentStatus(StrEnum):
    """Payment status enumeration."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class InvoiceDTO(BaseModel):
    """Invoice data transfer object.

    Attributes:
        id: Unique invoice identifier
        gateway: Payment gateway used
        amount: Invoice amount
        currency: Currency code (e.g., USD, EUR, RUB)
        status: Current invoice status
        payment_url: URL for payment (if available)
        payload: Custom payload/metadata
        created_at: Invoice creation timestamp
        expires_at: Invoice expiration timestamp (if applicable)
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str = Field(..., description="Unique invoice identifier")
    gateway: PaymentGateway = Field(..., description="Payment gateway")
    amount: Annotated[Decimal, Field(ge=0, decimal_places=2, description="Invoice amount")]
    currency: str = Field(..., min_length=3, max_length=3, description="Currency code")
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, description="Invoice status")
    payment_url: str | None = Field(None, description="Payment URL")
    payload: str = Field(..., description="Custom payload/metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")


class PaymentDTO(BaseModel):
    """Payment data transfer object.

    Attributes:
        id: Unique payment identifier
        user_uuid: User UUID who made the payment
        telegram_id: User's Telegram ID
        plan_id: Subscription plan ID
        duration_days: Subscription duration in days
        gateway: Payment gateway used
        amount: Payment amount
        currency: Currency code
        status: Payment status
        charge_id: External charge/transaction ID from gateway
        created_at: Payment creation timestamp
        completed_at: Payment completion timestamp (if completed)
        metadata: Additional payment metadata
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str = Field(..., description="Unique payment identifier")
    user_uuid: str = Field(..., description="User UUID")
    telegram_id: int = Field(..., description="User's Telegram ID")
    plan_id: str = Field(..., description="Subscription plan ID")
    duration_days: Annotated[int, Field(ge=-1, description="Duration in days (-1 for unlimited)")]
    gateway: PaymentGateway = Field(..., description="Payment gateway")
    amount: Annotated[Decimal, Field(ge=0, decimal_places=2, description="Payment amount")]
    currency: str = Field(..., min_length=3, max_length=3, description="Currency code")
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, description="Payment status")
    charge_id: str | None = Field(None, description="External charge/transaction ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    metadata: dict[str, str | int | float | bool] = Field(
        default_factory=dict, description="Additional payment metadata"
    )
