from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_session_issuer import hash_device_key
from src.application.services.config_service import ConfigService
from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.customer_onboarding import (
    ApplyCustomerOnboardingGrowthCodeUseCase,
    ConnectionPlatform,
    ConnectionSurface,
    CustomerConnectionBootstrapResult,
    CustomerOnboardingAppliedCode,
    CustomerOnboardingApplyResult,
    CustomerOnboardingCodeApplier,
    CustomerOnboardingCodePreviewer,
    CustomerOnboardingConnectionBootstrapUseCase,
    CustomerOnboardingCurrentState,
    CustomerOnboardingFlowTokenService,
    CustomerOnboardingMarkConnectedUseCase,
    CustomerOnboardingPreviewResult,
    CustomerOnboardingSkipResult,
    CustomerOnboardingUnavailableError,
    GetCurrentCustomerOnboardingUseCase,
    PreviewCustomerOnboardingGrowthCodeUseCase,
    SkipCustomerOnboardingUseCase,
)
from src.application.use_cases.customer_subscriptions import (
    CustomerSubscriptionServiceAccessUseCase,
    ListCustomerSubscriptionsUseCase,
)
from src.application.use_cases.gifts import RedeemGiftCodeUseCase
from src.application.use_cases.growth_codes import GrowthCodeResolutionOutcome, ResolveGrowthCodeUseCase
from src.application.use_cases.invites.redeem_invite import InviteRedemptionRuntimeContext, RedeemInviteUseCase
from src.application.use_cases.service_access import GetCurrentEntitlementStateUseCase
from src.application.use_cases.subscriptions import GenerateConfigUseCase
from src.config.settings import settings
from src.domain.entities.auth_realm import DEFAULT_AUTH_REALMS, stable_auth_realm_id
from src.domain.enums import (
    GrowthCodeActionContext,
    GrowthCodeRejectReason,
    GrowthCodeResolutionStatus,
    GrowthCodeType,
    GrowthCodeWrongContextTarget,
)
from src.domain.exceptions import (
    InviteCodeAlreadyUsedError,
    InviteCodeExpiredError,
    InviteCodeNotFoundError,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.infrastructure.database.repositories.customer_onboarding_repo import (
    CustomerConnectionSessionSqlAlchemyRepository,
    CustomerOnboardingStateSqlAlchemyRepository,
)
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    observe_customer_onboarding_apply,
    observe_customer_onboarding_connection_bootstrap,
    observe_customer_onboarding_preview,
    observe_customer_onboarding_skip,
)
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.subscription_urls import normalize_public_subscription_url
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.dependencies.auth import get_current_mobile_user_id, get_optional_current_mobile_user_id
from src.presentation.dependencies.auth_realms import get_request_customer_realm
from src.presentation.dependencies.client_ip import resolve_client_ip
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_remnawave_client

from .schemas import (
    CustomerOnboardingApplyRequest,
    CustomerOnboardingApplyResponse,
    CustomerOnboardingConnectionAppRecommendation,
    CustomerOnboardingConnectionBootstrapResponse,
    CustomerOnboardingConnectionInstruction,
    CustomerOnboardingConnectionInstructionStep,
    CustomerOnboardingCurrentResponse,
    CustomerOnboardingPreviewRequest,
    CustomerOnboardingPreviewResponse,
    CustomerOnboardingSkipRequest,
    CustomerOnboardingSkipResponse,
    MarkOnboardingConnectionConnectedRequest,
    MarkOnboardingConnectionConnectedResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customer/onboarding", tags=["customer-onboarding"])

_CUSTOMER_ONBOARDING_SURFACE = "customer_onboarding"


@dataclass(frozen=True, slots=True)
class _ConnectionConfigSnapshot:
    subscription_url: str | None
    config_profile_name: str | None
    service_identity_ready: bool


@router.get("/current", response_model=CustomerOnboardingCurrentResponse)
async def get_current_customer_onboarding(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> CustomerOnboardingCurrentResponse:
    runtime_config = await ConfigService(SystemConfigRepository(db)).get_customer_onboarding_runtime_config()
    state = await GetCurrentCustomerOnboardingUseCase(
        runtime_config=runtime_config,
        state_repo=CustomerOnboardingStateSqlAlchemyRepository(db),
        flow_tokens=CustomerOnboardingFlowTokenService(),
    ).execute(user_id=user_id)
    return _current_response(state)


@router.post("/growth-code/apply", response_model=CustomerOnboardingApplyResponse)
async def apply_customer_onboarding_growth_code(
    payload: CustomerOnboardingApplyRequest,
    request: Request,
    user_id: UUID | None = Depends(get_optional_current_mobile_user_id),
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
    db: AsyncSession = Depends(get_db),
) -> CustomerOnboardingApplyResponse:
    trusted_source_surface = _trusted_apply_source_surface(
        requested_source_surface=payload.source_surface,
        telegram_bot_secret=telegram_bot_secret,
    )
    resolved_user_id, resolved_realm = await _resolve_customer_onboarding_actor(
        db=db,
        authenticated_user_id=user_id,
        source_surface=trusted_source_surface,
        telegram_id=payload.telegram_id,
        telegram_bot_secret=telegram_bot_secret,
        current_realm=current_realm,
    )
    runtime_config = await ConfigService(SystemConfigRepository(db)).get_customer_onboarding_runtime_config()
    state_repo = CustomerOnboardingStateSqlAlchemyRepository(db)
    allow_without_prompt = False
    try:
        if trusted_source_surface == "telegram_bot":
            if not runtime_config.telegram_bot_code_apply_available:
                raise CustomerOnboardingUnavailableError(
                    code="CUSTOMER_ONBOARDING_TELEGRAM_CODE_APPLY_UNAVAILABLE",
                    message_key="onboarding.telegram_code_apply_unavailable",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            existing_state = await state_repo.get_current(
                user_id=resolved_user_id,
                flow_key=runtime_config.flow_key,
                version=runtime_config.version,
            )
            if existing_state is None:
                await state_repo.ensure_pending(
                    user_id=resolved_user_id,
                    runtime_config=runtime_config,
                    source_channel="telegram_bot",
                    auth_channel="telegram_bot",
                )
                logger.info(
                    "customer_onboarding_state_auto_created",
                    extra={"source_surface": trusted_source_surface, "flow_key": runtime_config.flow_key},
                )
            allow_without_prompt = True

        result = await ApplyCustomerOnboardingGrowthCodeUseCase(
            runtime_config=runtime_config,
            state_repo=state_repo,
            flow_tokens=CustomerOnboardingFlowTokenService(),
        ).execute(
            user_id=resolved_user_id,
            code=payload.code,
            flow_token=payload.flow_token,
            idempotency_key=payload.idempotency_key,
            require_flow_token=trusted_source_surface != "telegram_bot",
            allow_without_prompt=allow_without_prompt,
            code_applier=CustomerOnboardingGrowthCodeApplier(
                db,
                current_realm=resolved_realm,
                source_surface=trusted_source_surface,
                runtime_context=_invite_redemption_runtime_context(request),
            ),
        )
    except CustomerOnboardingUnavailableError as exc:
        if exc.code.startswith("CUSTOMER_ONBOARDING_CODE_"):
            await db.commit()
        else:
            await db.rollback()
        observe_customer_onboarding_apply(status=exc.code, code_type=None)
        raise _onboarding_http_error(exc) from exc
    if result.commit_required:
        await db.commit()
    observe_customer_onboarding_apply(status=result.status, code_type=result.code_type)
    return _apply_response(result)


@router.post("/growth-code/preview", response_model=CustomerOnboardingPreviewResponse)
async def preview_customer_onboarding_growth_code(
    payload: CustomerOnboardingPreviewRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> CustomerOnboardingPreviewResponse:
    runtime_config = await ConfigService(SystemConfigRepository(db)).get_customer_onboarding_runtime_config()
    try:
        result = await PreviewCustomerOnboardingGrowthCodeUseCase(
            runtime_config=runtime_config,
            flow_tokens=CustomerOnboardingFlowTokenService(),
        ).execute(
            user_id=user_id,
            code=payload.code,
            flow_token=payload.flow_token,
            code_previewer=CustomerOnboardingGrowthCodePreviewer(db),
        )
    except CustomerOnboardingUnavailableError as exc:
        await db.rollback()
        observe_customer_onboarding_preview(status=exc.code, detected_code_type=None)
        raise _onboarding_http_error(exc) from exc
    await db.rollback()
    observe_customer_onboarding_preview(status=result.status, detected_code_type=result.detected_code_type)
    return _preview_response(result)


@router.post("/growth-code/skip", response_model=CustomerOnboardingSkipResponse)
async def skip_customer_onboarding_growth_code(
    payload: CustomerOnboardingSkipRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> CustomerOnboardingSkipResponse:
    runtime_config = await ConfigService(SystemConfigRepository(db)).get_customer_onboarding_runtime_config()
    try:
        result = await SkipCustomerOnboardingUseCase(
            runtime_config=runtime_config,
            state_repo=CustomerOnboardingStateSqlAlchemyRepository(db),
            flow_tokens=CustomerOnboardingFlowTokenService(),
        ).execute(
            user_id=user_id,
            flow_token=payload.flow_token,
            idempotency_key=payload.idempotency_key,
        )
    except CustomerOnboardingUnavailableError as exc:
        observe_customer_onboarding_skip(status=exc.code)
        raise _onboarding_http_error(exc) from exc
    if result.commit_required:
        await db.commit()
    observe_customer_onboarding_skip(status=result.status)
    return _skip_response(result)


@router.get("/connection/bootstrap", response_model=CustomerOnboardingConnectionBootstrapResponse)
async def get_customer_onboarding_connection_bootstrap(
    response: Response,
    surface: ConnectionSurface = Query("web"),
    platform_hint: ConnectionPlatform = Query("unknown"),
    telegram_id: int | None = Query(None, gt=0),
    user_id: UUID | None = Depends(get_optional_current_mobile_user_id),
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> CustomerOnboardingConnectionBootstrapResponse:
    response.headers["Cache-Control"] = "no-store, private"
    resolved_user_id, resolved_realm = await _resolve_customer_onboarding_actor(
        db=db,
        authenticated_user_id=user_id,
        source_surface=surface,
        telegram_id=telegram_id,
        telegram_bot_secret=telegram_bot_secret,
        current_realm=current_realm,
    )
    mobile_user = await _get_mobile_user_or_404(db, resolved_user_id)
    runtime_config = await ConfigService(SystemConfigRepository(db)).get_customer_onboarding_runtime_config()
    entitlement_snapshot = await GetCurrentEntitlementStateUseCase(db).execute(
        customer_account_id=resolved_user_id,
        auth_realm_id=resolved_realm.auth_realm.id,
    )
    config_snapshot = await _resolve_connection_config(
        db=db,
        mobile_user=mobile_user,
        user_id=resolved_user_id,
        auth_realm_id=resolved_realm.auth_realm.id,
        remnawave_client=remnawave_client,
    )
    result = await CustomerOnboardingConnectionBootstrapUseCase(
        runtime_config=runtime_config,
        session_repo=CustomerConnectionSessionSqlAlchemyRepository(db),
    ).execute(
        user_id=resolved_user_id,
        surface=surface,
        platform_hint=platform_hint,
        subscription_url=config_snapshot.subscription_url,
        entitlement_status=_snapshot_str(entitlement_snapshot, "status"),
        service_identity_ready=config_snapshot.service_identity_ready,
        config_profile_name=config_snapshot.config_profile_name,
        device_limit=_nested_snapshot_int(entitlement_snapshot, "effective", "device_limit"),
        traffic_limit_bytes=_nested_snapshot_int(entitlement_snapshot, "effective", "traffic_limit_bytes"),
        entitlement_expires_at=_snapshot_datetime(entitlement_snapshot, "expires_at"),
    )
    await db.commit()
    observe_customer_onboarding_connection_bootstrap(status=result.status, surface=result.surface)
    return _connection_bootstrap_response(result)


@router.post("/connection/mark-connected", response_model=MarkOnboardingConnectionConnectedResponse)
async def mark_customer_onboarding_connection_connected(
    payload: MarkOnboardingConnectionConnectedRequest,
    user_id: UUID | None = Depends(get_optional_current_mobile_user_id),
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
    db: AsyncSession = Depends(get_db),
) -> MarkOnboardingConnectionConnectedResponse:
    resolved_user_id, _resolved_realm = await _resolve_customer_onboarding_actor(
        db=db,
        authenticated_user_id=user_id,
        source_surface=payload.source_surface,
        telegram_id=payload.telegram_id,
        telegram_bot_secret=telegram_bot_secret,
        current_realm=current_realm,
    )
    result = await CustomerOnboardingMarkConnectedUseCase(
        session_repo=CustomerConnectionSessionSqlAlchemyRepository(db),
    ).execute(
        user_id=resolved_user_id,
        surface=payload.source_surface,
        platform=payload.platform or "unknown",
        flow_key=payload.flow_key,
        version=payload.version,
        connection_session_id=_parse_connection_session_id(payload.connection_session_id),
    )
    await db.commit()
    return MarkOnboardingConnectionConnectedResponse(
        status=result.status,
        next_destination=result.next_destination,
        connected_at=result.connected_at.isoformat() if result.connected_at is not None else None,
        flow_key=result.flow_key,
        version=result.version,
    )


def _current_response(state: CustomerOnboardingCurrentState) -> CustomerOnboardingCurrentResponse:
    return CustomerOnboardingCurrentResponse(
        required=state.required,
        status=state.status,
        flow_key=state.flow_key,
        version=state.version,
        allowed_code_types=cast(list[Literal["promo", "invite", "gift"]], list(state.allowed_code_types)),
        flow_token=state.flow_token,
        message_key=state.message_key,
        server_state_available=state.server_state_available,
        referral_already_attributed=state.referral_already_attributed,
        connection_required=state.connection_required,
    )


def _apply_response(result: CustomerOnboardingApplyResult) -> CustomerOnboardingApplyResponse:
    safe_details = dict(result.safe_details or {})
    return CustomerOnboardingApplyResponse(
        status=cast(Literal["pending", "completed", "skipped"], result.status),
        message_key=result.message_key,
        masked_code=result.masked_code,
        next_destination=result.next_destination,
        connection_required=result.connection_required,
        code_type=result.code_type,
        entitlement=_entitlement_apply_summary(safe_details.get("entitlement_snapshot")),
        child_invites=_dict_or_none(safe_details.get("child_invites")),
    )


def _preview_response(result: CustomerOnboardingPreviewResult) -> CustomerOnboardingPreviewResponse:
    return CustomerOnboardingPreviewResponse(
        accepted=result.accepted,
        detected_code_type=result.detected_code_type,
        status=result.status,
        message_key=result.message_key,
        masked_code=result.masked_code,
        matched_code_types=list(result.matched_code_types),
        next_action=result.next_action,
        safe_details=dict(result.safe_details or {}),
    )


def _first_child_invite_plan_code(invites: tuple[object, ...]) -> str | None:
    if not invites:
        return None
    snapshot = dict(
        getattr(invites[0], "grant_snapshot", None) or getattr(invites[0], "entitlement_snapshot", {}) or {}
    )
    value = snapshot.get("plan_code")
    return value if isinstance(value, str) and value else None


def _first_child_invite_days(invites: tuple[object, ...]) -> int | None:
    if not invites:
        return None
    value = getattr(invites[0], "grant_duration_days", None) or getattr(invites[0], "free_days", None)
    return int(value) if value is not None else None


def _first_child_invite_duration_mode(invites: tuple[object, ...]) -> str | None:
    if not invites:
        return None
    value = getattr(invites[0], "grant_duration_mode", None)
    return str(value) if value else None


def _first_child_invite_device_override(invites: tuple[object, ...]) -> int | None:
    if not invites:
        return None
    value = getattr(invites[0], "grant_device_limit_override", None)
    return int(value) if value is not None else None


def _skip_response(result: CustomerOnboardingSkipResult) -> CustomerOnboardingSkipResponse:
    return CustomerOnboardingSkipResponse(
        status=cast(Literal["skipped", "completed"], result.status),
        message_key=result.message_key,
        next_destination=result.next_destination,
    )


def _connection_bootstrap_response(
    result: CustomerConnectionBootstrapResult,
) -> CustomerOnboardingConnectionBootstrapResponse:
    return CustomerOnboardingConnectionBootstrapResponse(
        available=result.available,
        status=result.status,
        message_key=result.message_key,
        subscription_url=result.subscription_url,
        qr_payload=result.qr_payload,
        config_profile_name=result.config_profile_name,
        expires_at=result.expires_at.isoformat() if result.expires_at is not None else None,
        device_limit=result.device_limit,
        traffic_limit_bytes=result.traffic_limit_bytes,
        instructions=[
            CustomerOnboardingConnectionInstruction(
                platform=item.platform,
                title_key=item.title_key,
                steps=[
                    CustomerOnboardingConnectionInstructionStep(
                        order=step.order,
                        title_key=step.title_key,
                        body_key=step.body_key,
                        action_url=step.action_url,
                        copy_value=step.copy_value,
                    )
                    for step in item.steps
                ],
                recommended_apps=[
                    CustomerOnboardingConnectionAppRecommendation(**app) for app in item.recommended_apps
                ],
            )
            for item in result.instructions
        ],
        surface=result.surface,
        preferred_layout=result.preferred_layout,
        supported_actions=list(result.supported_actions),
        connection_session_id=result.connection_session_id,
        telegram_payload=result.telegram_payload,
        flow_key=result.flow_key,
        version=result.version,
    )


def _parse_connection_session_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_CONNECTION_SESSION_ID",
                "message_key": "onboarding.connection.invalid_session",
            },
        ) from exc


def _trusted_apply_source_surface(
    *,
    requested_source_surface: ConnectionSurface,
    telegram_bot_secret: str | None,
) -> ConnectionSurface:
    del telegram_bot_secret
    if requested_source_surface == "telegram_bot":
        return "telegram_bot"
    return requested_source_surface


def _invite_redemption_runtime_context(request: Request) -> InviteRedemptionRuntimeContext:
    client_ip = resolve_client_ip(request).ip
    device_key = (
        request.cookies.get("__Host-cvpn_device_id")
        or request.headers.get("X-Device-ID")
        or request.headers.get("X-CyberVPN-Device-ID")
    )
    return InviteRedemptionRuntimeContext(
        client_ip_hash=_hash_runtime_key(client_ip) if client_ip else None,
        device_key_hash=hash_device_key(device_key.strip()) if device_key else None,
    )


def _hash_runtime_key(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


async def _resolve_customer_onboarding_actor(
    *,
    db: AsyncSession,
    authenticated_user_id: UUID | None,
    source_surface: ConnectionSurface,
    telegram_id: int | None,
    telegram_bot_secret: str | None,
    current_realm: RealmResolution,
) -> tuple[UUID, RealmResolution]:
    if source_surface == "telegram_bot":
        _require_telegram_bot_secret(telegram_bot_secret)
        if telegram_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "TELEGRAM_ID_REQUIRED",
                    "message": "telegram_id is required for telegram_bot onboarding requests.",
                },
            )
        mobile_user = await MobileUserRepository(db).get_by_telegram_id(telegram_id)
        if mobile_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "CUSTOMER_NOT_FOUND",
                    "message": "Telegram user is not linked to a customer account.",
                },
            )
        if not mobile_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "USER_INACTIVE", "message": "User account is inactive"},
            )
        return mobile_user.id, await _resolve_customer_realm_for_mobile_user(db, mobile_user)

    if authenticated_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid token"},
        )
    return authenticated_user_id, current_realm


async def _get_mobile_user_or_404(db: AsyncSession, user_id: UUID) -> MobileUserModel:
    mobile_user = await MobileUserRepository(db).get_by_id(user_id)
    if mobile_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CUSTOMER_NOT_FOUND", "message": "Customer account was not found."},
        )
    if not mobile_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_INACTIVE", "message": "User account is inactive"},
        )
    return mobile_user


def _is_valid_telegram_bot_secret(secret: str | None) -> bool:
    configured = settings.telegram_bot_internal_secret.get_secret_value().strip()
    if not configured or not secret:
        return False
    return hmac.compare_digest(secret.strip(), configured)


def _require_telegram_bot_secret(secret: str | None) -> None:
    if _is_valid_telegram_bot_secret(secret):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


async def _resolve_customer_realm_for_mobile_user(
    db: AsyncSession,
    mobile_user: MobileUserModel,
) -> RealmResolution:
    repo = AuthRealmRepository(db)
    default_realm_id = stable_auth_realm_id(str(DEFAULT_AUTH_REALMS["customer"]["realm_key"]))
    auth_realm_id = getattr(mobile_user, "auth_realm_id", None)
    realm = await repo.get_realm_by_id(auth_realm_id or default_realm_id)
    if realm is None:
        realm = await repo.get_or_create_default_realm("customer")
    return RealmResolution(auth_realm=realm, source="telegram_bot")


async def _resolve_connection_config(
    *,
    db: AsyncSession,
    mobile_user: MobileUserModel,
    user_id: UUID,
    auth_realm_id: UUID,
    remnawave_client: RemnawaveClient,
) -> _ConnectionConfigSnapshot:
    if mobile_user.remnawave_uuid:
        try:
            result = await GenerateConfigUseCase(remnawave_client).execute(mobile_user.remnawave_uuid)
        except HTTPException as exc:
            if exc.status_code not in {status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY}:
                raise
        else:
            return _connection_snapshot_from_result(
                result,
                fallback_subscription_url=mobile_user.subscription_url,
                config_profile_name="remnawave_subscription",
                service_identity_ready=True,
            )

    if mobile_user.telegram_id is not None:
        remnawave_user = await RemnawaveUserGateway(client=remnawave_client).get_by_telegram_id(mobile_user.telegram_id)
        if remnawave_user is not None:
            try:
                result = await GenerateConfigUseCase(remnawave_client).execute(remnawave_user.uuid)
            except HTTPException as exc:
                if exc.status_code not in {status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY}:
                    raise
            else:
                return _connection_snapshot_from_result(
                    result,
                    fallback_subscription_url=mobile_user.subscription_url,
                    config_profile_name="telegram_subscription",
                    service_identity_ready=True,
                )

    subscription_result = await ListCustomerSubscriptionsUseCase(db).execute(
        customer_account_id=user_id,
        auth_realm_id=auth_realm_id,
    )
    if subscription_result.default_subscription_key:
        try:
            result = await CustomerSubscriptionServiceAccessUseCase(db).get_config(
                customer_account_id=user_id,
                auth_realm_id=auth_realm_id,
                subscription_key=subscription_result.default_subscription_key,
                remnawave_client=remnawave_client,
            )
        except (LookupError, PermissionError):
            result = None
        if result is not None:
            return _connection_snapshot_from_result(
                result,
                fallback_subscription_url=mobile_user.subscription_url,
                config_profile_name="subscription_entitlement",
                service_identity_ready=True,
            )

    if mobile_user.subscription_url:
        subscription_url = normalize_public_subscription_url(mobile_user.subscription_url) or str(
            mobile_user.subscription_url
        )
        return _ConnectionConfigSnapshot(
            subscription_url=subscription_url,
            config_profile_name="legacy_subscription_url",
            service_identity_ready=True,
        )

    return _ConnectionConfigSnapshot(
        subscription_url=None,
        config_profile_name=None,
        service_identity_ready=bool(mobile_user.remnawave_uuid),
    )


def _connection_snapshot_from_result(
    result: dict[str, object],
    *,
    fallback_subscription_url: str | None,
    config_profile_name: str,
    service_identity_ready: bool,
) -> _ConnectionConfigSnapshot:
    subscription_url = _snapshot_str(result, "subscription_url")
    normalized = normalize_public_subscription_url(subscription_url) if subscription_url else None
    fallback = normalize_public_subscription_url(fallback_subscription_url) if fallback_subscription_url else None
    config = normalized or _snapshot_str(result, "config_string") or fallback
    return _ConnectionConfigSnapshot(
        subscription_url=config,
        config_profile_name=config_profile_name,
        service_identity_ready=service_identity_ready,
    )


def _snapshot_str(snapshot: dict[str, object], key: str) -> str | None:
    value = snapshot.get(key)
    return value if isinstance(value, str) and value else None


def _dict_or_none(value: object) -> dict[str, object] | None:
    return dict(value) if isinstance(value, dict) else None


def _entitlement_apply_summary(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    effective = value.get("effective_entitlements")
    effective_entitlements = dict(effective) if isinstance(effective, dict) else {}
    return {
        "plan_uuid": value.get("plan_uuid"),
        "plan_code": value.get("plan_code"),
        "display_name": value.get("display_name"),
        "period_days": value.get("period_days"),
        "expires_at": value.get("expires_at"),
        "device_limit": effective_entitlements.get("device_limit"),
        "traffic_policy": effective_entitlements.get("traffic_policy"),
        "display_traffic_label": effective_entitlements.get("display_traffic_label"),
        "connection_modes": effective_entitlements.get("connection_modes") or [],
        "server_pool": effective_entitlements.get("server_pool") or [],
        "is_trial": bool(value.get("is_trial", False)),
    }


def _nested_snapshot_int(snapshot: dict[str, object], section: str, key: str) -> int | None:
    nested = snapshot.get(section)
    if not isinstance(nested, dict):
        return None
    value = nested.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _snapshot_datetime(snapshot: dict[str, object], key: str) -> datetime | None:
    value = snapshot.get(key)
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _onboarding_http_error(exc: CustomerOnboardingUnavailableError) -> HTTPException:
    logger.info("customer_onboarding_unavailable", extra={"code": exc.code})
    return HTTPException(
        status_code=exc.status_code,
        detail={
            "code": exc.code,
            "message_key": exc.message_key,
        },
    )


class CustomerOnboardingGrowthCodeApplier(CustomerOnboardingCodeApplier):
    def __init__(
        self,
        session: AsyncSession,
        *,
        current_realm: RealmResolution,
        source_surface: str,
        runtime_context: InviteRedemptionRuntimeContext | None,
    ) -> None:
        self._session = session
        self._current_realm = current_realm
        self._source_surface = source_surface
        self._runtime_context = runtime_context
        self._resolver = ResolveGrowthCodeUseCase(session)
        self._invite_redeemer = RedeemInviteUseCase(session)
        self._gift_redeemer = RedeemGiftCodeUseCase(session)

    async def apply_code(
        self,
        *,
        code: str,
        user_id: UUID,
        idempotency_key: str,
        normalized_code_hash: str,
        masked_code: str,
    ) -> CustomerOnboardingAppliedCode:
        del idempotency_key, normalized_code_hash
        outcome = await self._resolver.execute(
            code=code,
            action_context=GrowthCodeActionContext.REDEEM,
            user_id=user_id,
            surface=_CUSTOMER_ONBOARDING_SURFACE,
        )
        if _is_checkout_staged_promo(outcome):
            return CustomerOnboardingAppliedCode(
                result="staged",
                code_type="promo",
                message_key=outcome.user_message_key,
                masked_code=masked_code,
                next_destination="/subscriptions",
                resolved_code_id=outcome.resolved_code_id,
                growth_code_id=outcome.growth_code_id,
                safe_details={"wrong_context_target": GrowthCodeWrongContextTarget.CHECKOUT.value},
            )
        if not outcome.accepted or outcome.code_type is None:
            raise _onboarding_code_rejected(outcome)

        if outcome.code_type == GrowthCodeType.INVITE:
            try:
                redeemed = await self._invite_redeemer.execute(
                    code=code,
                    user_id=user_id,
                    current_realm=self._current_realm,
                    source_surface=self._source_surface,
                    runtime_context=self._runtime_context,
                )
            except InviteCodeNotFoundError as exc:
                raise CustomerOnboardingUnavailableError(
                    code="CUSTOMER_ONBOARDING_CODE_NOT_FOUND",
                    message_key="growth_codes.code.not_found",
                    status_code=404,
                ) from exc
            except InviteCodeAlreadyUsedError as exc:
                raise CustomerOnboardingUnavailableError(
                    code="CUSTOMER_ONBOARDING_CODE_ALREADY_REDEEMED",
                    message_key="growth_codes.invite.already_redeemed",
                    status_code=409,
                ) from exc
            except InviteCodeExpiredError as exc:
                raise CustomerOnboardingUnavailableError(
                    code="CUSTOMER_ONBOARDING_CODE_EXPIRED",
                    message_key="growth_codes.invite.expired",
                    status_code=410,
                ) from exc
            except ValueError as exc:
                raise CustomerOnboardingUnavailableError(
                    code="CUSTOMER_ONBOARDING_CODE_NOT_ELIGIBLE",
                    message_key="growth_codes.invite.not_eligible",
                    status_code=422,
                ) from exc
            return CustomerOnboardingAppliedCode(
                result="accepted",
                code_type="invite",
                message_key=outcome.user_message_key,
                masked_code=masked_code,
                resolved_code_id=outcome.resolved_code_id,
                growth_code_id=outcome.growth_code_id,
                redemption_id=redeemed.redemption.id,
                entitlement_grant_id=redeemed.entitlement_grant_id,
                entitlement_snapshot=redeemed.entitlement_snapshot,
                child_invites={
                    "generated_count": len(redeemed.child_invites),
                    "issued_count": len(redeemed.child_invites),
                    "count": len(redeemed.child_invites),
                    "batch_id": str(redeemed.child_batch.id) if redeemed.child_batch is not None else None,
                    "available_count": sum(1 for invite in redeemed.child_invites if not invite.is_used),
                    "friend_plan_code": _first_child_invite_plan_code(redeemed.child_invites),
                    "friend_days": (
                        int(redeemed.child_batch.friend_days)
                        if redeemed.child_batch is not None
                        else _first_child_invite_days(redeemed.child_invites)
                    ),
                    "grant_plan_code": _first_child_invite_plan_code(redeemed.child_invites),
                    "grant_duration_mode": _first_child_invite_duration_mode(redeemed.child_invites),
                    "grant_duration_days": _first_child_invite_days(redeemed.child_invites),
                    "lifetime": _first_child_invite_duration_mode(redeemed.child_invites) == "lifetime",
                    "device_limit_override": _first_child_invite_device_override(redeemed.child_invites),
                    "expiry_mode": redeemed.child_batch.expiry_mode if redeemed.child_batch is not None else None,
                    "expires_at": redeemed.child_batch.expires_at.isoformat()
                    if redeemed.child_batch is not None and redeemed.child_batch.expires_at
                    else None,
                    "generation_depth": (
                        int(redeemed.child_invites[0].generation_depth) if redeemed.child_invites else None
                    ),
                },
                next_destination="/onboarding/connect",
            )

        if outcome.code_type == GrowthCodeType.GIFT:
            try:
                redeemed_gift = await self._gift_redeemer.execute(
                    code=code,
                    user_id=user_id,
                    current_realm=self._current_realm,
                )
            except ValueError as exc:
                raise _gift_redemption_error(str(exc)) from exc
            return CustomerOnboardingAppliedCode(
                result="accepted",
                code_type="gift",
                message_key=outcome.user_message_key,
                masked_code=masked_code,
                resolved_code_id=outcome.resolved_code_id,
                growth_code_id=outcome.growth_code_id,
                redemption_id=redeemed_gift.redemption.id,
                entitlement_grant_id=redeemed_gift.entitlement_grant_id,
                entitlement_snapshot=redeemed_gift.entitlement_snapshot,
                next_destination="/onboarding/connect",
            )

        raise _onboarding_code_rejected(outcome)


class CustomerOnboardingGrowthCodePreviewer(CustomerOnboardingCodePreviewer):
    def __init__(self, session: AsyncSession) -> None:
        self._resolver = ResolveGrowthCodeUseCase(session)

    async def preview_code(
        self,
        *,
        code: str,
        user_id: UUID,
        normalized_code_hash: str,
        masked_code: str,
    ) -> CustomerOnboardingPreviewResult:
        del normalized_code_hash
        outcome = await self._resolver.execute(
            code=code,
            action_context=GrowthCodeActionContext.REDEEM,
            user_id=user_id,
            surface=_CUSTOMER_ONBOARDING_SURFACE,
            record_event=False,
            ensure_registry=False,
        )
        return _preview_from_resolution(outcome=outcome, masked_code=masked_code)


def _is_checkout_staged_promo(outcome: GrowthCodeResolutionOutcome) -> bool:
    return (
        outcome.code_type == GrowthCodeType.PROMO
        and outcome.result == GrowthCodeResolutionStatus.REJECTED
        and outcome.reject_reason == GrowthCodeRejectReason.CODE_WRONG_CONTEXT
        and outcome.wrong_context_target == GrowthCodeWrongContextTarget.CHECKOUT
    )


def _preview_from_resolution(
    *,
    outcome: GrowthCodeResolutionOutcome,
    masked_code: str,
) -> CustomerOnboardingPreviewResult:
    checkout_stage = _is_checkout_staged_code(outcome)
    status = _preview_status(outcome)
    matched_code_types = _matched_code_types(outcome)
    return CustomerOnboardingPreviewResult(
        accepted=outcome.accepted or checkout_stage,
        detected_code_type=_detected_code_type(outcome),
        status=status,
        message_key=outcome.user_message_key,
        masked_code=masked_code,
        matched_code_types=matched_code_types,
        next_action=_preview_next_action(outcome=outcome, status=status, checkout_stage=checkout_stage),
        safe_details=_preview_safe_details(outcome),
    )


def _is_checkout_staged_code(outcome: GrowthCodeResolutionOutcome) -> bool:
    return (
        outcome.reject_reason == GrowthCodeRejectReason.CODE_WRONG_CONTEXT
        and outcome.wrong_context_target == GrowthCodeWrongContextTarget.CHECKOUT
        and outcome.code_type in {GrowthCodeType.PROMO, GrowthCodeType.REFERRAL, GrowthCodeType.PARTNER}
    )


def _preview_status(
    outcome: GrowthCodeResolutionOutcome,
) -> Literal[
    "preview_available",
    "not_found",
    "ambiguous",
    "wrong_context",
    "not_eligible",
    "expired",
    "already_used",
    "blocked",
]:
    if outcome.result == GrowthCodeResolutionStatus.CONFLICTED and (
        outcome.reject_reason == GrowthCodeRejectReason.CODE_NAMESPACE_AMBIGUOUS
        or outcome.conflict_code == "CODE_NAMESPACE_AMBIGUOUS"
    ):
        return "ambiguous"
    if outcome.accepted:
        return "preview_available"
    if outcome.reject_reason == GrowthCodeRejectReason.CODE_NOT_FOUND:
        return "not_found"
    if outcome.reject_reason == GrowthCodeRejectReason.CODE_WRONG_CONTEXT:
        return "wrong_context"
    if outcome.reject_reason == GrowthCodeRejectReason.CODE_EXPIRED:
        return "expired"
    if outcome.reject_reason in {
        GrowthCodeRejectReason.CODE_ALREADY_REDEEMED,
        GrowthCodeRejectReason.GIFT_ALREADY_REDEEMED,
    }:
        return "already_used"
    if outcome.reject_reason == GrowthCodeRejectReason.CODE_BLOCKED_BY_RISK:
        return "blocked"
    return "not_eligible"


def _preview_next_action(
    *,
    outcome: GrowthCodeResolutionOutcome,
    status: str,
    checkout_stage: bool,
) -> Literal[
    "apply_now",
    "stage_for_checkout",
    "redeem_entitlement",
    "resolve_ambiguity",
    "none",
]:
    if status == "ambiguous":
        return "resolve_ambiguity"
    if checkout_stage:
        return "stage_for_checkout"
    if outcome.accepted and outcome.code_type in {GrowthCodeType.INVITE, GrowthCodeType.GIFT}:
        return "redeem_entitlement"
    if outcome.accepted:
        return "apply_now"
    return "none"


def _detected_code_type(outcome: GrowthCodeResolutionOutcome):
    if outcome.code_type is None:
        return None
    value = outcome.code_type.value
    if value in {"promo", "invite", "gift", "referral", "partner"}:
        return cast(Literal["promo", "invite", "gift", "referral", "partner"], value)
    return None


def _matched_code_types(outcome: GrowthCodeResolutionOutcome) -> tuple[str, ...]:
    policy_snapshot = outcome.policy_snapshot if isinstance(outcome.policy_snapshot, dict) else {}
    raw_matched = policy_snapshot.get("matched_code_types")
    if isinstance(raw_matched, list):
        return tuple(
            str(item) for item in raw_matched if str(item) in {"promo", "invite", "gift", "referral", "partner"}
        )
    detected = _detected_code_type(outcome)
    return (detected,) if detected is not None else ()


def _preview_safe_details(outcome: GrowthCodeResolutionOutcome) -> dict[str, object]:
    details: dict[str, object] = {}
    if outcome.reject_reason is not None:
        details["reject_reason"] = outcome.reject_reason.value
    if outcome.conflict_code is not None:
        details["conflict_code"] = outcome.conflict_code
    if outcome.wrong_context_target is not None:
        details["wrong_context_target"] = outcome.wrong_context_target.value
    return details


def _onboarding_code_rejected(outcome: GrowthCodeResolutionOutcome) -> CustomerOnboardingUnavailableError:
    reject_reason = outcome.reject_reason
    status_code = 422
    error_code = "CUSTOMER_ONBOARDING_CODE_REJECTED"
    if reject_reason == GrowthCodeRejectReason.CODE_NOT_FOUND:
        status_code = 404
        error_code = "CUSTOMER_ONBOARDING_CODE_NOT_FOUND"
    elif reject_reason == GrowthCodeRejectReason.CODE_EXPIRED:
        status_code = 410
        error_code = "CUSTOMER_ONBOARDING_CODE_EXPIRED"
    elif reject_reason in {
        GrowthCodeRejectReason.CODE_ALREADY_REDEEMED,
        GrowthCodeRejectReason.GIFT_ALREADY_REDEEMED,
        GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PARTNER_BINDING,
        GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PARTNER_CODE,
        GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PROMO,
        GrowthCodeRejectReason.CODE_NAMESPACE_AMBIGUOUS,
    }:
        status_code = 409
        error_code = "CUSTOMER_ONBOARDING_CODE_CONFLICT"
    elif reject_reason == GrowthCodeRejectReason.CODE_BLOCKED_BY_RISK:
        status_code = 403
        error_code = "CUSTOMER_ONBOARDING_CODE_BLOCKED"
    return CustomerOnboardingUnavailableError(
        code=error_code,
        message_key=outcome.user_message_key,
        status_code=status_code,
    )


def _gift_redemption_error(detail: str) -> CustomerOnboardingUnavailableError:
    normalized = detail.lower()
    if "not found" in normalized:
        return CustomerOnboardingUnavailableError(
            code="CUSTOMER_ONBOARDING_CODE_NOT_FOUND",
            message_key="growth_codes.code.not_found",
            status_code=404,
        )
    if "already redeemed" in normalized:
        return CustomerOnboardingUnavailableError(
            code="CUSTOMER_ONBOARDING_CODE_ALREADY_REDEEMED",
            message_key="growth_codes.gift.already_redeemed",
            status_code=409,
        )
    if "expired" in normalized:
        return CustomerOnboardingUnavailableError(
            code="CUSTOMER_ONBOARDING_CODE_EXPIRED",
            message_key="growth_codes.gift.expired",
            status_code=410,
        )
    return CustomerOnboardingUnavailableError(
        code="CUSTOMER_ONBOARDING_CODE_NOT_ELIGIBLE",
        message_key="growth_codes.gift.not_eligible",
        status_code=422,
    )
