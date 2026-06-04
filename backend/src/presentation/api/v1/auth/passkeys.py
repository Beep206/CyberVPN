"""Passkey/WebAuthn routes."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import redis.asyncio as redis
import sentry_sdk
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.config_service import PASSKEY_ADMIN_POLICY_CONFIG_KEY, ConfigService
from src.application.services.passkey_webauthn import (
    PasskeyVerificationError,
    PasskeyWebAuthnService,
    credential_hash_from_browser_payload,
    credential_user_handle_from_browser_payload,
    passkey_identifier_hash,
    passkey_user_handle,
    passkey_user_handle_bytes,
)
from src.config.settings import settings
from src.infrastructure.cache.passkey_challenges import PasskeyChallengeError, PasskeyChallengeStore
from src.infrastructure.cache.passkey_fresh_auth import PasskeyFreshAuthGrantStore
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.passkey_credential_model import PasskeyCredentialModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.passkey_credential_repo import PasskeyCredentialRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.monitoring.instrumentation.routes import sync_active_sessions
from src.infrastructure.monitoring.metrics import route_operations_total
from src.presentation.api.v1.auth.cookies import set_auth_cookies
from src.presentation.api.v1.auth.passkey_schemas import (
    PasskeyAuthenticationOptionsRequest,
    PasskeyAuthenticationVerifyRequest,
    PasskeyCredentialListResponse,
    PasskeyCredentialResponse,
    PasskeyDeleteResponse,
    PasskeyOptionsResponse,
    PasskeyPolicyResponse,
    PasskeyReauthenticationOptionsRequest,
    PasskeyReauthenticationVerifyRequest,
    PasskeyReauthenticationVerifyResponse,
    PasskeyRegistrationOptionsRequest,
    PasskeyRegistrationVerifyRequest,
    PasskeyRenameRequest,
)
from src.presentation.api.v1.auth.realm_context import get_principal_type_for_realm
from src.presentation.api.v1.auth.schemas import LoginResponse
from src.presentation.api.v1.auth.session_tokens import store_refresh_token
from src.presentation.dependencies.auth import get_current_active_web_user
from src.presentation.dependencies.auth_realms import get_request_web_auth_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.passkey_fresh_auth import enforce_passkey_fresh_auth
from src.presentation.dependencies.services import get_auth_service
from src.shared.security.fingerprint import generate_client_fingerprint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/passkeys", tags=["auth", "passkeys"])

_GENERIC_AUTH_ERROR = "Invalid passkey ceremony"


@dataclass(frozen=True)
class _PasskeyPolicyContext:
    origin: str
    rp_id: str
    allowed_origins: list[str]
    enabled: bool
    configured_enabled: bool
    global_enabled: bool
    surface_enabled: bool
    conditional_ui_enabled: bool
    registration_enabled: bool
    authentication_enabled: bool
    reauthentication_enabled: bool
    security_dashboard_enabled: bool | None
    workspace_policy_enabled: bool | None
    admin_counts_as_mfa: bool
    challenge_ttl_seconds: int
    browser_timeout_ms: int
    fresh_auth_ttl_seconds: int
    policy_source: str
    updated_at: datetime | None
    updated_by: UUID | None


def _request_origin(request: Request) -> str:
    raw_origin = request.headers.get("Origin")
    if raw_origin:
        return raw_origin.strip().rstrip("/")

    raw_referer = request.headers.get("Referer")
    if raw_referer:
        from urllib.parse import urlparse

        parsed = urlparse(raw_referer)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Passkey origin is required")


def _passkey_surface_feature_enabled(realm_type: str) -> bool:
    if realm_type == "customer":
        return settings.passkey_customer_enabled
    if realm_type == "admin":
        return settings.passkey_admin_enabled
    if realm_type == "partner":
        return settings.passkey_partner_enabled
    return False


async def _passkey_context(
    request: Request,
    realm_type: str,
    db: AsyncSession,
) -> _PasskeyPolicyContext:
    global_enabled = settings.passkey_enabled
    surface_enabled = _passkey_surface_feature_enabled(realm_type)
    origin = _request_origin(request)
    if settings.passkey_dev_enabled and origin in settings.passkey_dev_allowed_origins:
        rp_id = settings.passkey_dev_rp_id
        allowed_origins = settings.passkey_dev_allowed_origins
    else:
        rp_id = settings.passkey_rp_id
        allowed_origins = settings.passkey_allowed_origins

    if origin not in allowed_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Passkey origin is not allowed")

    configured_enabled = True
    registration_enabled = True
    authentication_enabled = True
    reauthentication_enabled = True
    conditional_ui_enabled = True
    security_dashboard_enabled = settings.passkey_admin_security_dashboard_enabled if realm_type == "admin" else None
    workspace_policy_enabled = settings.passkey_partner_workspace_policy_enabled if realm_type == "partner" else None
    admin_counts_as_mfa = settings.passkey_admin_counts_as_mfa
    challenge_ttl_seconds = settings.passkey_challenge_ttl_seconds
    browser_timeout_ms = settings.passkey_browser_timeout_ms
    fresh_auth_ttl_seconds = settings.passkey_fresh_auth_ttl_seconds
    policy_source = "settings"
    updated_at: datetime | None = None
    updated_by: UUID | None = None

    if realm_type == "admin":
        config_repo = SystemConfigRepository(db)
        config_model = await config_repo.get_by_key(PASSKEY_ADMIN_POLICY_CONFIG_KEY)
        admin_policy = await ConfigService(config_repo).get_passkey_admin_policy_config()
        configured_enabled = admin_policy.enabled
        registration_enabled = admin_policy.registration_enabled
        authentication_enabled = admin_policy.authentication_enabled
        reauthentication_enabled = admin_policy.reauthentication_enabled
        conditional_ui_enabled = admin_policy.conditional_ui_enabled
        security_dashboard_enabled = admin_policy.security_dashboard_enabled
        admin_counts_as_mfa = admin_policy.admin_counts_as_mfa
        challenge_ttl_seconds = admin_policy.challenge_ttl_seconds
        browser_timeout_ms = admin_policy.browser_timeout_ms
        fresh_auth_ttl_seconds = admin_policy.fresh_auth_ttl_seconds
        if config_model is not None:
            policy_source = "system_config"
            updated_at = config_model.updated_at
            updated_by = config_model.updated_by

    enabled = global_enabled and surface_enabled and configured_enabled
    return _PasskeyPolicyContext(
        origin=origin,
        rp_id=rp_id,
        allowed_origins=allowed_origins,
        enabled=enabled,
        configured_enabled=configured_enabled,
        global_enabled=global_enabled,
        surface_enabled=surface_enabled,
        conditional_ui_enabled=settings.passkey_conditional_ui_enabled and enabled and conditional_ui_enabled,
        registration_enabled=enabled and registration_enabled,
        authentication_enabled=enabled and authentication_enabled,
        reauthentication_enabled=enabled and reauthentication_enabled,
        security_dashboard_enabled=(
            settings.passkey_admin_security_dashboard_enabled and enabled and bool(security_dashboard_enabled)
            if realm_type == "admin"
            else None
        ),
        workspace_policy_enabled=workspace_policy_enabled,
        admin_counts_as_mfa=admin_counts_as_mfa,
        challenge_ttl_seconds=challenge_ttl_seconds,
        browser_timeout_ms=browser_timeout_ms,
        fresh_auth_ttl_seconds=fresh_auth_ttl_seconds,
        policy_source=policy_source,
        updated_at=updated_at,
        updated_by=updated_by,
    )


def _require_passkeys_enabled(enabled: bool) -> None:
    if not enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passkeys are disabled")


def _credential_response(credential: PasskeyCredentialModel) -> PasskeyCredentialResponse:
    return PasskeyCredentialResponse(
        id=credential.id,
        label=credential.label,
        status=credential.status,
        credential_type=credential.credential_type,
        device_type=credential.device_type,
        transports=list(credential.transports or []),
        backed_up=credential.backed_up,
        user_verified=credential.user_verified,
        created_at=credential.created_at,
        last_used_at=credential.last_used_at,
        revoked_at=credential.revoked_at,
    )


def _default_label(label: str | None) -> str:
    normalized = (label or "").strip()
    if normalized:
        return normalized[:120]
    return f"Passkey added {datetime.now(UTC).date().isoformat()}"


def _generic_unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_GENERIC_AUTH_ERROR)


def _enforce_credential_user_handle(payload: dict, credential: PasskeyCredentialModel) -> None:
    try:
        payload_user_handle = credential_user_handle_from_browser_payload(payload)
    except PasskeyVerificationError as exc:
        raise _generic_unauthorized() from exc
    if payload_user_handle is not None and credential.user_handle and payload_user_handle != credential.user_handle:
        _track("credential_user_handle", "mismatch")
        raise _generic_unauthorized()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _track(action: str, metric_status: str) -> None:
    route_operations_total.labels(route="auth.passkeys", action=action, status=metric_status).inc()
    sentry_sdk.add_breadcrumb(
        category="auth.passkeys",
        message=action,
        data={"status": metric_status},
        level="info",
    )


async def _enforce_rate_limit(
    redis_client: redis.Redis,
    *,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    current = await redis_client.get(key)
    if current is not None:
        if isinstance(current, bytes):
            current = current.decode("utf-8")
        if int(current) >= limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Passkey rate limit exceeded")

    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, window_seconds)


async def _audit_passkey_event(
    db: AsyncSession,
    *,
    action: str,
    actor_id: UUID | None,
    credential: PasskeyCredentialModel | None = None,
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    db.add(
        AuditLog(
            admin_id=actor_id,
            action=action,
            entity_type="passkey_credential",
            entity_id=str(credential.id) if credential else None,
            new_value=metadata or {},
            ip_address=_client_ip(request) if request else None,
            user_agent=request.headers.get("User-Agent") if request else None,
        )
    )
    await db.flush()


async def _issue_session_for_passkey(
    *,
    request: Request,
    response: Response,
    db: AsyncSession,
    auth_service: AuthService,
    user: AdminUserModel,
    credential: PasskeyCredentialModel,
    cookie_namespace: str,
) -> LoginResponse:
    if user.totp_enabled:
        tfa_token, _, _ = auth_service.create_access_token(
            subject=str(user.id),
            role="2fa_pending",
            extra={"type": "2fa_pending", "auth_method": "passkey"},
            audience=credential.audience,
            principal_type=credential.principal_class,
            realm_id=str(credential.auth_realm_id),
            realm_key=credential.realm_key,
            scope_family=get_scope_family_for_realm_key(credential.realm_key),
        )
        return LoginResponse(
            access_token="",
            refresh_token="",
            expires_in=0,
            auth_realm_id=credential.auth_realm_id,
            auth_realm_key=credential.realm_key,
            audience=credential.audience,
            principal_type=credential.principal_class,
            scope_family=get_scope_family_for_realm_key(credential.realm_key),
            requires_2fa=True,
            tfa_token=tfa_token,
        )

    fingerprint = generate_client_fingerprint(request)
    scope_family = get_scope_family_for_realm_key(credential.realm_key)
    access_token, access_jti, _access_expire = auth_service.create_access_token(
        subject=str(user.id),
        role=user.role,
        audience=credential.audience,
        principal_type=credential.principal_class,
        realm_id=str(credential.auth_realm_id),
        realm_key=credential.realm_key,
        scope_family=scope_family,
        extra={"auth_method": "passkey"},
    )
    refresh_token, _refresh_jti, refresh_expire = auth_service.create_refresh_token(
        subject=str(user.id),
        fingerprint=fingerprint,
        audience=credential.audience,
        principal_type=credential.principal_class,
        realm_id=str(credential.auth_realm_id),
        realm_key=credential.realm_key,
        scope_family=scope_family,
    )
    await store_refresh_token(
        db,
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=refresh_expire,
        device_id=fingerprint,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        auth_realm_id=credential.auth_realm_id,
        principal_class=credential.principal_class,
        principal_subject=str(user.id),
        audience=credential.audience,
        scope_family=scope_family,
        access_token_jti=access_jti,
    )
    set_auth_cookies(response, access_token, refresh_token, cookie_namespace=cookie_namespace)
    await sync_active_sessions(db)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        auth_realm_id=credential.auth_realm_id,
        auth_realm_key=credential.realm_key,
        audience=credential.audience,
        principal_type=credential.principal_class,
        scope_family=scope_family,
        requires_2fa=False,
        tfa_token=None,
    )


def get_scope_family_for_realm_key(realm_key: str) -> str:
    if realm_key == "partner":
        return "partner"
    if realm_key == "customer":
        return "customer"
    return "admin"


@router.get("/policy", response_model=PasskeyPolicyResponse)
async def get_passkey_policy(
    request: Request,
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
) -> PasskeyPolicyResponse:
    context = await _passkey_context(request, current_realm.realm_type, db)
    return PasskeyPolicyResponse(
        enabled=context.enabled,
        configured_enabled=context.configured_enabled,
        global_enabled=context.global_enabled,
        surface_enabled=context.surface_enabled,
        surface=current_realm.realm_type,
        realm_key=current_realm.realm_key,
        rp_id=context.rp_id,
        rp_name=settings.passkey_rp_name,
        allowed_origins=context.allowed_origins,
        conditional_ui_enabled=context.conditional_ui_enabled,
        registration_enabled=context.registration_enabled,
        authentication_enabled=context.authentication_enabled,
        reauthentication_enabled=context.reauthentication_enabled,
        security_dashboard_enabled=context.security_dashboard_enabled,
        workspace_policy_enabled=context.workspace_policy_enabled,
        admin_counts_as_mfa=context.admin_counts_as_mfa,
        challenge_ttl_seconds=context.challenge_ttl_seconds,
        browser_timeout_ms=context.browser_timeout_ms,
        fresh_auth_ttl_seconds=context.fresh_auth_ttl_seconds,
        policy_source=context.policy_source,
        updated_at=context.updated_at,
        updated_by=context.updated_by,
    )


@router.post("/registration/options", response_model=PasskeyOptionsResponse)
async def create_passkey_registration_options(
    payload: PasskeyRegistrationOptionsRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> PasskeyOptionsResponse:
    context = await _passkey_context(request, current_realm.realm_type, db)
    _require_passkeys_enabled(context.registration_enabled)
    await _enforce_rate_limit(
        redis_client,
        key=f"passkey:rl:registration_options:{current_realm.realm_key}:{current_user.id}:{_client_ip(request)}",
        limit=10,
        window_seconds=3600,
    )

    principal_class = get_principal_type_for_realm(current_realm)
    principal_subject = str(current_user.id)
    repo = PasskeyCredentialRepository(db)
    existing_credentials = await repo.list_active_for_principal(
        auth_realm_id=current_realm.auth_realm.id,
        principal_class=principal_class,
        principal_subject=principal_subject,
    )
    user_handle_bytes = passkey_user_handle_bytes(
        auth_realm_id=current_realm.auth_realm.id,
        principal_class=principal_class,
        principal_subject=principal_subject,
    )
    options, challenge = PasskeyWebAuthnService().registration_options(
        rp_id=context.rp_id,
        rp_name=settings.passkey_rp_name,
        user_name=current_user.email or current_user.login,
        user_display_name=current_user.display_name or current_user.login,
        user_handle=user_handle_bytes,
        exclude_credentials=existing_credentials,
        timeout_ms=context.browser_timeout_ms,
    )
    challenge_record = await PasskeyChallengeStore(redis_client).create(
        challenge=challenge,
        ceremony="registration",
        rp_id=context.rp_id,
        expected_origin=context.origin,
        auth_realm_id=str(current_realm.auth_realm.id),
        realm_key=current_realm.realm_key,
        audience=current_realm.audience,
        principal_class=principal_class,
        principal_subject=principal_subject,
        user_handle=passkey_user_handle(
            auth_realm_id=current_realm.auth_realm.id,
            principal_class=principal_class,
            principal_subject=principal_subject,
        ),
        identifier_hash=passkey_identifier_hash(current_user.email or current_user.login),
        require_user_verification=True,
        ttl_seconds=context.challenge_ttl_seconds,
    )
    _track("registration_options", "success")
    return PasskeyOptionsResponse(
        challenge_id=challenge_record.challenge_id,
        public_key=options,
        expires_at=datetime.fromisoformat(challenge_record.expires_at),
    )


@router.post(
    "/registration/verify",
    response_model=PasskeyCredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def verify_passkey_registration(
    payload: PasskeyRegistrationVerifyRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> PasskeyCredentialResponse:
    context = await _passkey_context(request, current_realm.realm_type, db)
    _require_passkeys_enabled(context.registration_enabled)
    await _enforce_rate_limit(
        redis_client,
        key=f"passkey:rl:registration_verify:{current_realm.realm_key}:{current_user.id}:{_client_ip(request)}",
        limit=10,
        window_seconds=3600,
    )
    try:
        challenge = await PasskeyChallengeStore(redis_client).consume(
            payload.challenge_id,
            expected_ceremony="registration",
        )
    except PasskeyChallengeError as exc:
        logger.warning("Passkey registration challenge rejected", extra={"reason": str(exc)})
        _track("registration_verify", "challenge_failed")
        raise _generic_unauthorized() from exc

    principal_class = get_principal_type_for_realm(current_realm)
    principal_subject = str(current_user.id)
    if (
        challenge.auth_realm_id != str(current_realm.auth_realm.id)
        or challenge.realm_key != current_realm.realm_key
        or challenge.principal_class != principal_class
        or challenge.principal_subject != principal_subject
    ):
        raise _generic_unauthorized()

    service = PasskeyWebAuthnService()
    try:
        verified = service.verify_registration(payload=payload.credential, challenge=challenge)
    except PasskeyVerificationError as exc:
        _track("registration_verify", "verification_failed")
        raise _generic_unauthorized() from exc

    repo = PasskeyCredentialRepository(db)
    existing = await repo.get_active_by_hash(verified.credential_id_hash)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Passkey already registered")

    credential = await repo.add(
        PasskeyCredentialModel(
            credential_id=verified.credential_id_b64,
            credential_id_hash=verified.credential_id_hash,
            credential_public_key=verified.credential_public_key,
            sign_count=verified.sign_count,
            auth_realm_id=current_realm.auth_realm.id,
            realm_key=current_realm.realm_key,
            audience=current_realm.audience,
            principal_class=principal_class,
            principal_subject=principal_subject,
            user_handle=challenge.user_handle or "",
            label=_default_label(payload.label),
            surface=current_realm.realm_type,
            rp_id=challenge.rp_id,
            origin=challenge.expected_origin,
            aaguid=verified.aaguid,
            attestation_format=verified.attestation_format,
            credential_type=verified.credential_type,
            device_type=verified.device_type,
            transports=verified.transports,
            backed_up=verified.backed_up,
            user_verified=verified.user_verified,
            authenticator_attachment=verified.authenticator_attachment,
            policy_snapshot={
                "user_verification": "required",
                "admin_counts_as_mfa": context.admin_counts_as_mfa,
            },
        )
    )
    await _audit_passkey_event(
        db,
        action="passkey.registered",
        actor_id=current_user.id,
        credential=credential,
        request=request,
        metadata={
            "credential_id_hash": credential.credential_id_hash,
            "realm_key": credential.realm_key,
            "principal_class": credential.principal_class,
        },
    )
    _track("registration_verify", "success")
    return _credential_response(credential)


@router.post("/authentication/options", response_model=PasskeyOptionsResponse)
async def create_passkey_authentication_options(
    payload: PasskeyAuthenticationOptionsRequest,
    request: Request,
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> PasskeyOptionsResponse:
    context = await _passkey_context(request, current_realm.realm_type, db)
    _require_passkeys_enabled(context.authentication_enabled)
    identifier_hash = passkey_identifier_hash(payload.identifier)
    await _enforce_rate_limit(
        redis_client,
        key=(
            "passkey:rl:authentication_options:"
            f"{current_realm.realm_key}:{identifier_hash or 'discoverable'}:{_client_ip(request)}"
        ),
        limit=20,
        window_seconds=60,
    )

    principal_class: str | None = None
    principal_subject: str | None = None
    allow_credentials: list[PasskeyCredentialModel] = []
    if payload.identifier:
        user = await AdminUserRepository(db).get_by_login_or_email(
            payload.identifier,
            realm_id=current_realm.auth_realm.id,
            include_legacy_default=current_realm.realm_key == "admin",
        )
        if user and user.is_active:
            principal_class = get_principal_type_for_realm(current_realm)
            principal_subject = str(user.id)
            allow_credentials = await PasskeyCredentialRepository(db).list_active_for_principal(
                auth_realm_id=current_realm.auth_realm.id,
                principal_class=principal_class,
                principal_subject=principal_subject,
            )

    options, challenge = PasskeyWebAuthnService().authentication_options(
        rp_id=context.rp_id,
        allow_credentials=allow_credentials,
        timeout_ms=context.browser_timeout_ms,
    )
    challenge_record = await PasskeyChallengeStore(redis_client).create(
        challenge=challenge,
        ceremony="authentication",
        rp_id=context.rp_id,
        expected_origin=context.origin,
        auth_realm_id=str(current_realm.auth_realm.id),
        realm_key=current_realm.realm_key,
        audience=current_realm.audience,
        principal_class=principal_class,
        principal_subject=principal_subject,
        user_handle=None,
        identifier_hash=identifier_hash,
        require_user_verification=True,
        ttl_seconds=context.challenge_ttl_seconds,
    )
    _track("authentication_options", "success")
    return PasskeyOptionsResponse(
        challenge_id=challenge_record.challenge_id,
        public_key=options,
        expires_at=datetime.fromisoformat(challenge_record.expires_at),
    )


@router.post("/authentication/verify", response_model=LoginResponse)
async def verify_passkey_authentication(
    payload: PasskeyAuthenticationVerifyRequest,
    request: Request,
    response: Response,
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    context = await _passkey_context(request, current_realm.realm_type, db)
    _require_passkeys_enabled(context.authentication_enabled)
    try:
        challenge = await PasskeyChallengeStore(redis_client).consume(
            payload.challenge_id,
            expected_ceremony="authentication",
        )
    except PasskeyChallengeError as exc:
        logger.warning("Passkey authentication challenge rejected", extra={"reason": str(exc)})
        _track("authentication_verify", "challenge_failed")
        raise _generic_unauthorized() from exc

    try:
        credential_hash = credential_hash_from_browser_payload(payload.credential)
    except PasskeyVerificationError as exc:
        raise _generic_unauthorized() from exc

    await _enforce_rate_limit(
        redis_client,
        key=f"passkey:rl:authentication_verify:{current_realm.realm_key}:{credential_hash}:{_client_ip(request)}",
        limit=20,
        window_seconds=60,
    )

    repo = PasskeyCredentialRepository(db)
    credential = await repo.get_active_by_hash(credential_hash)
    if credential is None:
        _track("authentication_verify", "unknown_credential")
        raise _generic_unauthorized()

    if (
        credential.auth_realm_id != current_realm.auth_realm.id
        or credential.realm_key != current_realm.realm_key
        or credential.audience != current_realm.audience
        or challenge.auth_realm_id != str(current_realm.auth_realm.id)
        or challenge.realm_key != current_realm.realm_key
        or (challenge.principal_class and challenge.principal_class != credential.principal_class)
        or (challenge.principal_subject and challenge.principal_subject != credential.principal_subject)
    ):
        _track("authentication_verify", "realm_mismatch")
        raise _generic_unauthorized()

    try:
        verified = PasskeyWebAuthnService().verify_authentication(
            payload=payload.credential,
            challenge=challenge,
            credential=credential,
        )
    except PasskeyVerificationError as exc:
        _track("authentication_verify", "verification_failed")
        raise _generic_unauthorized() from exc

    if verified.credential_id_hash != credential.credential_id_hash:
        raise _generic_unauthorized()
    _enforce_credential_user_handle(payload.credential, credential)

    if verified.new_sign_count == 0 and credential.sign_count == 0:
        logger.warning(
            "Passkey zero sign-count accepted",
            extra={"credential_id_hash": credential.credential_id_hash, "realm_key": credential.realm_key},
        )
    elif verified.new_sign_count <= credential.sign_count:
        await repo.mark_clone_suspected(credential)
        await _audit_passkey_event(
            db,
            action="passkey.sign_count_anomaly",
            actor_id=UUID(credential.principal_subject),
            credential=credential,
            request=request,
            metadata={
                "credential_id_hash": credential.credential_id_hash,
                "stored_sign_count": credential.sign_count,
                "new_sign_count": verified.new_sign_count,
                "ceremony": "authentication",
            },
        )
        await db.commit()
        raise _generic_unauthorized()

    await repo.mark_used(
        credential,
        sign_count=verified.new_sign_count,
        user_verified=verified.user_verified,
        backed_up=verified.backed_up,
        device_type=verified.device_type,
    )
    user = await AdminUserRepository(db).get_by_id(UUID(credential.principal_subject))
    if not user or not user.is_active:
        raise _generic_unauthorized()

    await _audit_passkey_event(
        db,
        action="passkey.authenticated",
        actor_id=user.id,
        credential=credential,
        request=request,
        metadata={"credential_id_hash": credential.credential_id_hash, "realm_key": credential.realm_key},
    )
    _track("authentication_verify", "success")
    return await _issue_session_for_passkey(
        request=request,
        response=response,
        db=db,
        auth_service=auth_service,
        user=user,
        credential=credential,
        cookie_namespace=current_realm.cookie_namespace,
    )


@router.get("", response_model=PasskeyCredentialListResponse)
async def list_passkeys(
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
) -> PasskeyCredentialListResponse:
    context = await _passkey_context(request, current_realm.realm_type, db)
    _require_passkeys_enabled(context.enabled)
    credentials = await PasskeyCredentialRepository(db).list_active_for_principal(
        auth_realm_id=current_realm.auth_realm.id,
        principal_class=get_principal_type_for_realm(current_realm),
        principal_subject=str(current_user.id),
    )
    return PasskeyCredentialListResponse(credentials=[_credential_response(item) for item in credentials])


@router.patch("/{credential_id}", response_model=PasskeyCredentialResponse)
async def rename_passkey(
    credential_id: UUID,
    payload: PasskeyRenameRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> PasskeyCredentialResponse:
    context = await _passkey_context(request, current_realm.realm_type, db)
    _require_passkeys_enabled(context.enabled)
    principal_class = get_principal_type_for_realm(current_realm)
    await enforce_passkey_fresh_auth(
        request=request,
        redis_client=redis_client,
        principal_subject=str(current_user.id),
        principal_class=principal_class,
        auth_realm_id=str(current_realm.auth_realm.id),
        realm_key=current_realm.realm_key,
        action=f"passkey.credential.rename:{credential_id}",
    )
    repo = PasskeyCredentialRepository(db)
    credential = await repo.rename_for_principal(
        credential_id=credential_id,
        auth_realm_id=current_realm.auth_realm.id,
        principal_class=principal_class,
        principal_subject=str(current_user.id),
        label=payload.label.strip(),
    )
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passkey not found")
    await _audit_passkey_event(
        db,
        action="passkey.renamed",
        actor_id=current_user.id,
        credential=credential,
        request=request,
        metadata={"credential_id_hash": credential.credential_id_hash},
    )
    return _credential_response(credential)


@router.delete("/{credential_id}", response_model=PasskeyDeleteResponse)
async def delete_passkey(
    credential_id: UUID,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> PasskeyDeleteResponse:
    context = await _passkey_context(request, current_realm.realm_type, db)
    _require_passkeys_enabled(context.enabled)
    repo = PasskeyCredentialRepository(db)
    principal_class = get_principal_type_for_realm(current_realm)
    await enforce_passkey_fresh_auth(
        request=request,
        redis_client=redis_client,
        principal_subject=str(current_user.id),
        principal_class=principal_class,
        auth_realm_id=str(current_realm.auth_realm.id),
        realm_key=current_realm.realm_key,
        action=f"passkey.credential.revoke:{credential_id}",
    )
    active_count = await repo.count_active_for_principal(
        auth_realm_id=current_realm.auth_realm.id,
        principal_class=principal_class,
        principal_subject=str(current_user.id),
    )
    has_recovery_method = bool(current_user.password_hash or (current_user.email and current_user.is_email_verified))
    if active_count <= 1 and not has_recovery_method:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete the last viable login method")

    credential = await repo.revoke_for_principal(
        credential_id=credential_id,
        auth_realm_id=current_realm.auth_realm.id,
        principal_class=principal_class,
        principal_subject=str(current_user.id),
    )
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passkey not found")
    await _audit_passkey_event(
        db,
        action="passkey.revoked",
        actor_id=current_user.id,
        credential=credential,
        request=request,
        metadata={"credential_id_hash": credential.credential_id_hash},
    )
    return PasskeyDeleteResponse(id=credential.id, status=credential.status)


@router.post("/reauthentication/options", response_model=PasskeyOptionsResponse)
async def create_passkey_reauthentication_options(
    payload: PasskeyReauthenticationOptionsRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> PasskeyOptionsResponse:
    context = await _passkey_context(request, current_realm.realm_type, db)
    _require_passkeys_enabled(context.reauthentication_enabled)
    principal_class = get_principal_type_for_realm(current_realm)
    credentials = await PasskeyCredentialRepository(db).list_active_for_principal(
        auth_realm_id=current_realm.auth_realm.id,
        principal_class=principal_class,
        principal_subject=str(current_user.id),
    )
    if not credentials:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active passkey available")
    options, challenge = PasskeyWebAuthnService().authentication_options(
        rp_id=context.rp_id,
        allow_credentials=credentials,
        timeout_ms=context.browser_timeout_ms,
    )
    challenge_record = await PasskeyChallengeStore(redis_client).create(
        challenge=challenge,
        ceremony="reauthentication",
        rp_id=context.rp_id,
        expected_origin=context.origin,
        auth_realm_id=str(current_realm.auth_realm.id),
        realm_key=current_realm.realm_key,
        audience=current_realm.audience,
        principal_class=principal_class,
        principal_subject=str(current_user.id),
        user_handle=passkey_user_handle(
            auth_realm_id=current_realm.auth_realm.id,
            principal_class=principal_class,
            principal_subject=str(current_user.id),
        ),
        identifier_hash=passkey_identifier_hash(current_user.email or current_user.login),
        require_user_verification=True,
        action=payload.action,
        ttl_seconds=context.challenge_ttl_seconds,
    )
    return PasskeyOptionsResponse(
        challenge_id=challenge_record.challenge_id,
        public_key=options,
        expires_at=datetime.fromisoformat(challenge_record.expires_at),
    )


@router.post("/reauthentication/verify", response_model=PasskeyReauthenticationVerifyResponse)
async def verify_passkey_reauthentication(
    payload: PasskeyReauthenticationVerifyRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> PasskeyReauthenticationVerifyResponse:
    context = await _passkey_context(request, current_realm.realm_type, db)
    _require_passkeys_enabled(context.reauthentication_enabled)
    principal_class = get_principal_type_for_realm(current_realm)
    try:
        challenge = await PasskeyChallengeStore(redis_client).consume(
            payload.challenge_id,
            expected_ceremony="reauthentication",
        )
    except PasskeyChallengeError as exc:
        raise _generic_unauthorized() from exc

    if (
        challenge.action != payload.action
        or challenge.auth_realm_id != str(current_realm.auth_realm.id)
        or challenge.realm_key != current_realm.realm_key
        or challenge.audience != current_realm.audience
        or challenge.principal_class != principal_class
        or challenge.principal_subject != str(current_user.id)
    ):
        raise _generic_unauthorized()

    try:
        credential_hash = credential_hash_from_browser_payload(payload.credential)
    except PasskeyVerificationError as exc:
        raise _generic_unauthorized() from exc

    repo = PasskeyCredentialRepository(db)
    credential = await repo.get_active_by_hash(credential_hash)
    if (
        credential is None
        or credential.auth_realm_id != current_realm.auth_realm.id
        or credential.realm_key != current_realm.realm_key
        or credential.audience != current_realm.audience
        or credential.principal_class != principal_class
        or credential.principal_subject != str(current_user.id)
    ):
        raise _generic_unauthorized()

    try:
        verified = PasskeyWebAuthnService().verify_authentication(
            payload=payload.credential,
            challenge=challenge,
            credential=credential,
        )
    except PasskeyVerificationError as exc:
        raise _generic_unauthorized() from exc

    if verified.credential_id_hash != credential.credential_id_hash:
        raise _generic_unauthorized()
    _enforce_credential_user_handle(payload.credential, credential)

    if verified.new_sign_count == 0 and credential.sign_count == 0:
        logger.warning(
            "Passkey zero sign-count accepted for reauthentication",
            extra={"credential_id_hash": credential.credential_id_hash, "realm_key": credential.realm_key},
        )
    elif verified.new_sign_count <= credential.sign_count:
        await repo.mark_clone_suspected(credential)
        await _audit_passkey_event(
            db,
            action="passkey.sign_count_anomaly",
            actor_id=current_user.id,
            credential=credential,
            request=request,
            metadata={
                "credential_id_hash": credential.credential_id_hash,
                "stored_sign_count": credential.sign_count,
                "new_sign_count": verified.new_sign_count,
                "ceremony": "reauthentication",
            },
        )
        await db.commit()
        raise _generic_unauthorized()

    await repo.mark_used(
        credential,
        sign_count=verified.new_sign_count,
        user_verified=verified.user_verified,
        backed_up=verified.backed_up,
        device_type=verified.device_type,
    )

    grant = await PasskeyFreshAuthGrantStore(redis_client).create(
        principal_subject=str(current_user.id),
        principal_class=principal_class,
        auth_realm_id=str(current_realm.auth_realm.id),
        realm_key=current_realm.realm_key,
        action=payload.action,
        ttl_seconds=context.fresh_auth_ttl_seconds,
    )
    await _audit_passkey_event(
        db,
        action="passkey.reauthenticated",
        actor_id=current_user.id,
        credential=credential,
        request=request,
        metadata={"credential_id_hash": credential.credential_id_hash, "action": payload.action},
    )
    return PasskeyReauthenticationVerifyResponse(
        fresh_auth_grant_id=grant.grant_id,
        expires_at=datetime.fromisoformat(grant.expires_at),
    )
