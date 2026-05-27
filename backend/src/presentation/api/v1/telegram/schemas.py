"""Telegram API schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.application.use_cases.trial.stage1_trial_policy import (
    STAGE1_TRIAL_DEVICE_LIMIT,
    STAGE1_TRIAL_DURATION_DAYS,
    STAGE1_TRIAL_ONE_PER_ACCOUNT,
    STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES,
)
from src.presentation.api.v1.access_delivery_channels.schemas import CurrentServiceStateResponse
from src.presentation.api.v1.addons.schemas import AddonResponse
from src.presentation.api.v1.orders.schemas import OrderResponse
from src.presentation.api.v1.payments.schemas import (
    CheckoutAddonRequest,
    CheckoutCommitResponse,
    CheckoutQuoteResponse,
)
from src.presentation.api.v1.plans.schemas import PlanResponse
from src.presentation.api.v1.subscriptions.schemas import CurrentEntitlementsResponse


class TelegramUserResponse(BaseModel):
    """Response schema for Telegram user information."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "uuid": "550e8400-e29b-41d4-a716-446655440000",
                "username": "user123",
                "status": "active",
                "data_usage": 5368709120,
                "data_limit": 107374182400,
                "expires_at": "2024-12-31T23:59:59",
                "subscription_url": "vless://config-string-here",
            }
        },
    )

    uuid: UUID = Field(..., description="User unique identifier")
    username: str = Field(..., max_length=100, description="Username")
    status: str = Field(..., max_length=50, description="User account status")
    data_usage: int = Field(..., description="Current data usage in bytes")
    data_limit: int | None = Field(None, description="Data limit in bytes")
    expires_at: datetime | None = Field(None, description="Subscription expiration date")
    subscription_url: str | None = Field(None, max_length=5000, description="VPN subscription configuration URL")


class CreateSubscriptionRequest(BaseModel):
    """Request schema for creating a subscription."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "plan_name": "Premium Monthly",
                "duration_days": 30,
            }
        }
    )

    plan_name: str = Field(..., max_length=100, description="Name of the subscription plan")
    duration_days: int = Field(..., gt=0, le=3650, description="Subscription duration in days")


class CreateSubscriptionResponse(BaseModel):
    """Response schema for a created Telegram user subscription."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(default="success", description="Operation status")
    subscription_id: str | int | None = Field(None, description="Created subscription identifier")
    expires_at: datetime | None = Field(None, description="Subscription expiration date")


class ConfigResponse(BaseModel):
    """Response schema for VPN configuration."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "config_string": "vless://uuid@server:port?encryption=none&security=tls",
                "client_type": "vless",
            }
        }
    )

    config_string: str = Field(..., max_length=5000, description="Primary VPN subscription URL or fallback config")
    client_type: str = Field(..., max_length=50, description="VPN client type (vless, vmess, etc.)")
    subscription_url: str | None = Field(
        None,
        max_length=5000,
        description="Canonical subscription URL when available",
    )
    subscription_key: str | None = Field(None, max_length=220, description="Selected customer subscription key")


class NotifyRequest(BaseModel):
    """Request schema for sending notifications to Telegram users."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "telegram_id": 123456789,
                "message": "Your subscription will expire in 3 days",
                "notification_type": "warning",
            }
        }
    )

    telegram_id: int = Field(..., description="Telegram user ID")
    message: str = Field(..., min_length=1, max_length=4096, description="Notification message")
    notification_type: str | None = Field(
        None,
        max_length=50,
        description="Type of notification (info, warning, error)",
    )


class TelegramBotUserCreateRequest(BaseModel):
    """Internal bot request to create or bootstrap a Telegram user."""

    telegram_id: int = Field(..., gt=0)
    username: str | None = Field(default=None, max_length=255)
    first_name: str | None = Field(default=None, max_length=255)
    language_code: str = Field(default="en", max_length=16)
    referrer_id: int | None = Field(default=None, gt=0)


class TelegramBotUserUpdateRequest(BaseModel):
    """Internal bot request to update Telegram-side profile details."""

    username: str | None = Field(default=None, max_length=255)
    first_name: str | None = Field(default=None, max_length=255)
    language_code: str | None = Field(default=None, max_length=16)


class TelegramBotUserResponse(BaseModel):
    """Telegram bot-facing user payload compatible with the bot service DTO."""

    uuid: str
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    language_code: str = "en"
    status: str = "none"
    is_admin: bool = False
    personal_discount: float = 0.0
    next_purchase_discount: float = 0.0
    referrer_id: int | None = None
    points: int = 0
    subscription: dict | None = None
    subscriptions: list[dict] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TelegramBotAccessSettingsResponse(BaseModel):
    """Bot access settings returned to the Telegram bot service."""

    access_mode: str = "open"
    rules_url: str | None = None
    channel_id: str | None = None


class TelegramBotSubscriptionResponse(BaseModel):
    """Bot-facing subscription summary."""

    subscription_key: str | None = None
    kind: str | None = None
    status: str
    display_name: str | None = None
    plan_name: str | None = None
    expires_at: datetime | None = None
    traffic_limit_bytes: int | None = None
    used_traffic_bytes: int | None = None
    can_deliver_config: bool = False
    auto_renew: bool = False


class TelegramBotTrialStatusResponse(BaseModel):
    """Bot-facing trial status and eligibility."""

    eligible: bool
    reason: str | None = None
    is_trial_active: bool = False
    trial_start: datetime | None = None
    trial_end: datetime | None = None
    days_remaining: int = 0
    duration_days: int = STAGE1_TRIAL_DURATION_DAYS
    device_limit: int = STAGE1_TRIAL_DEVICE_LIMIT
    traffic_limit_bytes: int = STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES
    one_trial_per_account: bool = STAGE1_TRIAL_ONE_PER_ACCOUNT
    expires_at: datetime | None = None
    entitlements_snapshot: CurrentEntitlementsResponse | None = None


class TelegramBotReferralStatsResponse(BaseModel):
    """Bot-facing referral summary."""

    total_referrals: int = 0
    bonus_days: int = 0
    referral_link: str | None = None


class TelegramBotInviteCodeResponse(BaseModel):
    """Bot-facing invite code payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    free_days: int
    is_used: bool
    expires_at: datetime | None = None
    created_at: datetime


class TelegramBotCheckoutRequest(BaseModel):
    """Canonical checkout payload accepted from the Telegram bot."""

    plan_id: UUID = Field(..., description="Subscription plan UUID")
    addons: list[CheckoutAddonRequest] = Field(default_factory=list)
    promo_code: str | None = Field(default=None, max_length=50)
    use_wallet: float = Field(default=0, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=12)
    payment_method: str = Field(default="cryptobot", min_length=1, max_length=30)


class TelegramStarsInvoiceCreateRequest(TelegramBotCheckoutRequest):
    """Internal Telegram Stars invoice request."""

    telegram_id: int = Field(..., gt=0)
    telegram_stars_amount: int = Field(..., gt=0)


class TelegramStarsInvoiceResponse(BaseModel):
    """Bot-facing invoice parameters for Telegram Stars."""

    payment_id: UUID
    title: str
    description: str
    invoice_payload: str
    amount: int = Field(..., gt=0, description="Telegram Stars amount in XTR minor units")
    currency: str = Field(default="XTR")
    status: str = Field(default="pending")
    expires_at: datetime


class TelegramStarsPreCheckoutRequest(BaseModel):
    """Validation payload received from pre_checkout_query."""

    telegram_id: int = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=12)
    total_amount: int = Field(..., gt=0)
    invoice_payload: str = Field(..., min_length=1, max_length=255)


class TelegramStarsPreCheckoutResponse(BaseModel):
    """Validation result for answering Telegram pre-checkout queries."""

    ok: bool
    payment_id: UUID | None = None
    status: str | None = None
    error_message: str | None = None


class TelegramStarsConfirmRequest(TelegramStarsPreCheckoutRequest):
    """Authoritative payment confirmation payload from successful_payment."""

    telegram_payment_charge_id: str = Field(..., min_length=1, max_length=255)
    provider_payment_charge_id: str | None = Field(default=None, min_length=1, max_length=255)


class TelegramStarsConfirmResponse(BaseModel):
    """Confirmation result for a Telegram Stars payment."""

    payment_id: UUID
    status: str
    provider: str
    external_id: str | None = None
    amount: float
    currency: str
    already_processed: bool = False
    created_at: datetime
    updated_at: datetime


class TelegramStarsRefundReconciliationRequest(BaseModel):
    """Provider-state reconciliation payload for Telegram Stars refunds."""

    telegram_id: int = Field(..., gt=0)
    telegram_payment_charge_id: str = Field(..., min_length=1, max_length=255)
    transaction_id: str = Field(..., min_length=1, max_length=255)
    amount: int = Field(..., gt=0, description="Telegram Stars amount in XTR minor units")
    refunded_at: datetime | None = None
    invoice_payload: str | None = Field(default=None, max_length=255)
    raw_transaction: dict[str, object] = Field(default_factory=dict)


class TelegramStarsRefundReconciliationResponse(BaseModel):
    """Backend reconciliation result for Telegram Stars refund sync."""

    action: str
    payment_id: UUID | None = None
    refund_id: UUID | None = None
    refund_status: str | None = None
    already_reconciled: bool = False


class TelegramBotPaymentStatusResponse(BaseModel):
    """Payment status returned to the Telegram bot."""

    payment_id: UUID
    status: str
    provider: str
    external_id: str | None = None
    amount: float
    currency: str
    created_at: datetime
    updated_at: datetime


class TelegramBotSupportEscalationRequest(BaseModel):
    """Support escalation payload created by the Telegram bot first-line triage."""

    support_reference: str = Field(..., min_length=8, max_length=100, pattern=r"^[a-z0-9:_-]+$")
    category: Literal["payment", "provisioning", "connectivity", "account", "legal_abuse", "general"]
    priority: Literal["p0", "p1", "p2", "p3"]
    safe_summary: str = Field(..., min_length=1, max_length=1000)
    first_line_reply_key: str = Field(..., min_length=1, max_length=100)
    source: Literal["telegram_bot"] = "telegram_bot"
    telegram_username: str | None = Field(default=None, max_length=255)


class TelegramBotSupportEscalationResponse(BaseModel):
    """Bot-facing response for an accepted support escalation."""

    support_reference: str
    status: Literal["accepted"] = "accepted"
    user_uuid: UUID
    note_id: UUID


TelegramBotPlanResponse = PlanResponse
TelegramBotAddonResponse = AddonResponse
TelegramBotEntitlementsResponse = CurrentEntitlementsResponse
TelegramBotCheckoutQuoteResponse = CheckoutQuoteResponse
TelegramBotCheckoutCommitResponse = CheckoutCommitResponse
TelegramBotOrderResponse = OrderResponse
TelegramBotCurrentServiceStateResponse = CurrentServiceStateResponse
