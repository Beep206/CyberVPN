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
    plan_id: str = Field(..., max_length=100, description="Subscription plan identifier")
    currency: str = Field(..., min_length=3, max_length=12, description="Currency or asset code")

    @field_validator("currency")
    @classmethod
    def validate_currency_uppercase(cls, value: str) -> str:
        if not value.isupper():
            raise ValueError("Currency code must be uppercase (e.g. USD, EUR, TON)")
        return value


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
    payment_url: str = Field(..., max_length=2000, description="URL for payment processing")
    amount: float = Field(..., ge=0, description="Invoice amount")
    currency: str = Field(..., description="Currency or asset code")
    status: str = Field(..., description="Invoice status")
    expires_at: datetime = Field(..., description="Invoice expiration timestamp")


class PaymentHistoryItem(BaseModel):
    """Payment history item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Payment record unique identifier")
    amount: float = Field(..., description="Subtotal before promo/wallet application")
    currency: str = Field(..., description="Currency code")
    status: PaymentStatus = Field(..., description="Payment status")
    provider: PaymentProvider = Field(..., description="Payment provider name")
    created_at: datetime = Field(..., description="Payment creation timestamp")


class PaymentHistoryResponse(BaseModel):
    """Response schema for payment history."""

    payments: list[PaymentHistoryItem] = Field(..., description="List of payment history items")


class CheckoutAddonRequest(BaseModel):
    """Requested add-on line."""

    code: str = Field(..., min_length=1, max_length=50)
    qty: int = Field(default=1, ge=1, le=100)
    location_code: str | None = Field(None, min_length=2, max_length=64)


class CheckoutAddonResponse(BaseModel):
    """Priced add-on line returned by quote/commit."""

    addon_id: UUID
    code: str
    display_name: str
    qty: int
    unit_price: float
    total_price: float
    location_code: str | None = None


class EffectiveEntitlementsResponse(BaseModel):
    device_limit: int
    traffic_policy: str
    display_traffic_label: str
    connection_modes: list[str]
    server_pool: list[str]
    support_sla: str
    dedicated_ip_count: int


class EntitlementsSnapshotResponse(BaseModel):
    status: str
    plan_uuid: str | None = None
    plan_code: str | None = None
    display_name: str | None = None
    period_days: int | None = None
    expires_at: str | None = None
    effective_entitlements: EffectiveEntitlementsResponse
    invite_bundle: dict[str, int]
    is_trial: bool
    addons: list[dict] = Field(default_factory=list)


class CheckoutQuoteRequest(BaseModel):
    """Quote request for a plan + add-ons basket."""

    plan_id: UUID = Field(..., description="Subscription plan to purchase")
    addons: list[CheckoutAddonRequest] = Field(default_factory=list)
    promo_code: str | None = Field(None, max_length=50, description="Optional promo code")
    partner_code: str | None = Field(None, max_length=30, description="Optional partner code")
    use_wallet: float = Field(0, ge=0, description="Requested wallet amount in USD")
    currency: str = Field("USD", min_length=3, max_length=12, description="Gateway asset code")
    channel: str = Field("web", min_length=1, max_length=30, description="Checkout sale channel")

    @field_validator("currency")
    @classmethod
    def validate_quote_currency_uppercase(cls, value: str) -> str:
        if not value.isupper():
            raise ValueError("Currency code must be uppercase")
        return value


class CheckoutQuoteResponse(BaseModel):
    """Quote response with final entitlement snapshot."""

    base_price: float
    addon_amount: float
    displayed_price: float
    discount_amount: float
    wallet_amount: float
    gateway_amount: float
    partner_markup: float
    is_zero_gateway: bool
    plan_id: UUID | None = None
    promo_code_id: UUID | None = None
    partner_code_id: UUID | None = None
    addons: list[CheckoutAddonResponse] = Field(default_factory=list)
    entitlements_snapshot: EntitlementsSnapshotResponse


class CheckoutCommitResponse(CheckoutQuoteResponse):
    """Commit response with persisted payment or invoice reference."""

    payment_id: UUID | None = Field(None, description="Local payment identifier")
    status: str = Field(..., description="completed or pending")
    invoice: InvoiceResponse | None = None


# Backward-compatible aliases for older imports/routes.
CheckoutRequest = CheckoutQuoteRequest
CheckoutResponse = CheckoutCommitResponse
