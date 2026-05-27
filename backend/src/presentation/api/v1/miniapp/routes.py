from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from time import perf_counter
from typing import Literal
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService, MiniAppRuntimeConfig
from src.application.services.stage1_plan_policy import (
    filter_stage1_public_addons,
    filter_stage1_public_paid_plans,
)
from src.application.services.wallet_service import WalletService
from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.customer_subscriptions import (
    CustomerSubscriptionServiceAccessUseCase,
    GetCustomerSubscriptionEntitlementsUseCase,
    ListCustomerSubscriptionsUseCase,
    SelectedSubscriptionCheckoutUseCase,
)
from src.application.use_cases.payments.checkout import CheckoutAddonInput
from src.application.use_cases.payments.commit_checkout import CommitCheckoutUseCase
from src.application.use_cases.referrals.get_referral_code import GetReferralCodeUseCase
from src.application.use_cases.service_access import GetCurrentEntitlementStateUseCase, GetCurrentServiceStateUseCase
from src.application.use_cases.subscriptions import (
    GenerateConfigUseCase,
    GetCurrentEntitlementsUseCase,
    PurchaseAddonsUseCase,
    UpgradeSubscriptionUseCase,
)
from src.application.use_cases.trial.activate_trial import ActivateTrialUseCase
from src.application.use_cases.trial.get_trial_status import GetTrialStatusUseCase
from src.application.use_cases.trial.stage1_trial_policy import (
    STAGE1_TRIAL_ACTIVATE_RATE_LIMIT_MAX,
    STAGE1_TRIAL_ACTIVATE_RATE_LIMIT_WINDOW_SECONDS,
)
from src.application.use_cases.trial.stage1_trial_provisioning import Stage1TrialProvisioningGateway
from src.config.settings import settings
from src.domain.entities.user import User
from src.domain.enums import CatalogVisibility
from src.domain.exceptions import InsufficientWalletBalanceError, WalletNotFoundError
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.mobile_user_repo import MobileDeviceRepository, MobileUserRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.plan_addon_repo import PlanAddonRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.database.repositories.wallet_repo import WalletRepository
from src.infrastructure.monitoring.instrumentation.routes import (
    observe_miniapp_runtime_duration,
    track_miniapp_checkout_commit,
    track_miniapp_config_delivery,
    track_miniapp_payment_status_check,
    track_miniapp_runtime_request,
    track_trial_activation,
)
from src.infrastructure.payments.cryptobot.client import CryptoBotClient
from src.infrastructure.remnawave.client import RemnawaveClient, get_remnawave_client
from src.infrastructure.remnawave.stage1_trial_gateway import RemnawaveStage1TrialProvisioningGateway
from src.infrastructure.remnawave.subscription_urls import normalize_public_subscription_url
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.api.shared.stage1_payment_runtime import (
    require_stage1_payments_enabled,
    require_stage1_telegram_stars_enabled,
)
from src.presentation.api.v1.addons.schemas import AddonResponse
from src.presentation.api.v1.payments.routes import (
    _build_quote as _build_base_checkout_quote,
)
from src.presentation.api.v1.payments.routes import (
    _serialize_quote as _serialize_base_checkout_quote,
)
from src.presentation.api.v1.payments.schemas import CheckoutQuoteRequest, InvoiceResponse
from src.presentation.api.v1.payments.telegram_stars import create_telegram_stars_checkout
from src.presentation.api.v1.plans.schemas import (
    DedicatedIpSchema,
    InviteBundleSchema,
    PlanResponse,
    TrafficPolicySchema,
)
from src.presentation.api.v1.subscriptions.routes import _serialize_subscription_quote
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import get_request_customer_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_crypto_client

from .schemas import (
    MiniAppBootstrapDevicesResponse,
    MiniAppBootstrapFreshnessResponse,
    MiniAppBootstrapPaymentResponse,
    MiniAppBootstrapPrimaryCtaResponse,
    MiniAppBootstrapReferralResponse,
    MiniAppBootstrapResponse,
    MiniAppBootstrapRolloutResponse,
    MiniAppBootstrapRuntimeAttributionResponse,
    MiniAppBootstrapRuntimeBrandResponse,
    MiniAppBootstrapRuntimeCommercialPolicyResponse,
    MiniAppBootstrapRuntimeResponse,
    MiniAppBootstrapRuntimeTenantResponse,
    MiniAppBootstrapServiceStateResponse,
    MiniAppBootstrapSessionResponse,
    MiniAppBootstrapSubscriptionResponse,
    MiniAppBootstrapSupportResponse,
    MiniAppBootstrapTrialResponse,
    MiniAppBootstrapUsageResponse,
    MiniAppBootstrapUserResponse,
    MiniAppBootstrapWalletResponse,
    MiniAppCheckoutCommitResponse,
    MiniAppCheckoutQuoteResponse,
    MiniAppCheckoutRequest,
    MiniAppConfigResponse,
    MiniAppOffersResponse,
    MiniAppPaymentStatusResponse,
    MiniAppTrialActivateResponse,
)

router = APIRouter(prefix="/miniapp", tags=["miniapp"])
logger = logging.getLogger(__name__)

_RTL_LOCALE_PREFIXES = ("ar", "fa", "he", "ur")


class _MiniAppRuntimeDecision:
    def __init__(
        self,
        *,
        allowed: bool,
        is_canary_user: bool,
        gate_reason_code: str | None = None,
    ) -> None:
        self.allowed = allowed
        self.is_canary_user = is_canary_user
        self.gate_reason_code = gate_reason_code


def _is_rtl_locale(locale: str) -> bool:
    normalized = (locale or "").strip().lower()
    return any(normalized.startswith(prefix) for prefix in _RTL_LOCALE_PREFIXES)


def _build_support_url() -> str | None:
    username = settings.telegram_bot_username.strip().lstrip("@")
    if not username:
        return None
    return f"https://t.me/{username}?start=support"


def _build_invite_url(referral_code: str | None) -> str | None:
    username = settings.telegram_bot_username.strip().lstrip("@")
    if not username or not referral_code:
        return None
    return f"https://t.me/{username}?startapp=ref_{referral_code}"


def _build_referral_share_text(referral_code: str | None, invite_url: str | None) -> str | None:
    if not referral_code:
        return None
    if invite_url:
        return f"Try CyberVPN in Telegram. Use my invite code {referral_code}: {invite_url}"
    return f"Try CyberVPN in Telegram. Use my invite code {referral_code}."


async def _get_miniapp_runtime_config(db: AsyncSession) -> MiniAppRuntimeConfig:
    if not hasattr(db, "get"):
        return MiniAppRuntimeConfig()
    return await ConfigService(SystemConfigRepository(db)).get_miniapp_runtime_config()


def _build_miniapp_gate_message(config: MiniAppRuntimeConfig, fallback: str) -> str:
    return config.maintenance_message or fallback


def _evaluate_miniapp_runtime_access(
    config: MiniAppRuntimeConfig,
    *,
    feature: str,
    telegram_user_id: int | None = None,
) -> _MiniAppRuntimeDecision:
    is_canary_user = telegram_user_id is not None and telegram_user_id in config.canary_telegram_user_ids

    if config.mode == "maintenance":
        return _MiniAppRuntimeDecision(
            allowed=False,
            is_canary_user=is_canary_user,
            gate_reason_code="maintenance",
        )

    if not config.enabled:
        return _MiniAppRuntimeDecision(
            allowed=False,
            is_canary_user=is_canary_user,
            gate_reason_code="runtime_disabled",
        )

    if config.mode == "rollback" and feature in {"trial", "checkout"}:
        return _MiniAppRuntimeDecision(
            allowed=False,
            is_canary_user=is_canary_user,
            gate_reason_code="rollback",
        )

    feature_enabled = {
        "trial": config.trial_enabled,
        "checkout": config.checkout_enabled,
        "config": config.config_enabled,
    }.get(feature, True)
    if not feature_enabled:
        return _MiniAppRuntimeDecision(
            allowed=False,
            is_canary_user=is_canary_user,
            gate_reason_code="feature_disabled",
        )

    if config.mode == "canary" and not is_canary_user:
        return _MiniAppRuntimeDecision(
            allowed=False,
            is_canary_user=False,
            gate_reason_code="canary_not_allowed",
        )

    return _MiniAppRuntimeDecision(allowed=True, is_canary_user=is_canary_user)


def _assert_miniapp_runtime_enabled(
    config: MiniAppRuntimeConfig,
    *,
    feature: str,
    telegram_user_id: int | None = None,
) -> None:
    decision = _evaluate_miniapp_runtime_access(
        config,
        feature=feature,
        telegram_user_id=telegram_user_id,
    )
    if decision.allowed:
        return

    fallback = {
        "runtime_disabled": "Mini App is temporarily unavailable. Please try again later.",
        "maintenance": "Mini App is temporarily in maintenance mode. Please try again later.",
        "rollback": "Mini App trial and checkout are temporarily paused while rollback is in progress.",
        "feature_disabled": {
            "trial": "Trial activation is temporarily unavailable. Please try again later.",
            "checkout": "Checkout is temporarily unavailable. Please try again later.",
            "config": "Config delivery is temporarily unavailable. Please try again later.",
        }.get(feature, "Mini App feature is temporarily unavailable. Please try again later."),
        "canary_not_allowed": (
            "Mini App is in limited canary rollout. Please try again later or use the primary bot flow."
        ),
    }.get(
        decision.gate_reason_code,
        "Mini App feature is temporarily unavailable. Please try again later.",
    )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=_build_miniapp_gate_message(config, fallback),
    )


async def _resolve_miniapp_runtime_telegram_user_id(
    *,
    config: MiniAppRuntimeConfig,
    db: AsyncSession,
    user_id: UUID,
) -> int | None:
    if config.mode != "canary":
        return None
    mobile_user = await MobileUserRepository(db).get_by_id(user_id)
    if mobile_user is None:
        return None
    return mobile_user.telegram_id


def _build_primary_cta(
    *,
    subscription_status: str,
    trial_eligible: bool,
    has_config: bool,
) -> MiniAppBootstrapPrimaryCtaResponse:
    if subscription_status in {"active", "trial"}:
        if has_config:
            return MiniAppBootstrapPrimaryCtaResponse(kind="select_server", label="Select server")
        return MiniAppBootstrapPrimaryCtaResponse(kind="get_config", label="Get config")

    if subscription_status in {"expired", "grace_period"}:
        return MiniAppBootstrapPrimaryCtaResponse(kind="renew", label="Renew subscription")

    if trial_eligible:
        return MiniAppBootstrapPrimaryCtaResponse(kind="start_trial", label="Start trial")

    return MiniAppBootstrapPrimaryCtaResponse(kind="buy_plan", label="View plans")


def _build_usage_snapshot(
    remnawave_user: User | None,
    unavailable_reason: Literal["upstream_user_not_found", "upstream_unavailable"] = "upstream_user_not_found",
) -> MiniAppBootstrapUsageResponse:
    now = datetime.now(UTC)
    if remnawave_user is None:
        return MiniAppBootstrapUsageResponse(
            usageAvailable=False,
            usageSource="unavailable",
            usageUnavailableReason=unavailable_reason,
            bandwidthUsedBytes=0,
            bandwidthLimitBytes=0,
            connectionsActive=0,
            connectionsLimit=0,
            periodStart=now,
            periodEnd=now,
            lastConnectionAt=None,
        )

    if remnawave_user.last_traffic_reset_at:
        period_start = remnawave_user.last_traffic_reset_at
        next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        period_end = (
            remnawave_user.expire_at
            if remnawave_user.expire_at and remnawave_user.expire_at < next_month
            else next_month
        )
    else:
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        period_end = (
            remnawave_user.expire_at
            if remnawave_user.expire_at and remnawave_user.expire_at < next_month
            else next_month
        )

    return MiniAppBootstrapUsageResponse(
        usageAvailable=True,
        usageSource="remnawave",
        usageUnavailableReason=None,
        bandwidthUsedBytes=remnawave_user.used_traffic_bytes or 0,
        bandwidthLimitBytes=remnawave_user.traffic_limit_bytes or 0,
        connectionsActive=1 if remnawave_user.online_at else 0,
        connectionsLimit=remnawave_user.hwid_device_limit or 0,
        periodStart=period_start,
        periodEnd=period_end,
        lastConnectionAt=remnawave_user.online_at,
    )


async def _get_remnawave_user(
    *,
    client: RemnawaveClient,
    telegram_id: int | None,
) -> User | None:
    if telegram_id is None:
        return None
    gateway = RemnawaveUserGateway(client)
    return await gateway.get_by_telegram_id(telegram_id)


async def _get_remnawave_user_for_mobile_user(
    *,
    client: RemnawaveClient,
    mobile_user,
) -> User | None:
    gateway = RemnawaveUserGateway(client)
    if getattr(mobile_user, "remnawave_uuid", None):
        return await gateway.get_by_uuid(UUID(str(mobile_user.remnawave_uuid)))
    telegram_id = getattr(mobile_user, "telegram_id", None)
    if telegram_id is None:
        return None
    return await gateway.get_by_telegram_id(int(telegram_id))


async def _get_remnawave_user_for_provider_subject(
    *,
    client: RemnawaveClient,
    provider_subject_ref: str | None,
) -> User | None:
    if not provider_subject_ref:
        return None
    return await RemnawaveUserGateway(client).get_by_uuid(UUID(str(provider_subject_ref)))


def _build_config_response_from_remnawave_result(
    result: dict,
    *,
    subscription_url_fallback: str | None = None,
) -> MiniAppConfigResponse:
    subscription_url = normalize_public_subscription_url(result.get("subscription_url")) or (
        normalize_public_subscription_url(subscription_url_fallback)
        if subscription_url_fallback
        else None
    )
    config_string = subscription_url or result.get("config_string", "")
    return MiniAppConfigResponse(
        config=str(config_string),
        configString=str(config_string),
        clientType="subscription" if subscription_url else str(result.get("client_type", "subscription")),
        isFound=bool(result.get("is_found", True)),
        links=list(result.get("links", [])),
        ssConfLinks=dict(result.get("ss_conf_links", {})),
        source="remnawave_generated",
        subscriptionUrl=str(subscription_url) if subscription_url else None,
        generatedAt=datetime.now(UTC),
    )


async def _get_stage1_trial_provisioning_gateway(
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> Stage1TrialProvisioningGateway | None:
    if not settings.stage1_trial_provisioning_enabled:
        return None
    return RemnawaveStage1TrialProvisioningGateway(RemnawaveUserGateway(remnawave_client))


def _serialize_plan(plan) -> PlanResponse:
    return PlanResponse(
        uuid=str(plan.id),
        name=plan.name,
        plan_code=plan.plan_code or "",
        display_name=plan.display_name or plan.name,
        catalog_visibility=plan.catalog_visibility,
        duration_days=plan.duration_days,
        traffic_limit_bytes=plan.traffic_limit_bytes,
        devices_included=plan.device_limit,
        price_usd=float(plan.price_usd),
        price_rub=float(plan.price_rub) if plan.price_rub is not None else None,
        traffic_policy=TrafficPolicySchema.model_validate(
            plan.traffic_policy or {"mode": "fair_use", "display_label": "Unlimited"}
        ),
        connection_modes=plan.connection_modes or [],
        server_pool=plan.server_pool or [],
        support_sla=plan.support_sla,
        dedicated_ip=DedicatedIpSchema.model_validate(plan.dedicated_ip or {"included": 0, "eligible": False}),
        sale_channels=plan.sale_channels or [],
        invite_bundle=InviteBundleSchema.model_validate(
            plan.invite_bundle or {"count": 0, "friend_days": 0, "expiry_days": 0}
        ),
        trial_eligible=plan.trial_eligible,
        features=plan.features or {},
        is_active=plan.is_active,
        sort_order=plan.sort_order,
    )


def _serialize_addon(addon) -> AddonResponse:
    return AddonResponse(
        uuid=str(addon.id),
        code=addon.code,
        display_name=addon.display_name,
        duration_mode=addon.duration_mode,
        is_stackable=addon.is_stackable,
        quantity_step=addon.quantity_step,
        price_usd=float(addon.price_usd),
        price_rub=float(addon.price_rub) if addon.price_rub is not None else None,
        max_quantity_by_plan=addon.max_quantity_by_plan or {},
        delta_entitlements=addon.delta_entitlements or {},
        requires_location=addon.requires_location,
        sale_channels=addon.sale_channels or [],
        is_active=addon.is_active,
    )


def _build_legacy_config_response(subscription_url: str) -> MiniAppConfigResponse:
    normalized_subscription_url = normalize_public_subscription_url(subscription_url) or subscription_url
    return MiniAppConfigResponse(
        config=normalized_subscription_url,
        configString=normalized_subscription_url,
        clientType="subscription",
        isFound=True,
        links=[normalized_subscription_url],
        ssConfLinks={},
        source="legacy_subscription_url",
        subscriptionUrl=normalized_subscription_url,
        generatedAt=datetime.now(UTC),
    )


def _normalize_miniapp_request_status(error: Exception | None) -> str:
    if error is None:
        return "success"
    if isinstance(error, HTTPException):
        if error.status_code == 404:
            return "not_found"
        if error.status_code == 429:
            return "rate_limited"
        if 400 <= error.status_code < 500:
            return "client_error"
    return "server_error"


async def _build_miniapp_quote(
    *,
    body: MiniAppCheckoutRequest,
    db: AsyncSession,
    user_id: UUID,
    auth_realm_id: UUID,
) -> MiniAppCheckoutQuoteResponse:
    try:
        if body.flow == "addons" and body.subscription_key:
            result = await SelectedSubscriptionCheckoutUseCase(db).quote_addons(
                customer_account_id=user_id,
                auth_realm_id=auth_realm_id,
                subscription_key=body.subscription_key,
                addons=[
                    CheckoutAddonInput(
                        code=addon.code,
                        qty=addon.qty,
                        location_code=addon.location_code,
                    )
                    for addon in body.addons
                ],
                promo_code=body.promo_code,
                use_wallet=Decimal(str(body.use_wallet)),
                sale_channel="miniapp",
            )
            return _serialize_subscription_quote(result)

        if body.flow == "upgrade" and body.subscription_key:
            if body.plan_id is None:
                raise HTTPException(status_code=400, detail="planId is required for upgrade flow")
            result = await SelectedSubscriptionCheckoutUseCase(db).quote_upgrade(
                customer_account_id=user_id,
                auth_realm_id=auth_realm_id,
                subscription_key=body.subscription_key,
                target_plan_id=body.plan_id,
                promo_code=body.promo_code,
                use_wallet=Decimal(str(body.use_wallet)),
                sale_channel="miniapp",
            )
            return _serialize_subscription_quote(result)

        if body.flow == "addons":
            result = await PurchaseAddonsUseCase(db).execute(
                user_id=user_id,
                addons=[
                    CheckoutAddonInput(
                        code=addon.code,
                        qty=addon.qty,
                        location_code=addon.location_code,
                    )
                    for addon in body.addons
                ],
                promo_code=body.promo_code,
                use_wallet=Decimal(str(body.use_wallet)),
                sale_channel="miniapp",
            )
            return _serialize_subscription_quote(result)

        if body.flow == "upgrade":
            if body.plan_id is None:
                raise HTTPException(status_code=400, detail="planId is required for upgrade flow")
            result = await UpgradeSubscriptionUseCase(db).execute(
                user_id=user_id,
                target_plan_id=body.plan_id,
                promo_code=body.promo_code,
                use_wallet=Decimal(str(body.use_wallet)),
                sale_channel="miniapp",
            )
            return _serialize_subscription_quote(result)

        if body.plan_id is None:
            raise HTTPException(status_code=400, detail="planId is required for checkout flow")

        checkout_body = CheckoutQuoteRequest(
            plan_id=body.plan_id,
            addons=body.addons,
            code_input=body.code_input,
            promo_code=body.promo_code,
            partner_code=body.partner_code,
            use_wallet=body.use_wallet,
            currency=body.currency,
            channel="miniapp",
        )
        result = await _build_base_checkout_quote(
            body=checkout_body,
            db=db,
            user_id=user_id,
        )
        return _serialize_base_checkout_quote(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get("/bootstrap", response_model=MiniAppBootstrapResponse)
async def get_miniapp_bootstrap(
    locale: str = Query("en-EN", min_length=2, max_length=16),
    start_param: str | None = Query(None, alias="startParam", max_length=256),
    selected_subscription_key: str | None = Query(None, alias="selectedSubscriptionKey", min_length=1, max_length=220),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> MiniAppBootstrapResponse:
    started = perf_counter()
    error: Exception | None = None
    try:
        mobile_user_repo = MobileUserRepository(db)
        device_repo = MobileDeviceRepository(db)
        wallet_service = WalletService(WalletRepository(db))
        rollout = await _get_miniapp_runtime_config(db)

        mobile_user = await mobile_user_repo.get_by_id(user_id)
        if mobile_user is None:
            raise HTTPException(status_code=404, detail="Mobile user not found")

        subscription_list = await ListCustomerSubscriptionsUseCase(db).execute(
            customer_account_id=user_id,
            auth_realm_id=current_realm.auth_realm.id,
            selected_subscription_key=selected_subscription_key,
        )
        effective_selected_subscription_key = subscription_list.selected_subscription_key

        selected_entitlement_snapshot = None
        if effective_selected_subscription_key:
            selected_entitlement_snapshot = await GetCustomerSubscriptionEntitlementsUseCase(db).execute(
                customer_account_id=user_id,
                auth_realm_id=current_realm.auth_realm.id,
                subscription_key=effective_selected_subscription_key,
            )

        entitlement_snapshot = selected_entitlement_snapshot or await GetCurrentEntitlementStateUseCase(db).execute(
            customer_account_id=user_id,
            auth_realm_id=current_realm.auth_realm.id,
        )
        trial_status = await GetTrialStatusUseCase(db).execute(user_id)

        try:
            wallet = await wallet_service.get_balance(user_id)
            wallet_balance = float(wallet.balance)
            wallet_currency = wallet.currency
            wallet_bonuses = max(float(wallet.balance) - float(wallet.frozen), 0.0)
        except WalletNotFoundError:
            wallet_balance = 0.0
            wallet_currency = "USD"
            wallet_bonuses = 0.0

        referral_code = await GetReferralCodeUseCase(db).execute(user_id) if settings.referral_enabled else None
        invite_url = _build_invite_url(referral_code)
        mobile_devices = await device_repo.get_user_devices(user_id)

        current_service_state = None
        selected_service_state = None
        if mobile_user.telegram_id is not None:
            if effective_selected_subscription_key:
                try:
                    selected_service_state = await CustomerSubscriptionServiceAccessUseCase(db).get_service_state(
                        customer_account_id=user_id,
                        auth_realm_id=current_realm.auth_realm.id,
                        subscription_key=effective_selected_subscription_key,
                        provider_name="remnawave",
                        channel_type="telegram_bot",
                        channel_subject_ref=f"telegram-miniapp:{mobile_user.telegram_id}",
                        remnawave_client=remnawave_client,
                    )
                except (LookupError, PermissionError, ValueError) as exc:
                    logger.warning(
                        "Could not resolve selected Mini App service state",
                        extra={
                            "telegram_id": str(mobile_user.telegram_id),
                            "subscription_key": effective_selected_subscription_key,
                            "error": str(exc),
                        },
                    )
            if selected_service_state is None:
                current_service_state = await GetCurrentServiceStateUseCase(db).execute(
                    customer_account_id=user_id,
                    current_realm=current_realm,
                    provider_name="remnawave",
                    channel_type="telegram_bot",
                    channel_subject_ref=None,
                    provisioning_profile_key=None,
                    credential_type="telegram_bot",
                    credential_subject_key=f"telegram-miniapp:{mobile_user.telegram_id}",
                )

        remnawave_user = None
        usage_unavailable_reason: Literal[
            "upstream_user_not_found",
            "upstream_unavailable",
        ] = "upstream_user_not_found"
        try:
            selected_provider_subject_ref = (
                selected_service_state.service_identity.provider_subject_ref
                if selected_service_state and selected_service_state.service_identity is not None
                else None
            )
            remnawave_user = (
                await _get_remnawave_user_for_provider_subject(
                    client=remnawave_client,
                    provider_subject_ref=selected_provider_subject_ref,
                )
                if selected_provider_subject_ref
                else await _get_remnawave_user_for_mobile_user(
                    client=remnawave_client,
                    mobile_user=mobile_user,
                )
            )
        except Exception as exc:
            usage_unavailable_reason = "upstream_unavailable"
            logger.warning(
                "Could not fetch Mini App usage from Remnawave",
                extra={
                    "telegram_id": str(mobile_user.telegram_id),
                    "reason": usage_unavailable_reason,
                    "error": str(exc),
                },
            )
        rollout_access = _evaluate_miniapp_runtime_access(
            rollout,
            feature="bootstrap",
            telegram_user_id=mobile_user.telegram_id,
        )

        subscription_status = str(entitlement_snapshot.get("status") or "none")
        effective_entitlements = dict(entitlement_snapshot.get("effective_entitlements") or {})
        device_limit = int(effective_entitlements.get("device_limit") or 0)
        has_config = bool(
            mobile_user.subscription_url
            or (selected_service_state and selected_service_state.service_identity is not None)
            or (selected_service_state and selected_service_state.access_delivery_channel is not None)
            or (current_service_state and current_service_state.service_identity is not None)
            or (current_service_state and current_service_state.access_delivery_channel is not None)
        )

        return MiniAppBootstrapResponse(
            session=MiniAppBootstrapSessionResponse(
                authenticated=True,
                userId=str(mobile_user.id),
                telegramUserId=str(mobile_user.telegram_id) if mobile_user.telegram_id is not None else None,
                authRealm="customer",
            ),
            runtime=MiniAppBootstrapRuntimeResponse(
                tenant=MiniAppBootstrapRuntimeTenantResponse(kind="platform"),
                brand=MiniAppBootstrapRuntimeBrandResponse(
                    name="CyberVPN",
                    primaryColor="#00ffff",
                    supportUrl=_build_support_url(),
                    legalName="CyberVPN",
                ),
                commercialPolicy=MiniAppBootstrapRuntimeCommercialPolicyResponse(
                    pricingPolicyId="cybervpn-miniapp-default",
                    currencyPolicy="telegram_stars_xtr",
                    trialPolicyId="cybervpn-default-trial",
                ),
                attribution=MiniAppBootstrapRuntimeAttributionResponse(
                    source="telegram",
                    surface="miniapp",
                    startParam=start_param,
                ),
            ),
            user=MiniAppBootstrapUserResponse(
                firstName=mobile_user.telegram_username or mobile_user.username,
                username=mobile_user.telegram_username or mobile_user.username,
                locale=locale,
                rtl=_is_rtl_locale(locale),
            ),
            subscription=MiniAppBootstrapSubscriptionResponse(
                status=subscription_status,
                planId=entitlement_snapshot.get("plan_uuid"),
                planName=entitlement_snapshot.get("display_name"),
                expiresAt=entitlement_snapshot.get("expires_at"),
                autoRenew=False,
            ),
            trial=MiniAppBootstrapTrialResponse(
                eligible=trial_status.is_eligible,
                reason=None if trial_status.is_eligible else "already_used",
                durationDays=7,
                trialStart=trial_status.trial_start,
                trialEnd=trial_status.trial_end,
                daysRemaining=trial_status.days_remaining,
            ),
            wallet=MiniAppBootstrapWalletResponse(
                balance=wallet_balance,
                currency=wallet_currency,
                bonusesAvailable=wallet_bonuses,
            ),
            devices=MiniAppBootstrapDevicesResponse(
                activeCount=len(mobile_devices),
                limit=device_limit,
                hasConfig=has_config,
            ),
            usage=_build_usage_snapshot(
                remnawave_user,
                unavailable_reason=usage_unavailable_reason,
            ),
            serviceState=MiniAppBootstrapServiceStateResponse(
                providerName=(
                    "remnawave"
                    if (selected_service_state is not None or current_service_state is not None)
                    else None
                ),
                channelType=(
                    selected_service_state.access_delivery_channel.channel_type
                    if selected_service_state and selected_service_state.access_delivery_channel is not None
                    else
                    current_service_state.access_delivery_channel.channel_type
                    if current_service_state and current_service_state.access_delivery_channel is not None
                    else "telegram_bot"
                    if mobile_user.telegram_id is not None
                    else None
                ),
            ),
            recommendedServer=None,
            primaryCta=_build_primary_cta(
                subscription_status=subscription_status,
                trial_eligible=(rollout_access.allowed and rollout.trial_enabled and trial_status.is_eligible),
                has_config=has_config,
            ),
            referral=MiniAppBootstrapReferralResponse(
                code=referral_code,
                inviteUrl=invite_url,
                shareText=_build_referral_share_text(referral_code, invite_url),
            ),
            payment=MiniAppBootstrapPaymentResponse(),
            support=MiniAppBootstrapSupportResponse(
                url=_build_support_url(),
                paysupportCommandAvailable=bool(settings.telegram_bot_username.strip()),
            ),
            rollout=MiniAppBootstrapRolloutResponse(
                enabled=rollout.enabled,
                mode=rollout.mode,
                trialEnabled=rollout.trial_enabled,
                checkoutEnabled=rollout.checkout_enabled,
                configEnabled=rollout.config_enabled,
                accessGranted=rollout_access.allowed,
                isCanaryUser=rollout_access.is_canary_user,
                gateReasonCode=rollout_access.gate_reason_code,
                maintenanceMessage=rollout.maintenance_message,
            ),
            featureFlags={
                "miniapp_bootstrap_v1": True,
                "miniapp_network_server_picker_seeded": True,
                "miniapp_runtime_enabled": rollout.enabled,
                "miniapp_runtime_canary": rollout.mode == "canary",
                "miniapp_trial_enabled": rollout.trial_enabled,
                "miniapp_checkout_enabled": rollout.checkout_enabled,
                "miniapp_config_enabled": rollout.config_enabled,
                "stage1_referral_enabled": settings.referral_enabled,
                "stage1_promo_codes_enabled": settings.promo_codes_enabled,
                "stage1_gift_codes_enabled": settings.gift_codes_enabled,
                "stage1_checkout_code_discounts_enabled": settings.checkout_code_discounts_enabled,
            },
            freshness=MiniAppBootstrapFreshnessResponse(generatedAt=datetime.now(UTC)),
        )
    except Exception as exc:
        error = exc
        raise
    finally:
        track_miniapp_runtime_request(endpoint="bootstrap", status=_normalize_miniapp_request_status(error))
        observe_miniapp_runtime_duration(endpoint="bootstrap", duration_seconds=perf_counter() - started)


@router.get("/offers", response_model=MiniAppOffersResponse)
async def get_miniapp_offers(
    selected_subscription_key: str | None = Query(None, alias="selectedSubscriptionKey", min_length=1, max_length=220),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> MiniAppOffersResponse:
    started = perf_counter()
    error: Exception | None = None
    try:
        plan_repo = SubscriptionPlanRepository(db)
        addon_repo = PlanAddonRepository(db)

        plans = await plan_repo.list_catalog(
            visibility=CatalogVisibility.PUBLIC,
            sale_channel="miniapp",
            active_only=True,
        )
        addons = await addon_repo.list_catalog(active_only=True, sale_channel="miniapp")
        trial_status = await GetTrialStatusUseCase(db).execute(user_id)
        current_entitlements = None
        if selected_subscription_key:
            current_entitlements = await GetCustomerSubscriptionEntitlementsUseCase(db).execute(
                customer_account_id=user_id,
                auth_realm_id=current_realm.auth_realm.id,
                subscription_key=selected_subscription_key,
            )
        if current_entitlements is None:
            current_entitlements = await GetCurrentEntitlementsUseCase(db).execute(
                user_id,
                auth_realm_id=current_realm.auth_realm.id,
            )

        return MiniAppOffersResponse(
            plans=[_serialize_plan(plan) for plan in filter_stage1_public_paid_plans(plans, sale_channel="miniapp")],
            addons=[
                _serialize_addon(addon)
                for addon in filter_stage1_public_addons(
                    addons,
                    sale_channel="miniapp",
                    enabled=settings.stage1_addons_enabled,
                )
            ],
            trial=trial_status,
            currentEntitlements=current_entitlements,
            freshness=MiniAppBootstrapFreshnessResponse(generatedAt=datetime.now(UTC)),
        )
    except Exception as exc:
        error = exc
        raise
    finally:
        track_miniapp_runtime_request(endpoint="offers", status=_normalize_miniapp_request_status(error))
        observe_miniapp_runtime_duration(endpoint="offers", duration_seconds=perf_counter() - started)


@router.post("/trial/activate", response_model=MiniAppTrialActivateResponse)
async def activate_miniapp_trial(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    redis_client: redis.Redis = Depends(get_redis),
    provisioning_gateway: Stage1TrialProvisioningGateway | None = Depends(_get_stage1_trial_provisioning_gateway),
) -> MiniAppTrialActivateResponse:
    started = perf_counter()
    error: Exception | None = None
    rate_limit_key = f"trial_activate:{user_id}"
    rate_limit_window = STAGE1_TRIAL_ACTIVATE_RATE_LIMIT_WINDOW_SECONDS
    rate_limit_max = STAGE1_TRIAL_ACTIVATE_RATE_LIMIT_MAX

    try:
        rollout = await _get_miniapp_runtime_config(db)
        telegram_user_id = await _resolve_miniapp_runtime_telegram_user_id(
            config=rollout,
            db=db,
            user_id=user_id,
        )
        _assert_miniapp_runtime_enabled(
            rollout,
            feature="trial",
            telegram_user_id=telegram_user_id,
        )

        current_count = await redis_client.get(rate_limit_key)
        if current_count and int(current_count) >= rate_limit_max:
            ttl = await redis_client.ttl(rate_limit_key)
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again in {ttl} seconds.")

        try:
            result = await ActivateTrialUseCase(db, provisioning_gateway=provisioning_gateway).execute(user_id)
        except ValueError as exc:
            if "already activated" in str(exc):
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        if not result.activated:
            raise HTTPException(status_code=400, detail=result.message)

        pipe = redis_client.pipeline()
        await pipe.incr(rate_limit_key)
        await pipe.expire(rate_limit_key, rate_limit_window)
        await pipe.execute()

        track_trial_activation()
        return MiniAppTrialActivateResponse(
            activated=result.activated,
            trial_end=result.trial_end,
            message=result.message,
        )
    except Exception as exc:
        error = exc
        raise
    finally:
        track_miniapp_runtime_request(endpoint="trial_activate", status=_normalize_miniapp_request_status(error))
        observe_miniapp_runtime_duration(endpoint="trial_activate", duration_seconds=perf_counter() - started)


@router.post("/checkout/quote", response_model=MiniAppCheckoutQuoteResponse)
async def quote_miniapp_checkout(
    body: MiniAppCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> MiniAppCheckoutQuoteResponse:
    started = perf_counter()
    error: Exception | None = None
    try:
        rollout = await _get_miniapp_runtime_config(db)
        telegram_user_id = await _resolve_miniapp_runtime_telegram_user_id(
            config=rollout,
            db=db,
            user_id=user_id,
        )
        _assert_miniapp_runtime_enabled(
            rollout,
            feature="checkout",
            telegram_user_id=telegram_user_id,
        )
        return await _build_miniapp_quote(
            body=body,
            db=db,
            user_id=user_id,
            auth_realm_id=current_realm.auth_realm.id,
        )
    except Exception as exc:
        error = exc
        raise
    finally:
        track_miniapp_runtime_request(endpoint="checkout_quote", status=_normalize_miniapp_request_status(error))
        observe_miniapp_runtime_duration(endpoint="checkout_quote", duration_seconds=perf_counter() - started)


@router.post("/checkout/commit", response_model=MiniAppCheckoutCommitResponse)
async def commit_miniapp_checkout(
    body: MiniAppCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
) -> MiniAppCheckoutCommitResponse:
    started = perf_counter()
    error: Exception | None = None
    commit_metric_status = "server_error"
    payment_rail = "telegram_stars_xtr" if body.currency.upper() == "XTR" else "generic_checkout"
    response: MiniAppCheckoutCommitResponse | None = None
    try:
        if body.currency.upper() == "XTR":
            require_stage1_telegram_stars_enabled()
        else:
            require_stage1_payments_enabled()

        rollout = await _get_miniapp_runtime_config(db)
        telegram_user_id = await _resolve_miniapp_runtime_telegram_user_id(
            config=rollout,
            db=db,
            user_id=user_id,
        )
        _assert_miniapp_runtime_enabled(
            rollout,
            feature="checkout",
            telegram_user_id=telegram_user_id,
        )

        if body.flow == "addons":
            if body.subscription_key:
                result = await SelectedSubscriptionCheckoutUseCase(db).quote_addons(
                    customer_account_id=user_id,
                    auth_realm_id=current_realm.auth_realm.id,
                    subscription_key=body.subscription_key,
                    addons=[
                        CheckoutAddonInput(
                            code=addon.code,
                            qty=addon.qty,
                            location_code=addon.location_code,
                        )
                        for addon in body.addons
                    ],
                    promo_code=body.promo_code,
                    use_wallet=Decimal(str(body.use_wallet)),
                    sale_channel="miniapp",
                )
            else:
                result = await PurchaseAddonsUseCase(db).execute(
                    user_id=user_id,
                    addons=[
                        CheckoutAddonInput(
                            code=addon.code,
                            qty=addon.qty,
                            location_code=addon.location_code,
                        )
                        for addon in body.addons
                    ],
                    promo_code=body.promo_code,
                    use_wallet=Decimal(str(body.use_wallet)),
                    sale_channel="miniapp",
                )
            quote = _serialize_subscription_quote(result)
            commit_result = await CommitCheckoutUseCase(db, crypto_client).execute(
                user_id=user_id,
                quote_result=result,
                currency=body.currency,
                channel="miniapp",
                description=f"CyberVPN add-ons for {result.plan_name or 'plan'}",
                payload=f"{user_id}:{result.plan_id}:addons",
                checkout_mode="addon_only",
                payment_plan_id=None,
                use_quote_plan_id_for_payment=False,
                subscription_days_override=result.duration_days,
                metadata_extra={
                    "base_plan_id": str(result.plan_id) if result.plan_id else None,
                    "target_subscription_key": body.subscription_key,
                },
            )
        elif body.flow == "upgrade":
            if body.plan_id is None:
                raise HTTPException(status_code=400, detail="planId is required for upgrade flow")
            if body.subscription_key:
                result = await SelectedSubscriptionCheckoutUseCase(db).quote_upgrade(
                    customer_account_id=user_id,
                    auth_realm_id=current_realm.auth_realm.id,
                    subscription_key=body.subscription_key,
                    target_plan_id=body.plan_id,
                    promo_code=body.promo_code,
                    use_wallet=Decimal(str(body.use_wallet)),
                    sale_channel="miniapp",
                )
            else:
                result = await UpgradeSubscriptionUseCase(db).execute(
                    user_id=user_id,
                    target_plan_id=body.plan_id,
                    promo_code=body.promo_code,
                    use_wallet=Decimal(str(body.use_wallet)),
                    sale_channel="miniapp",
                )
            quote = _serialize_subscription_quote(result)
            commit_result = await CommitCheckoutUseCase(db, crypto_client).execute(
                user_id=user_id,
                quote_result=result,
                currency=body.currency,
                channel="miniapp",
                description=f"CyberVPN upgrade to {result.plan_name or 'plan'}",
                payload=f"{user_id}:{body.plan_id}:upgrade",
                checkout_mode="selected_subscription_upgrade" if body.subscription_key else "upgrade",
                payment_plan_id=result.plan_id,
                metadata_extra={"target_subscription_key": body.subscription_key},
            )
        else:
            if body.plan_id is None:
                raise HTTPException(status_code=400, detail="planId is required for checkout flow")
            checkout_body = CheckoutQuoteRequest(
                plan_id=body.plan_id,
                addons=body.addons,
                code_input=body.code_input,
                promo_code=body.promo_code,
                partner_code=body.partner_code,
                use_wallet=body.use_wallet,
                currency=body.currency,
                channel="miniapp",
            )
            result = await _build_base_checkout_quote(
                body=checkout_body,
                db=db,
                user_id=user_id,
            )
            quote = _serialize_base_checkout_quote(result)

            can_use_stars = body.currency.upper() == "XTR" and body.use_wallet <= 0 and len(body.addons) == 0
            if can_use_stars:
                payment_rail = "telegram_stars_xtr"
                mobile_user = await db.get(MobileUserModel, user_id)
                if mobile_user is None:
                    raise HTTPException(status_code=404, detail="User not found")
                stars_result = await create_telegram_stars_checkout(
                    db,
                    user=mobile_user,
                    quote_result=result,
                    channel="miniapp",
                    checkout_mode="new_purchase",
                    description=f"CyberVPN {result.plan_name or 'plan'} - {result.duration_days or 0} days",
                )
                await db.commit()
                response = MiniAppCheckoutCommitResponse(
                    **quote.model_dump(),
                    payment_id=stars_result.payment.id,
                    status="pending",
                    invoice=InvoiceResponse(
                        invoice_id=str(stars_result.payment.id),
                        payment_url=stars_result.invoice_url,
                        amount=float(stars_result.stars_amount),
                        currency="XTR",
                        status="pending",
                        expires_at=stars_result.expires_at,
                    ),
                )
                commit_metric_status = "pending"
            else:
                commit_result = await CommitCheckoutUseCase(db, crypto_client).execute(
                    user_id=user_id,
                    quote_result=result,
                    currency=body.currency,
                    channel="miniapp",
                    description=f"CyberVPN {result.plan_name or 'plan'} - {result.duration_days or 0} days",
                    payload=f"{user_id}:{body.plan_id}",
                    checkout_mode="new_purchase",
                    payment_plan_id=result.plan_id,
                )
                invoice = (
                    InvoiceResponse(**asdict(commit_result.invoice)) if commit_result.invoice is not None else None
                )
                commit_metric_status = str(commit_result.status or "completed")
                response = MiniAppCheckoutCommitResponse(
                    **quote.model_dump(),
                    payment_id=commit_result.payment.id,
                    status=commit_result.status,
                    invoice=invoice,
                )
        if response is None:
            invoice = InvoiceResponse(**asdict(commit_result.invoice)) if commit_result.invoice is not None else None
            commit_metric_status = str(commit_result.status or "completed")
            response = MiniAppCheckoutCommitResponse(
                **quote.model_dump(),
                payment_id=commit_result.payment.id,
                status=commit_result.status,
                invoice=invoice,
            )
    except ValueError as exc:
        error = HTTPException(status_code=400, detail=str(exc))
        commit_metric_status = "client_error"
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except (InsufficientWalletBalanceError, WalletNotFoundError) as exc:
        error = HTTPException(status_code=400, detail=str(exc))
        commit_metric_status = "client_error"
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except HTTPException as exc:
        error = exc
        commit_metric_status = _normalize_miniapp_request_status(exc)
        raise
    except Exception as exc:
        error = exc
        commit_metric_status = "server_error"
        raise HTTPException(status_code=500, detail="Payment processing failed") from None
    else:
        track_miniapp_checkout_commit(flow=body.flow, payment_rail=payment_rail, status=commit_metric_status)
        track_miniapp_runtime_request(endpoint="checkout_commit", status="success")
        observe_miniapp_runtime_duration(endpoint="checkout_commit", duration_seconds=perf_counter() - started)
        return response
    finally:
        if error is not None:
            track_miniapp_checkout_commit(flow=body.flow, payment_rail=payment_rail, status=commit_metric_status)
            track_miniapp_runtime_request(endpoint="checkout_commit", status=_normalize_miniapp_request_status(error))
            observe_miniapp_runtime_duration(endpoint="checkout_commit", duration_seconds=perf_counter() - started)


@router.get("/payments/{payment_id}", response_model=MiniAppPaymentStatusResponse)
async def get_miniapp_payment_status(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> MiniAppPaymentStatusResponse:
    started = perf_counter()
    error: Exception | None = None
    try:
        payment = await PaymentRepository(db).get_by_id(payment_id)
        if payment is None or payment.user_uuid != user_id:
            raise HTTPException(status_code=404, detail="Payment not found")

        track_miniapp_payment_status_check(provider=str(payment.provider), payment_status=str(payment.status))
        return MiniAppPaymentStatusResponse(
            payment_id=payment.id,
            status=payment.status,
            provider=payment.provider,
            external_id=payment.external_id,
            amount=float(payment.amount),
            currency=payment.currency,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
        )
    except Exception as exc:
        error = exc
        raise
    finally:
        track_miniapp_runtime_request(endpoint="payment_status", status=_normalize_miniapp_request_status(error))
        observe_miniapp_runtime_duration(endpoint="payment_status", duration_seconds=perf_counter() - started)


@router.get("/config", response_model=MiniAppConfigResponse)
async def get_miniapp_config(
    selected_subscription_key: str | None = Query(None, alias="selectedSubscriptionKey", min_length=1, max_length=220),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> MiniAppConfigResponse:
    started = perf_counter()
    error: Exception | None = None
    config_source = "unknown"
    try:
        rollout = await _get_miniapp_runtime_config(db)
        telegram_user_id = await _resolve_miniapp_runtime_telegram_user_id(
            config=rollout,
            db=db,
            user_id=user_id,
        )
        _assert_miniapp_runtime_enabled(
            rollout,
            feature="config",
            telegram_user_id=telegram_user_id,
        )

        mobile_user = await MobileUserRepository(db).get_by_id(user_id)
        if mobile_user is None:
            raise HTTPException(status_code=404, detail="Mobile user not found")

        if selected_subscription_key:
            try:
                result = await CustomerSubscriptionServiceAccessUseCase(db).get_config(
                    customer_account_id=user_id,
                    auth_realm_id=current_realm.auth_realm.id,
                    subscription_key=selected_subscription_key,
                    remnawave_client=remnawave_client,
                )
            except LookupError as exc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
            except PermissionError as exc:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

            config_source = "remnawave_generated"
            track_miniapp_config_delivery(source=config_source, status="success")
            return _build_config_response_from_remnawave_result(
                result,
            )

        if mobile_user.remnawave_uuid:
            try:
                result = await GenerateConfigUseCase(remnawave_client).execute(mobile_user.remnawave_uuid)
            except HTTPException as exc:
                if exc.status_code != status.HTTP_404_NOT_FOUND:
                    raise
            else:
                config_source = "remnawave_generated"
                track_miniapp_config_delivery(source=config_source, status="success")
                return _build_config_response_from_remnawave_result(
                    result,
                    subscription_url_fallback=mobile_user.subscription_url,
                )

        remnawave_user = await _get_remnawave_user(
            client=remnawave_client,
            telegram_id=mobile_user.telegram_id,
        )
        if remnawave_user is not None:
            result = await GenerateConfigUseCase(remnawave_client).execute(remnawave_user.uuid)
            config_source = "remnawave_generated"
            track_miniapp_config_delivery(source=config_source, status="success")
            return _build_config_response_from_remnawave_result(
                result,
                subscription_url_fallback=mobile_user.subscription_url,
            )

        if mobile_user.subscription_url:
            config_source = "legacy_subscription_url"
            track_miniapp_config_delivery(source=config_source, status="success")
            return _build_legacy_config_response(str(mobile_user.subscription_url))

        raise HTTPException(status_code=404, detail="Subscription config not found")
    except Exception as exc:
        error = exc
        track_miniapp_config_delivery(source=config_source, status=_normalize_miniapp_request_status(exc))
        raise
    finally:
        track_miniapp_runtime_request(endpoint="config", status=_normalize_miniapp_request_status(error))
        observe_miniapp_runtime_duration(endpoint="config", duration_seconds=perf_counter() - started)
