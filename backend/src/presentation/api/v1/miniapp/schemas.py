from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.presentation.api.v1.addons.schemas import AddonResponse
from src.presentation.api.v1.payments.schemas import (
    CheckoutAddonRequest,
    CheckoutCommitResponse,
    CheckoutQuoteResponse,
    PaymentStatusResponse,
)
from src.presentation.api.v1.plans.schemas import PlanResponse
from src.presentation.api.v1.subscriptions.schemas import CurrentEntitlementsResponse, SubscriptionConfigResponse
from src.presentation.api.v1.trial.schemas import TrialActivateResponse, TrialStatusResponse


class MiniAppBootstrapSessionResponse(BaseModel):
    authenticated: bool
    user_id: str | None = Field(None, alias="userId")
    telegram_user_id: str | None = Field(None, alias="telegramUserId")
    auth_realm: Literal["customer", "partner_customer"] = Field(..., alias="authRealm")


class MiniAppBootstrapRuntimeTenantResponse(BaseModel):
    kind: Literal["platform", "partner"]
    partner_id: str | None = Field(None, alias="partnerId")
    workspace_id: str | None = Field(None, alias="workspaceId")
    storefront_id: str | None = Field(None, alias="storefrontId")
    bot_id: str | None = Field(None, alias="botId")


class MiniAppBootstrapRuntimeBrandResponse(BaseModel):
    name: str
    logo_url: str | None = Field(None, alias="logoUrl")
    primary_color: str | None = Field(None, alias="primaryColor")
    support_url: str | None = Field(None, alias="supportUrl")
    legal_name: str | None = Field(None, alias="legalName")


class MiniAppBootstrapRuntimeCommercialPolicyResponse(BaseModel):
    pricing_policy_id: str = Field(..., alias="pricingPolicyId")
    currency_policy: str = Field(..., alias="currencyPolicy")
    revenue_share_policy_id: str | None = Field(None, alias="revenueSharePolicyId")
    trial_policy_id: str | None = Field(None, alias="trialPolicyId")


class MiniAppBootstrapRuntimeAttributionResponse(BaseModel):
    source: str
    surface: str
    referral_code: str | None = Field(None, alias="referralCode")
    campaign: str | None = None
    start_param: str | None = Field(None, alias="startParam")


class MiniAppBootstrapRuntimeResponse(BaseModel):
    surface: Literal["telegram_miniapp"] = "telegram_miniapp"
    tenant: MiniAppBootstrapRuntimeTenantResponse
    brand: MiniAppBootstrapRuntimeBrandResponse
    commercial_policy: MiniAppBootstrapRuntimeCommercialPolicyResponse = Field(..., alias="commercialPolicy")
    attribution: MiniAppBootstrapRuntimeAttributionResponse


class MiniAppBootstrapUserResponse(BaseModel):
    first_name: str | None = Field(None, alias="firstName")
    username: str | None = None
    photo_url: str | None = Field(None, alias="photoUrl")
    locale: str
    rtl: bool


class MiniAppBootstrapSubscriptionResponse(BaseModel):
    status: str
    plan_id: str | None = Field(None, alias="planId")
    plan_name: str | None = Field(None, alias="planName")
    expires_at: str | None = Field(None, alias="expiresAt")
    auto_renew: bool = Field(False, alias="autoRenew")


class MiniAppBootstrapTrialResponse(BaseModel):
    eligible: bool
    reason: str | None = None
    duration_days: int | None = Field(None, alias="durationDays")
    trial_start: datetime | None = Field(None, alias="trialStart")
    trial_end: datetime | None = Field(None, alias="trialEnd")
    days_remaining: int = Field(0, alias="daysRemaining")


class MiniAppBootstrapWalletResponse(BaseModel):
    balance: float
    currency: str
    bonuses_available: float = Field(0, alias="bonusesAvailable")


class MiniAppBootstrapDevicesResponse(BaseModel):
    active_count: int = Field(..., alias="activeCount")
    limit: int
    has_config: bool = Field(..., alias="hasConfig")


class MiniAppBootstrapUsageResponse(BaseModel):
    bandwidth_used_bytes: int = Field(..., alias="bandwidthUsedBytes")
    bandwidth_limit_bytes: int = Field(..., alias="bandwidthLimitBytes")
    connections_active: int = Field(..., alias="connectionsActive")
    connections_limit: int = Field(..., alias="connectionsLimit")
    period_start: datetime | None = Field(None, alias="periodStart")
    period_end: datetime | None = Field(None, alias="periodEnd")
    last_connection_at: datetime | None = Field(None, alias="lastConnectionAt")


class MiniAppBootstrapServiceStateResponse(BaseModel):
    provider_name: str | None = Field(None, alias="providerName")
    channel_type: str | None = Field(None, alias="channelType")


class MiniAppBootstrapRecommendedServerResponse(BaseModel):
    id: str
    country_code: str = Field(..., alias="countryCode")
    city: str | None = None
    public_name: str = Field(..., alias="publicName")
    latency_ms: int | None = Field(None, alias="latencyMs")
    speed_mbps: float | None = Field(None, alias="speedMbps")
    uptime_pct_30d: float | None = Field(None, alias="uptimePct30d")
    dpi_score: int | None = Field(None, alias="dpiScore")
    status: Literal["online", "degraded", "offline"]
    recommended_reason: str | None = Field(None, alias="recommendedReason")


class MiniAppBootstrapPrimaryCtaResponse(BaseModel):
    kind: Literal["start_trial", "buy_plan", "renew", "get_config", "select_server"]
    label: str


class MiniAppBootstrapReferralResponse(BaseModel):
    code: str | None = None
    invite_url: str | None = Field(None, alias="inviteUrl")
    share_text: str | None = Field(None, alias="shareText")


class MiniAppBootstrapPaymentResponse(BaseModel):
    unresolved_payment_id: str | None = Field(None, alias="unresolvedPaymentId")
    last_status: Literal["pending", "paid", "cancelled", "failed"] | None = Field(None, alias="lastStatus")


class MiniAppBootstrapSupportResponse(BaseModel):
    url: str | None = None
    paysupport_command_available: bool = Field(False, alias="paysupportCommandAvailable")


class MiniAppBootstrapRolloutResponse(BaseModel):
    enabled: bool
    mode: Literal["live", "canary", "maintenance", "rollback"] = "live"
    trial_enabled: bool = Field(..., alias="trialEnabled")
    checkout_enabled: bool = Field(..., alias="checkoutEnabled")
    config_enabled: bool = Field(..., alias="configEnabled")
    access_granted: bool = Field(..., alias="accessGranted")
    is_canary_user: bool = Field(False, alias="isCanaryUser")
    gate_reason_code: (
        Literal["runtime_disabled", "maintenance", "rollback", "feature_disabled", "canary_not_allowed"]
        | None
    ) = Field(None, alias="gateReasonCode")
    maintenance_message: str | None = Field(None, alias="maintenanceMessage")


class MiniAppBootstrapFreshnessResponse(BaseModel):
    generated_at: datetime = Field(..., alias="generatedAt")


class MiniAppBootstrapResponse(BaseModel):
    session: MiniAppBootstrapSessionResponse
    runtime: MiniAppBootstrapRuntimeResponse
    user: MiniAppBootstrapUserResponse
    subscription: MiniAppBootstrapSubscriptionResponse
    trial: MiniAppBootstrapTrialResponse
    wallet: MiniAppBootstrapWalletResponse
    devices: MiniAppBootstrapDevicesResponse
    usage: MiniAppBootstrapUsageResponse
    service_state: MiniAppBootstrapServiceStateResponse = Field(..., alias="serviceState")
    recommended_server: MiniAppBootstrapRecommendedServerResponse | None = Field(None, alias="recommendedServer")
    primary_cta: MiniAppBootstrapPrimaryCtaResponse = Field(..., alias="primaryCta")
    referral: MiniAppBootstrapReferralResponse
    payment: MiniAppBootstrapPaymentResponse
    support: MiniAppBootstrapSupportResponse
    rollout: MiniAppBootstrapRolloutResponse
    feature_flags: dict[str, bool] = Field(default_factory=dict, alias="featureFlags")
    freshness: MiniAppBootstrapFreshnessResponse


class MiniAppOffersResponse(BaseModel):
    plans: list[PlanResponse]
    addons: list[AddonResponse]
    trial: TrialStatusResponse
    current_entitlements: CurrentEntitlementsResponse = Field(..., alias="currentEntitlements")
    freshness: MiniAppBootstrapFreshnessResponse


class MiniAppConfigResponse(SubscriptionConfigResponse):
    config_string: str = Field(..., alias="configString")
    client_type: str = Field(..., alias="clientType")
    source: Literal["remnawave_generated", "legacy_subscription_url"] = Field(..., alias="source")
    subscription_url: str | None = Field(None, alias="subscriptionUrl")
    generated_at: datetime = Field(..., alias="generatedAt")


class MiniAppCheckoutRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    flow: Literal["checkout", "upgrade", "addons"] = "checkout"
    plan_id: UUID | None = Field(None, alias="planId")
    addons: list[CheckoutAddonRequest] = Field(default_factory=list)
    code_input: str | None = Field(None, alias="codeInput", max_length=64)
    promo_code: str | None = Field(None, alias="promoCode", max_length=50)
    partner_code: str | None = Field(None, alias="partnerCode", max_length=30)
    use_wallet: float = Field(0, alias="useWallet", ge=0)
    currency: str = Field("USD", min_length=3, max_length=12)


MiniAppCheckoutQuoteResponse = CheckoutQuoteResponse
MiniAppCheckoutCommitResponse = CheckoutCommitResponse
MiniAppPaymentStatusResponse = PaymentStatusResponse
MiniAppTrialActivateResponse = TrialActivateResponse
