"""Telegram bot integration routes."""

import hmac
import logging
import secrets
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.entitlements_service import EntitlementsService
from src.application.use_cases.auth.oauth_login import OAuthLoginUseCase
from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.payments.checkout import CheckoutAddonInput, CheckoutUseCase
from src.application.use_cases.payments.commit_checkout import CommitCheckoutUseCase
from src.application.use_cases.subscriptions import GenerateConfigUseCase
from src.application.use_cases.subscriptions.get_current_entitlements import GetCurrentEntitlementsUseCase
from src.application.use_cases.trial.activate_trial import ActivateTrialUseCase
from src.config.settings import settings
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.plan_addon_repo import PlanAddonRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.payments.cryptobot.client import CryptoBotClient
from src.infrastructure.remnawave.adapters import RemnawaveUserAdapter, get_remnawave_adapter
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveCreatedSubscriptionResponse
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.api.v1.addons.schemas import AddonResponse
from src.presentation.api.v1.payments.schemas import (
    CheckoutAddonResponse,
    CheckoutCommitResponse,
    CheckoutQuoteResponse,
    EntitlementsSnapshotResponse,
    InvoiceResponse,
)
from src.presentation.api.v1.plans.schemas import PlanResponse
from src.presentation.api.v1.telegram.schemas import (
    ConfigResponse,
    CreateSubscriptionRequest,
    CreateSubscriptionResponse,
    TelegramBotAccessSettingsResponse,
    TelegramBotAddonResponse,
    TelegramBotCheckoutCommitResponse,
    TelegramBotCheckoutQuoteResponse,
    TelegramBotCheckoutRequest,
    TelegramBotEntitlementsResponse,
    TelegramBotPaymentStatusResponse,
    TelegramBotPlanResponse,
    TelegramBotReferralStatsResponse,
    TelegramBotSubscriptionResponse,
    TelegramBotTrialStatusResponse,
    TelegramBotUserCreateRequest,
    TelegramBotUserResponse,
    TelegramBotUserUpdateRequest,
    TelegramUserResponse,
)
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission
from src.presentation.dependencies.services import get_auth_service, get_crypto_client

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)


def _is_valid_telegram_bot_secret(secret: str | None) -> bool:
    configured = settings.telegram_bot_internal_secret.get_secret_value().strip()
    if not configured or not secret:
        return False
    return hmac.compare_digest(secret.strip(), configured)


def _require_telegram_bot_secret(secret: str | None) -> None:
    if _is_valid_telegram_bot_secret(secret):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


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
        traffic_policy=plan.traffic_policy or {"mode": "fair_use", "display_label": "Unlimited"},
        connection_modes=plan.connection_modes or [],
        server_pool=plan.server_pool or [],
        support_sla=plan.support_sla,
        dedicated_ip=plan.dedicated_ip or {"included": 0, "eligible": False},
        sale_channels=plan.sale_channels or [],
        invite_bundle=plan.invite_bundle or {"count": 0, "friend_days": 0, "expiry_days": 0},
        trial_eligible=plan.trial_eligible,
        features=plan.features or {},
        is_active=plan.is_active,
        sort_order=plan.sort_order,
    )


def _serialize_addon(model) -> AddonResponse:
    return AddonResponse(
        uuid=str(model.id),
        code=model.code,
        display_name=model.display_name,
        duration_mode=model.duration_mode,
        is_stackable=model.is_stackable,
        quantity_step=model.quantity_step,
        price_usd=float(model.price_usd),
        price_rub=float(model.price_rub) if model.price_rub is not None else None,
        max_quantity_by_plan=model.max_quantity_by_plan or {},
        delta_entitlements=model.delta_entitlements or {},
        requires_location=model.requires_location,
        sale_channels=model.sale_channels or [],
        is_active=model.is_active,
    )


def _serialize_quote(result) -> CheckoutQuoteResponse:
    return CheckoutQuoteResponse(
        base_price=float(result.base_price),
        addon_amount=float(result.addon_amount),
        displayed_price=float(result.displayed_price),
        discount_amount=float(result.discount_amount),
        wallet_amount=float(result.wallet_amount),
        gateway_amount=float(result.gateway_amount),
        partner_markup=float(result.partner_markup),
        is_zero_gateway=result.is_zero_gateway,
        plan_id=result.plan_id,
        promo_code_id=result.promo_code_id,
        partner_code_id=result.partner_code_id,
        addons=[
            CheckoutAddonResponse(
                addon_id=line.addon_id,
                code=line.code,
                display_name=line.display_name,
                qty=line.qty,
                unit_price=float(line.unit_price),
                total_price=float(line.total_price),
                location_code=line.location_code,
            )
            for line in result.addons
        ],
        entitlements_snapshot=EntitlementsSnapshotResponse.model_validate(result.entitlements_snapshot),
    )


def _placeholder_mobile_email(telegram_id: int) -> str:
    return f"tg{telegram_id}@telegram.local"


def _placeholder_mobile_username(*, telegram_id: int, username: str | None, first_name: str | None) -> str:
    if username:
        return username
    if first_name:
        return first_name[:50]
    return f"tg{telegram_id}"


async def _ensure_mobile_user(
    db: AsyncSession,
    *,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    language_code: str | None,
    referrer_id: int | None = None,
    auth_service: AuthService,
) -> MobileUserModel:
    mobile_repo = MobileUserRepository(db)
    mobile_user = await mobile_repo.get_by_telegram_id(telegram_id)
    referred_by_user_id: UUID | None = None
    if referrer_id:
        referrer = await mobile_repo.get_by_telegram_id(referrer_id)
        if referrer is not None:
            referred_by_user_id = referrer.id

    if mobile_user is None:
        password_hash = await auth_service.hash_password(secrets.token_urlsafe(32))
        mobile_user = MobileUserModel(
            email=_placeholder_mobile_email(telegram_id),
            password_hash=password_hash,
            username=_placeholder_mobile_username(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            ),
            telegram_id=telegram_id,
            telegram_username=username,
            status="active",
            is_active=True,
            referred_by_user_id=referred_by_user_id,
        )
        return await mobile_repo.create(mobile_user)

    changed = False
    if username is not None and mobile_user.telegram_username != username:
        mobile_user.telegram_username = username
        changed = True
    if mobile_user.username is None:
        mobile_user.username = _placeholder_mobile_username(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )
        changed = True
    if referred_by_user_id and mobile_user.referred_by_user_id is None:
        mobile_user.referred_by_user_id = referred_by_user_id
        changed = True
    if changed:
        mobile_user = await mobile_repo.update(mobile_user)
    return mobile_user


async def _get_mobile_user_or_404(db: AsyncSession, telegram_id: int) -> MobileUserModel:
    mobile_repo = MobileUserRepository(db)
    user = await mobile_repo.get_by_telegram_id(telegram_id)
    if user is not None:
        return user
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Mobile user with telegram_id {telegram_id} not found",
    )


async def _build_checkout_result(
    *,
    db: AsyncSession,
    user_id: UUID,
    body: TelegramBotCheckoutRequest,
) -> object:
    use_case = CheckoutUseCase(db)
    try:
        return await use_case.execute(
            user_id=user_id,
            plan_id=body.plan_id,
            promo_code=body.promo_code,
            use_wallet=Decimal(str(body.use_wallet)),
            addons=[
                CheckoutAddonInput(
                    code=addon.code,
                    qty=addon.qty,
                    location_code=addon.location_code,
                )
                for addon in body.addons
            ],
            sale_channel="telegram_bot",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


async def _build_mobile_trial_status(
    db: AsyncSession,
    mobile_user: MobileUserModel,
) -> TelegramBotTrialStatusResponse:
    entitlements = await GetCurrentEntitlementsUseCase(db).execute(mobile_user.id)
    now = datetime.now(UTC)
    is_trial_active = bool(mobile_user.trial_expires_at and mobile_user.trial_expires_at > now)

    if entitlements["status"] == "active":
        eligible = False
        reason = "active_subscription"
    elif mobile_user.trial_activated_at is not None:
        eligible = False
        reason = "already_used"
    else:
        eligible = True
        reason = None

    days_remaining = 0
    if is_trial_active and mobile_user.trial_expires_at is not None:
        days_remaining = max(0, (mobile_user.trial_expires_at - now).days)

    return TelegramBotTrialStatusResponse(
        eligible=eligible,
        reason=reason,
        is_trial_active=is_trial_active,
        trial_start=mobile_user.trial_activated_at,
        trial_end=mobile_user.trial_expires_at,
        days_remaining=days_remaining,
        duration_days=EntitlementsService.TRIAL_PERIOD_DAYS,
        expires_at=mobile_user.trial_expires_at,
        entitlements_snapshot=TelegramBotEntitlementsResponse(**entitlements),
    )


def _build_bot_user_response(
    user: AdminUserModel,
    *,
    remnawave_user: Any | None = None,
    entitlements_snapshot: dict | None = None,
) -> TelegramBotUserResponse:
    prefs = user.notification_prefs or {}
    stored_username = prefs.get("telegram_username") if isinstance(prefs, dict) else None
    stored_first_name = prefs.get("telegram_first_name") if isinstance(prefs, dict) else None
    effective_status = str((entitlements_snapshot or {}).get("status") or "none")

    has_subscription = bool(
        remnawave_user
        and (
            getattr(remnawave_user, "subscription_uuid", None) is not None
            or getattr(remnawave_user, "expire_at", None) is not None
            or getattr(remnawave_user, "subscription_url", None)
        )
    )
    status_value = getattr(getattr(remnawave_user, "status", None), "value", None) or effective_status
    status = status_value if has_subscription or effective_status in {"active", "trial"} else "none"
    subscription = _build_bot_subscription(remnawave_user)
    if subscription is None and entitlements_snapshot and status in {"active", "trial"}:
        subscription = TelegramBotSubscriptionResponse(
            status=status,
            plan_name=str(entitlements_snapshot.get("display_name") or entitlements_snapshot.get("plan_code") or "VPN"),
            expires_at=datetime.fromisoformat(
                str(entitlements_snapshot["expires_at"]).replace("Z", "+00:00")
            ) if entitlements_snapshot.get("expires_at") else None,
            traffic_limit_bytes=None,
            used_traffic_bytes=None,
            auto_renew=False,
        )
    subscriptions = [subscription.model_dump()] if subscription is not None else []

    return TelegramBotUserResponse(
        uuid=str(user.id),
        telegram_id=user.telegram_id or 0,
        username=stored_username or user.login,
        first_name=stored_first_name or user.display_name,
        language_code=user.language,
        status=status,
        is_admin=user.role == "admin",
        personal_discount=0.0,
        next_purchase_discount=0.0,
        referrer_id=None,
        points=0,
        subscription=subscription.model_dump() if subscription is not None else None,
        subscriptions=subscriptions,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _build_bot_subscription(remnawave_user: Any | None) -> TelegramBotSubscriptionResponse | None:
    has_subscription = bool(
        remnawave_user
        and (
            getattr(remnawave_user, "subscription_uuid", None) is not None
            or getattr(remnawave_user, "expire_at", None) is not None
            or getattr(remnawave_user, "subscription_url", None)
        )
    )
    if not has_subscription:
        return None

    status_value = getattr(getattr(remnawave_user, "status", None), "value", None) or "active"
    return TelegramBotSubscriptionResponse(
        status=status_value,
        plan_name="VPN",
        expires_at=getattr(remnawave_user, "expire_at", None),
        traffic_limit_bytes=getattr(remnawave_user, "traffic_limit_bytes", None),
        used_traffic_bytes=getattr(remnawave_user, "used_traffic_bytes", None),
        auto_renew=False,
    )


async def _get_bot_user_or_404(db: Any, telegram_id: int) -> AdminUserModel:
    user_repo = AdminUserRepository(db)
    user = await user_repo.get_by_telegram_id(telegram_id)
    if user:
        return user
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"User with telegram_id {telegram_id} not found",
    )


def _build_bot_trial_status(
    user: AdminUserModel,
    *,
    remnawave_user: Any | None = None,
) -> TelegramBotTrialStatusResponse:
    now = datetime.now(UTC)
    is_trial_active = bool(user.trial_expires_at and user.trial_expires_at > now)
    has_subscription = _build_bot_subscription(remnawave_user) is not None

    reason: str | None = None
    eligible = False
    if has_subscription:
        reason = "active_subscription"
    elif user.trial_activated_at is not None:
        reason = "already_used"
    else:
        eligible = True

    days_remaining = 0
    if is_trial_active and user.trial_expires_at is not None:
        days_remaining = max(0, (user.trial_expires_at - now).days)

    return TelegramBotTrialStatusResponse(
        eligible=eligible,
        reason=reason,
        is_trial_active=is_trial_active,
        trial_start=user.trial_activated_at,
        trial_end=user.trial_expires_at,
        days_remaining=days_remaining,
    )


@router.get("/user/{telegram_id}", response_model=TelegramUserResponse)
async def get_telegram_user(
    telegram_id: int,
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> TelegramUserResponse:
    """Get Telegram user information."""
    gateway = RemnawaveUserGateway(client=remnawave_client)
    user = await gateway.get_by_telegram_id(telegram_id=telegram_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with telegram_id {telegram_id} not found",
        )

    route_operations_total.labels(route="telegram", action="get_user", status="success").inc()
    return TelegramUserResponse(
        uuid=user.uuid,
        username=user.username,
        status=user.status,
        data_usage=user.data_usage,
        data_limit=user.data_limit,
        expires_at=user.expires_at,
        subscription_url=user.subscription_url,
    )


@router.post(
    "/user/{telegram_id}/subscription",
    response_model=CreateSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    telegram_id: int,
    request: CreateSubscriptionRequest,
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SUBSCRIPTION_CREATE)),
) -> CreateSubscriptionResponse:
    """Create a subscription for a Telegram user."""
    gateway = RemnawaveUserGateway(client=remnawave_client)
    user = await gateway.get_by_telegram_id(telegram_id=telegram_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with telegram_id {telegram_id} not found",
        )

    subscription_data = {
        "user_uuid": str(user.uuid),
        "plan_name": request.plan_name,
        "duration_days": request.duration_days,
    }

    result = await remnawave_client.post_validated(
        "/api/subscriptions",
        RemnawaveCreatedSubscriptionResponse,
        json=subscription_data,
    )

    route_operations_total.labels(route="telegram", action="create_subscription", status="success").inc()
    return CreateSubscriptionResponse(
        status="success",
        subscription_id=result.uuid or result.id,
        expires_at=result.expires_at,
    )


@router.get("/user/{telegram_id}/config", response_model=ConfigResponse)
async def get_user_config(
    telegram_id: int,
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> ConfigResponse:
    """Get VPN configuration for a Telegram user."""
    gateway = RemnawaveUserGateway(client=remnawave_client)
    user = await gateway.get_by_telegram_id(telegram_id=telegram_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with telegram_id {telegram_id} not found",
        )

    result = await GenerateConfigUseCase(remnawave_client).execute(user.uuid)

    route_operations_total.labels(route="telegram", action="get_config", status="success").inc()
    return ConfigResponse(
        config_string=str(result.get("config_string", "")),
        client_type=str(result.get("client_type", "subscription")),
    )


@router.get("/bot/settings/access", response_model=TelegramBotAccessSettingsResponse)
async def get_bot_access_settings(
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
) -> TelegramBotAccessSettingsResponse:
    """Return bot access settings for the Telegram bot service."""
    _require_telegram_bot_secret(telegram_bot_secret)
    return TelegramBotAccessSettingsResponse()


@router.get("/bot/plans", response_model=list[TelegramBotPlanResponse])
async def get_bot_plans(
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> list[TelegramBotPlanResponse]:
    """Return the canonical public catalog for the Telegram bot channel."""
    _require_telegram_bot_secret(telegram_bot_secret)
    repo = SubscriptionPlanRepository(db)
    plans = await repo.list_catalog(
        visibility="public",
        sale_channel="telegram_bot",
        active_only=True,
    )
    route_operations_total.labels(route="telegram_bot", action="list_plans", status="success").inc()
    return [_serialize_plan(plan) for plan in plans]


@router.get("/bot/addons/catalog", response_model=list[TelegramBotAddonResponse])
async def get_bot_addons_catalog(
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> list[TelegramBotAddonResponse]:
    """Return the canonical add-on catalog for the Telegram bot channel."""
    _require_telegram_bot_secret(telegram_bot_secret)
    repo = PlanAddonRepository(db)
    addons = await repo.list_catalog(active_only=True, sale_channel="telegram_bot")
    route_operations_total.labels(route="telegram_bot", action="list_addons", status="success").inc()
    return [_serialize_addon(addon) for addon in addons]


@router.get("/bot/user/{telegram_id}", response_model=TelegramBotUserResponse)
async def get_bot_user(
    telegram_id: int,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> TelegramBotUserResponse:
    """Return Telegram bot-facing user payload for bot menus/profile screens."""
    _require_telegram_bot_secret(telegram_bot_secret)

    user = await _get_bot_user_or_404(db, telegram_id)
    mobile_user = await MobileUserRepository(db).get_by_telegram_id(telegram_id)

    gateway = RemnawaveUserGateway(client=remnawave_client)
    remnawave_user = await gateway.get_by_telegram_id(telegram_id)
    entitlements_snapshot = (
        await GetCurrentEntitlementsUseCase(db).execute(mobile_user.id)
        if mobile_user is not None
        else None
    )

    route_operations_total.labels(route="telegram_bot", action="get_user", status="success").inc()
    return _build_bot_user_response(
        user,
        remnawave_user=remnawave_user,
        entitlements_snapshot=entitlements_snapshot,
    )


@router.post("/bot/user", response_model=TelegramBotUserResponse)
async def create_or_bootstrap_bot_user(
    request: TelegramBotUserCreateRequest,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    remnawave_adapter: RemnawaveUserAdapter = Depends(get_remnawave_adapter),
) -> TelegramBotUserResponse:
    """Create or refresh a Telegram bot user in the FastAPI auth backend."""
    _require_telegram_bot_secret(telegram_bot_secret)

    user_repo = AdminUserRepository(db)
    existing = await user_repo.get_by_telegram_id(request.telegram_id)
    if existing:
        prefs = dict(existing.notification_prefs or {})
        prefs["telegram_username"] = request.username
        prefs["telegram_first_name"] = request.first_name
        existing.notification_prefs = prefs
        if request.first_name:
            existing.display_name = request.first_name
        if request.language_code:
            existing.language = request.language_code
        if request.referrer_id and existing.referred_by_id is None:
            referrer = await user_repo.get_by_telegram_id(request.referrer_id)
            if referrer:
                existing.referred_by_id = referrer.id
        await user_repo.update(existing)
        mobile_user = await _ensure_mobile_user(
            db,
            telegram_id=request.telegram_id,
            username=request.username,
            first_name=request.first_name,
            language_code=request.language_code,
            referrer_id=request.referrer_id,
            auth_service=auth_service,
        )
        entitlements_snapshot = await GetCurrentEntitlementsUseCase(db).execute(mobile_user.id)
        route_operations_total.labels(route="telegram_bot", action="upsert_user", status="success").inc()
        return _build_bot_user_response(existing, entitlements_snapshot=entitlements_snapshot)

    login = OAuthLoginUseCase._generate_telegram_login(
        username=request.username,
        first_name=request.first_name,
        telegram_id=str(request.telegram_id),
    )
    while await user_repo.get_by_login(login):
        login = f"{login}_{secrets.token_hex(3)}"

    password_hash = await auth_service.hash_password(secrets.token_urlsafe(32))
    notification_prefs = {
        "telegram_username": request.username,
        "telegram_first_name": request.first_name,
    }
    referred_by_id = None
    if request.referrer_id:
        referrer = await user_repo.get_by_telegram_id(request.referrer_id)
        if referrer:
            referred_by_id = referrer.id
    user = AdminUserModel(
        login=login,
        password_hash=password_hash,
        telegram_id=request.telegram_id,
        role="viewer",
        is_active=True,
        is_email_verified=True,
        language=request.language_code or "en",
        display_name=request.first_name,
        notification_prefs=notification_prefs,
        referred_by_id=referred_by_id,
    )
    user = await user_repo.create(user)
    mobile_user = await _ensure_mobile_user(
        db,
        telegram_id=request.telegram_id,
        username=request.username,
        first_name=request.first_name,
        language_code=request.language_code,
        referrer_id=request.referrer_id,
        auth_service=auth_service,
    )

    try:
        await remnawave_adapter.create_user(
            username=user.login,
            email="",
            telegram_id=request.telegram_id,
        )
    except Exception as exc:
        # Best-effort provisioning: Telegram bot should remain operational even if upstream provisioning fails.
        logger.warning(
            "telegram_bot_user_provisioning_failed",
            extra={"telegram_id": request.telegram_id, "error": str(exc)},
        )

    entitlements_snapshot = await GetCurrentEntitlementsUseCase(db).execute(mobile_user.id)
    route_operations_total.labels(route="telegram_bot", action="create_user", status="success").inc()
    return _build_bot_user_response(user, entitlements_snapshot=entitlements_snapshot)


@router.patch("/bot/user/{telegram_id}", response_model=TelegramBotUserResponse)
async def update_bot_user(
    telegram_id: int,
    request: TelegramBotUserUpdateRequest,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    auth_service: AuthService = Depends(get_auth_service),
) -> TelegramBotUserResponse:
    """Update Telegram-facing profile details for a bot user."""
    _require_telegram_bot_secret(telegram_bot_secret)

    user_repo = AdminUserRepository(db)
    user = await user_repo.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with telegram_id {telegram_id} not found",
        )

    prefs = dict(user.notification_prefs or {})
    if request.username is not None:
        prefs["telegram_username"] = request.username
    if request.first_name is not None:
        prefs["telegram_first_name"] = request.first_name
        user.display_name = request.first_name
    user.notification_prefs = prefs
    if request.language_code:
        user.language = request.language_code

    await user_repo.update(user)
    mobile_user = await _ensure_mobile_user(
        db,
        telegram_id=telegram_id,
        username=request.username,
        first_name=request.first_name,
        language_code=request.language_code,
        auth_service=auth_service,
    )

    gateway = RemnawaveUserGateway(client=remnawave_client)
    remnawave_user = await gateway.get_by_telegram_id(telegram_id)
    entitlements_snapshot = await GetCurrentEntitlementsUseCase(db).execute(mobile_user.id)

    route_operations_total.labels(route="telegram_bot", action="update_user", status="success").inc()
    return _build_bot_user_response(
        user,
        remnawave_user=remnawave_user,
        entitlements_snapshot=entitlements_snapshot,
    )


@router.get("/bot/user/{telegram_id}/subscriptions", response_model=list[TelegramBotSubscriptionResponse])
async def get_bot_user_subscriptions(
    telegram_id: int,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> list[TelegramBotSubscriptionResponse]:
    """Return Telegram bot-facing subscriptions list."""
    _require_telegram_bot_secret(telegram_bot_secret)

    await _get_bot_user_or_404(db, telegram_id)
    gateway = RemnawaveUserGateway(client=remnawave_client)
    remnawave_user = await gateway.get_by_telegram_id(telegram_id)
    subscription = _build_bot_subscription(remnawave_user)

    route_operations_total.labels(route="telegram_bot", action="list_subscriptions", status="success").inc()
    return [subscription] if subscription is not None else []


@router.get("/bot/user/{telegram_id}/entitlements", response_model=TelegramBotEntitlementsResponse)
async def get_bot_user_entitlements(
    telegram_id: int,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> TelegramBotEntitlementsResponse:
    """Return the canonical current entitlement snapshot for a Telegram bot user."""
    _require_telegram_bot_secret(telegram_bot_secret)
    mobile_user = await _get_mobile_user_or_404(db, telegram_id)
    snapshot = await GetCurrentEntitlementsUseCase(db).execute(mobile_user.id)
    route_operations_total.labels(route="telegram_bot", action="entitlements", status="success").inc()
    return TelegramBotEntitlementsResponse(**snapshot)


@router.post("/bot/user/{telegram_id}/checkout/quote", response_model=TelegramBotCheckoutQuoteResponse)
async def quote_bot_user_checkout(
    telegram_id: int,
    body: TelegramBotCheckoutRequest,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> TelegramBotCheckoutQuoteResponse:
    """Calculate checkout totals for the Telegram bot without creating a payment."""
    _require_telegram_bot_secret(telegram_bot_secret)
    mobile_user = await _get_mobile_user_or_404(db, telegram_id)
    result = await _build_checkout_result(db=db, user_id=mobile_user.id, body=body)
    route_operations_total.labels(route="telegram_bot", action="checkout_quote", status="success").inc()
    return _serialize_quote(result)


@router.post("/bot/user/{telegram_id}/checkout/commit", response_model=TelegramBotCheckoutCommitResponse)
async def commit_bot_user_checkout(
    telegram_id: int,
    body: TelegramBotCheckoutRequest,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
) -> TelegramBotCheckoutCommitResponse:
    """Create a payment and optional invoice for a Telegram bot checkout basket."""
    _require_telegram_bot_secret(telegram_bot_secret)
    if body.payment_method != "cryptobot":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot checkout currently supports only cryptobot payments",
        )

    mobile_user = await _get_mobile_user_or_404(db, telegram_id)
    result = await _build_checkout_result(db=db, user_id=mobile_user.id, body=body)
    quote_response = _serialize_quote(result)
    commit_use_case = CommitCheckoutUseCase(db, crypto_client)

    try:
        commit_result = await commit_use_case.execute(
            user_id=mobile_user.id,
            quote_result=result,
            currency=body.currency,
            channel="telegram_bot",
            description=f"CyberVPN {result.plan_name or 'plan'} - {result.duration_days or 0} days",
            payload=f"tg:{telegram_id}:{body.plan_id}",
            checkout_mode="new_purchase",
            payment_plan_id=result.plan_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    except Exception:
        logger.exception("telegram_bot_checkout_commit_failed", extra={"telegram_id": telegram_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Telegram bot payment processing failed",
        ) from None

    invoice = InvoiceResponse(**asdict(commit_result.invoice)) if commit_result.invoice is not None else None
    route_operations_total.labels(route="telegram_bot", action="checkout_commit", status=commit_result.status).inc()
    return CheckoutCommitResponse(
        **quote_response.model_dump(),
        payment_id=commit_result.payment.id,
        status=commit_result.status,
        invoice=invoice,
    )


@router.get("/bot/user/{telegram_id}/payments/{payment_id}", response_model=TelegramBotPaymentStatusResponse)
async def get_bot_user_payment_status(
    telegram_id: int,
    payment_id: UUID,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> TelegramBotPaymentStatusResponse:
    """Return the status of a previously created Telegram bot payment."""
    _require_telegram_bot_secret(telegram_bot_secret)
    mobile_user = await _get_mobile_user_or_404(db, telegram_id)
    payment = await PaymentRepository(db).get_by_id(payment_id)
    if payment is None or payment.user_uuid != mobile_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    route_operations_total.labels(route="telegram_bot", action="payment_status", status=payment.status).inc()
    return TelegramBotPaymentStatusResponse(
        payment_id=payment.id,
        status=payment.status,
        provider=payment.provider,
        external_id=payment.external_id,
        amount=float(payment.amount),
        currency=payment.currency,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )


@router.get("/bot/user/{telegram_id}/trial-status", response_model=TelegramBotTrialStatusResponse)
async def get_bot_user_trial_status(
    telegram_id: int,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> TelegramBotTrialStatusResponse:
    """Return Telegram bot-facing trial eligibility/status."""
    _require_telegram_bot_secret(telegram_bot_secret)

    user = await _get_mobile_user_or_404(db, telegram_id)
    route_operations_total.labels(route="telegram_bot", action="trial_status", status="success").inc()
    return await _build_mobile_trial_status(db, user)


@router.post("/bot/user/{telegram_id}/trial/activate", response_model=TelegramBotTrialStatusResponse)
async def activate_bot_user_trial(
    telegram_id: int,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> TelegramBotTrialStatusResponse:
    """Activate trial for a Telegram bot user."""
    _require_telegram_bot_secret(telegram_bot_secret)

    user = await _get_mobile_user_or_404(db, telegram_id)
    current_status = await _build_mobile_trial_status(db, user)
    if not current_status.eligible:
        return current_status

    use_case = ActivateTrialUseCase(db)
    await use_case.execute(user.id)
    refreshed_user = await _get_mobile_user_or_404(db, telegram_id)

    route_operations_total.labels(route="telegram_bot", action="activate_trial", status="success").inc()
    return await _build_mobile_trial_status(db, refreshed_user)


@router.get("/bot/user/{telegram_id}/referral-stats", response_model=TelegramBotReferralStatsResponse)
async def get_bot_user_referral_stats(
    telegram_id: int,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> TelegramBotReferralStatsResponse:
    """Return Telegram bot-facing referral stats."""
    _require_telegram_bot_secret(telegram_bot_secret)

    user = await _get_mobile_user_or_404(db, telegram_id)
    referred_count = await db.scalar(
        select(func.count())
        .select_from(MobileUserModel)
        .where(MobileUserModel.referred_by_user_id == user.id)
    )

    route_operations_total.labels(route="telegram_bot", action="referral_stats", status="success").inc()
    username = settings.telegram_bot_username.strip()
    link = f"https://t.me/{username}?start=ref_{telegram_id}" if username else None
    return TelegramBotReferralStatsResponse(
        total_referrals=int(referred_count or 0),
        bonus_days=0,
        referral_link=link,
    )


@router.get("/bot/user/{telegram_id}/config", response_model=ConfigResponse)
async def get_bot_user_config(
    telegram_id: int,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> ConfigResponse:
    """Return Telegram bot-facing VPN config using the FastAPI backend as gateway."""
    _require_telegram_bot_secret(telegram_bot_secret)

    gateway = RemnawaveUserGateway(client=remnawave_client)
    user = await gateway.get_by_telegram_id(telegram_id=telegram_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with telegram_id {telegram_id} not found",
        )

    result = await GenerateConfigUseCase(remnawave_client).execute(user.uuid)
    route_operations_total.labels(route="telegram_bot", action="get_config", status="success").inc()
    return ConfigResponse(
        config_string=str(result.get("config_string", "")),
        client_type=str(result.get("client_type", "subscription")),
    )
