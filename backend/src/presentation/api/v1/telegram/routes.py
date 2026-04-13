"""Telegram bot integration routes."""

import hmac
import logging
import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select

from src.application.services.auth_service import AuthService
from src.application.use_cases.auth.oauth_login import OAuthLoginUseCase
from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.subscriptions import GenerateConfigUseCase
from src.application.use_cases.trial.activate_trial import ActivateTrialUseCase
from src.config.settings import settings
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.adapters import RemnawaveUserAdapter, get_remnawave_adapter
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveCreatedSubscriptionResponse
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.api.v1.telegram.schemas import (
    ConfigResponse,
    CreateSubscriptionRequest,
    CreateSubscriptionResponse,
    TelegramBotAccessSettingsResponse,
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
from src.presentation.dependencies.services import get_auth_service

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


def _build_bot_user_response(
    user: AdminUserModel,
    *,
    remnawave_user: Any | None = None,
) -> TelegramBotUserResponse:
    prefs = user.notification_prefs or {}
    stored_username = prefs.get("telegram_username") if isinstance(prefs, dict) else None
    stored_first_name = prefs.get("telegram_first_name") if isinstance(prefs, dict) else None

    has_subscription = bool(
        remnawave_user
        and (
            getattr(remnawave_user, "subscription_uuid", None) is not None
            or getattr(remnawave_user, "expire_at", None) is not None
            or getattr(remnawave_user, "subscription_url", None)
        )
    )
    status_value = getattr(getattr(remnawave_user, "status", None), "value", None)
    status = status_value if has_subscription and status_value else "none"
    subscription = _build_bot_subscription(remnawave_user)
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


@router.get("/bot/plans", response_model=list[dict[str, Any]])
async def get_bot_plans(
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
) -> list[dict[str, Any]]:
    """Return bot-facing plan catalog.

    The FastAPI auth backend is the integration boundary for the Telegram bot.
    Until plan catalog data is migrated into this backend, return an empty list
    instead of forcing the bot to call legacy upstreams directly.
    """
    _require_telegram_bot_secret(telegram_bot_secret)
    route_operations_total.labels(route="telegram_bot", action="list_plans", status="success").inc()
    return []


@router.get("/bot/user/{telegram_id}", response_model=TelegramBotUserResponse)
async def get_bot_user(
    telegram_id: int,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db=Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> TelegramBotUserResponse:
    """Return Telegram bot-facing user payload for bot menus/profile screens."""
    _require_telegram_bot_secret(telegram_bot_secret)

    user = await _get_bot_user_or_404(db, telegram_id)

    gateway = RemnawaveUserGateway(client=remnawave_client)
    remnawave_user = await gateway.get_by_telegram_id(telegram_id)

    route_operations_total.labels(route="telegram_bot", action="get_user", status="success").inc()
    return _build_bot_user_response(user, remnawave_user=remnawave_user)


@router.post("/bot/user", response_model=TelegramBotUserResponse)
async def create_or_bootstrap_bot_user(
    request: TelegramBotUserCreateRequest,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db=Depends(get_db),
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
        route_operations_total.labels(route="telegram_bot", action="upsert_user", status="success").inc()
        return _build_bot_user_response(existing)

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

    route_operations_total.labels(route="telegram_bot", action="create_user", status="success").inc()
    return _build_bot_user_response(user)


@router.patch("/bot/user/{telegram_id}", response_model=TelegramBotUserResponse)
async def update_bot_user(
    telegram_id: int,
    request: TelegramBotUserUpdateRequest,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db=Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
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

    gateway = RemnawaveUserGateway(client=remnawave_client)
    remnawave_user = await gateway.get_by_telegram_id(telegram_id)

    route_operations_total.labels(route="telegram_bot", action="update_user", status="success").inc()
    return _build_bot_user_response(user, remnawave_user=remnawave_user)


@router.get("/bot/user/{telegram_id}/subscriptions", response_model=list[TelegramBotSubscriptionResponse])
async def get_bot_user_subscriptions(
    telegram_id: int,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db=Depends(get_db),
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


@router.get("/bot/user/{telegram_id}/trial-status", response_model=TelegramBotTrialStatusResponse)
async def get_bot_user_trial_status(
    telegram_id: int,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db=Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> TelegramBotTrialStatusResponse:
    """Return Telegram bot-facing trial eligibility/status."""
    _require_telegram_bot_secret(telegram_bot_secret)

    user = await _get_bot_user_or_404(db, telegram_id)
    gateway = RemnawaveUserGateway(client=remnawave_client)
    remnawave_user = await gateway.get_by_telegram_id(telegram_id)

    route_operations_total.labels(route="telegram_bot", action="trial_status", status="success").inc()
    return _build_bot_trial_status(user, remnawave_user=remnawave_user)


@router.post("/bot/user/{telegram_id}/trial/activate", response_model=TelegramBotTrialStatusResponse)
async def activate_bot_user_trial(
    telegram_id: int,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db=Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> TelegramBotTrialStatusResponse:
    """Activate trial for a Telegram bot user."""
    _require_telegram_bot_secret(telegram_bot_secret)

    user = await _get_bot_user_or_404(db, telegram_id)
    gateway = RemnawaveUserGateway(client=remnawave_client)
    remnawave_user = await gateway.get_by_telegram_id(telegram_id)
    current_status = _build_bot_trial_status(user, remnawave_user=remnawave_user)
    if not current_status.eligible:
        return current_status

    use_case = ActivateTrialUseCase(db)
    await use_case.execute(user.id)
    refreshed_user = await _get_bot_user_or_404(db, telegram_id)

    route_operations_total.labels(route="telegram_bot", action="activate_trial", status="success").inc()
    return _build_bot_trial_status(refreshed_user, remnawave_user=remnawave_user)


@router.get("/bot/user/{telegram_id}/referral-stats", response_model=TelegramBotReferralStatsResponse)
async def get_bot_user_referral_stats(
    telegram_id: int,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db=Depends(get_db),
) -> TelegramBotReferralStatsResponse:
    """Return Telegram bot-facing referral stats."""
    _require_telegram_bot_secret(telegram_bot_secret)

    user = await _get_bot_user_or_404(db, telegram_id)
    referred_count = await db.scalar(
        select(func.count())
        .select_from(AdminUserModel)
        .where(AdminUserModel.referred_by_id == user.id)
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
