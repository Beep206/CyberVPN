"""Authentication dependencies for FastAPI.

LOW-007: All auth dependencies now include JWT revocation checks.
SEC-01: Supports both Bearer header (mobile) and httpOnly cookie (web) auth.
"""

import logging
from dataclasses import dataclass
from uuid import UUID

import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.mobile_auth import DeviceInfoDTO
from src.application.dto.mobile_auth import Platform as MobilePlatform
from src.application.services.auth_service import AuthService
from src.application.services.jwt_revocation_service import JWTRevocationService
from src.application.use_cases.auth_realms import RealmResolution
from src.domain.enums import PrincipalClass
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.monitoring.instrumentation.partner_runtime import (
    PARTNER_PORTAL_SURFACE,
    PARTNER_PRINCIPAL_CLASS,
    bind_partner_context_from_realm,
    bind_partner_runtime_context,
    log_partner_runtime_event,
    observe_partner_cross_realm_denied,
    observe_partner_wrong_host_token_rejected,
)
from src.presentation.api.v1.auth.cookies import get_access_token_cookie
from src.presentation.dependencies.auth_realms import (
    get_request_admin_realm,
    get_request_auth_realm,
    get_request_customer_realm,
)
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_auth_service

logger = logging.getLogger(__name__)
# auto_error=False so we can fall back to cookie when no Authorization header
security = HTTPBearer(auto_error=False)


@dataclass
class TokenValidationResult:
    """Result of JWT token validation."""

    user_id: str
    jti: str | None = None
    principal_type: str | None = None
    realm_id: str | None = None
    realm_key: str | None = None
    audience: str | None = None
    claims: dict | None = None


@dataclass
class CurrentPrincipalActor:
    principal_id: UUID
    principal_type: str
    auth_realm_id: UUID
    auth_realm_key: str
    audience: str


@dataclass
class PendingMobile2FAContext:
    user: MobileUserModel
    device: DeviceInfoDTO
    auth_method: str | None = None


def _record_partner_realm_denial(
    *,
    reason: str,
    token_payload: dict | None = None,
) -> None:
    bind_partner_runtime_context(
        surface=PARTNER_PORTAL_SURFACE,
        realm_type="partner",
        principal_class=PARTNER_PRINCIPAL_CLASS,
        route_group="auth_session",
        result="denied",
        error_code=reason,
    )
    observe_partner_cross_realm_denied(reason=reason)
    if reason in {"realm_key_mismatch", "wrong_host_token"}:
        observe_partner_wrong_host_token_rejected(reason=reason)
    log_partner_runtime_event(
        "partner_auth.cross_realm_denied",
        level="warning",
        reason=reason,
        token_realm_key=token_payload.get("realm_key") if token_payload else None,
        token_audience=token_payload.get("aud") if token_payload else None,
    )


async def _validate_token(
    token: str,
    auth_service: AuthService,
    redis_client: redis.Redis | None = None,
    *,
    check_revocation: bool = True,
    allowed_token_types: frozenset[str] = frozenset({"access"}),
    expected_audience: str | None = None,
    expected_realm_key: str | None = None,
    allow_legacy_without_realm: bool = False,
) -> TokenValidationResult | None:
    """Validate JWT token and optionally check revocation.

    LOW-007: Common token validation logic extracted for reuse.

    Args:
        token: JWT access token
        auth_service: Auth service for token decoding
        redis_client: Redis client for revocation check (required if check_revocation=True)
        check_revocation: Whether to check JWT revocation list

    Returns:
        TokenValidationResult if token is valid, None otherwise

    Raises:
        HTTPException: If token is revoked and check_revocation=True
        JWTError: If token decoding fails (caller should handle)
    """
    try:
        payload = auth_service.decode_token(token, audience=expected_audience)
    except JWTError:
        if expected_realm_key == "partner" or expected_audience == "cybervpn:partner":
            raw_payload: dict | None = None
            try:
                raw_payload = auth_service.decode_token(token, audience=None)
            except JWTError:
                raw_payload = None
            if raw_payload is not None:
                if (
                    expected_realm_key
                    and raw_payload.get("realm_key")
                    and raw_payload.get("realm_key") != expected_realm_key
                ):
                    _record_partner_realm_denial(reason="realm_key_mismatch", token_payload=raw_payload)
                elif (
                    expected_audience
                    and raw_payload.get("aud")
                    and raw_payload.get("aud") != expected_audience
                ):
                    _record_partner_realm_denial(reason="audience_mismatch", token_payload=raw_payload)
        if not allow_legacy_without_realm:
            raise
        payload = auth_service.decode_token(token, audience=None)

    if payload.get("type") not in allowed_token_types:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    if expected_realm_key and payload.get("realm_key") and payload.get("realm_key") != expected_realm_key:
        if expected_realm_key == "partner":
            _record_partner_realm_denial(reason="realm_key_mismatch", token_payload=payload)
        return None
    if expected_audience and payload.get("aud") and payload.get("aud") != expected_audience:
        if expected_audience == "cybervpn:partner":
            _record_partner_realm_denial(reason="audience_mismatch", token_payload=payload)
        return None

    jti = payload.get("jti")

    # SEC-003 + LOW-007: Check if token is revoked
    if check_revocation and jti and redis_client:
        revocation_service = JWTRevocationService(redis_client)
        if await revocation_service.is_revoked(jti):
            logger.warning(
                "Revoked token used",
                extra={"jti": jti[:8] + "..." if jti else None, "user_id": user_id},
            )
            return None  # Return None for optional auth, caller decides on exception

    return TokenValidationResult(
        user_id=user_id,
        jti=jti,
        principal_type=payload.get("principal_type"),
        realm_id=payload.get("realm_id"),
        realm_key=payload.get("realm_key"),
        audience=payload.get("aud"),
        claims=payload,
    )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    redis_client: redis.Redis = Depends(get_redis),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
) -> AdminUserModel:
    """Get current authenticated user from JWT token.

    SEC-01: Accepts token from Authorization Bearer header (mobile/API) OR
    from the httpOnly ``access_token`` cookie (web frontend).
    SEC-003: Includes JWT revocation check to ensure logout invalidates tokens.
    LOW-007: Uses shared _validate_token() helper for consistent validation.

    Raises:
        HTTPException: 401 if token is invalid, expired, revoked, or user not found
    """
    # Resolve the raw JWT token: prefer Authorization header, fall back to cookie
    token: str | None = None
    if credentials:
        token = credentials.credentials
    else:
        token = get_access_token_cookie(request.cookies, current_realm.cookie_namespace)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        result = await _validate_token(
            token,
            auth_service,
            redis_client,
            check_revocation=True,
            expected_audience=current_realm.audience,
            expected_realm_key=current_realm.realm_key,
            allow_legacy_without_realm=current_realm.realm_key == "admin",
        )
        if not result:
            # Token was invalid or revoked
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked token")

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    repo = AdminUserRepository(db)
    user = await repo.get_by_id(UUID(result.user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    bind_partner_context_from_realm(
        current_realm=current_realm,
        route_group="auth_session",
        principal_class=result.principal_type or PARTNER_PRINCIPAL_CLASS,
        result="authenticated",
    )
    return user


async def get_current_pending_2fa_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    redis_client: redis.Redis = Depends(get_redis),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
) -> AdminUserModel:
    """Resolve a user from a short-lived pending-2FA token."""
    token = credentials.credentials if credentials else get_access_token_cookie(
        request.cookies,
        current_realm.cookie_namespace,
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="2FA login session not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        result = await _validate_token(
            token,
            auth_service,
            redis_client,
            check_revocation=True,
            allowed_token_types=frozenset({"2fa_pending"}),
            expected_audience=current_realm.audience,
            expected_realm_key=current_realm.realm_key,
            allow_legacy_without_realm=current_realm.realm_key == "admin",
        )
        if not result:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired 2FA login session")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired 2FA login session")

    repo = AdminUserRepository(db)
    user = await repo.get_by_id(UUID(result.user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    bind_partner_context_from_realm(
        current_realm=current_realm,
        route_group="auth_session",
        principal_class=result.principal_type or PARTNER_PRINCIPAL_CLASS,
        result="pending_2fa_authenticated",
    )
    return user


async def get_current_active_user(
    user: AdminUserModel = Depends(get_current_user),
) -> AdminUserModel:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


async def optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    redis_client: redis.Redis = Depends(get_redis),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
) -> AdminUserModel | None:
    """Get user from JWT token if present and valid, None otherwise.

    SEC-01: Accepts token from Authorization header or httpOnly cookie.
    LOW-007: Now includes JWT revocation check for consistency with get_current_user.
    Revoked tokens will return None (not authenticated) rather than the user.

    Args:
        request: HTTP request (for cookie fallback)
        credentials: Optional Bearer token from Authorization header
        db: Database session
        auth_service: Auth service for token decoding
        redis_client: Redis client for revocation check

    Returns:
        AdminUserModel if token is valid and not revoked, None otherwise
    """
    # Resolve the raw JWT token: prefer Authorization header, fall back to cookie
    token: str | None = None
    if credentials:
        token = credentials.credentials
    else:
        token = get_access_token_cookie(request.cookies, current_realm.cookie_namespace)

    if not token:
        return None

    try:
        result = await _validate_token(
            token,
            auth_service,
            redis_client,
            check_revocation=True,
            expected_audience=current_realm.audience,
            expected_realm_key=current_realm.realm_key,
            allow_legacy_without_realm=current_realm.realm_key == "admin",
        )
        if not result:
            return None

        repo = AdminUserRepository(db)
        user = await repo.get_by_id(UUID(result.user_id))
        if not user or not user.is_active:
            return None
        return user
    except JWTError:
        return None


async def get_current_mobile_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> UUID:
    """Extract and validate mobile user ID from JWT token.

    SEC-006: Verifies user is active before returning ID.

    Used for endpoints that return data scoped to the current user.
    Accepts Bearer token first (mobile), then falls back to httpOnly cookie
    (web dashboard).
    Returns the user UUID after verifying user is active.

    Raises:
        HTTPException: 401 if token is invalid, expired, revoked, or user inactive.
    """
    token: str | None = credentials.credentials if credentials else get_access_token_cookie(
        request.cookies,
        current_realm.cookie_namespace,
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid token"},
        )

    try:
        try:
            payload = auth_service.decode_token(token, audience=current_realm.audience)
        except JWTError:
            payload = auth_service.decode_token(token, audience=None)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Invalid token type"},
            )
        if payload.get("aud") and payload.get("aud") != current_realm.audience:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Invalid audience"},
            )
        if payload.get("realm_key") and payload.get("realm_key") != current_realm.realm_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Invalid realm"},
            )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Invalid token"},
            )

        # SEC-003: Check if token is revoked
        jti = payload.get("jti")
        if jti:
            revocation_service = JWTRevocationService(redis_client)
            if await revocation_service.is_revoked(jti):
                logger.warning("Revoked mobile token used", extra={"jti": jti[:8] + "...", "user_id": user_id})
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "TOKEN_REVOKED", "message": "Token has been revoked"},
                )

        # SEC-006: Verify user is active
        repo = MobileUserRepository(db)
        user = await repo.get_by_id(UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "USER_NOT_FOUND", "message": "User not found"},
            )
        if not user.is_active:
            logger.warning("Inactive user attempted mobile access", extra={"user_id": user_id})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "USER_INACTIVE", "message": "User account is inactive"},
            )

        return UUID(user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"},
        )


async def get_current_pending_mobile_2fa_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> PendingMobile2FAContext:
    """Resolve a mobile user and device snapshot from a short-lived pending-2FA token."""
    token: str | None = credentials.credentials if credentials else get_access_token_cookie(
        request.cookies,
        current_realm.cookie_namespace,
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_2FA_TOKEN", "message": "2FA login session not found"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        result = await _validate_token(
            token,
            auth_service,
            redis_client,
            check_revocation=True,
            allowed_token_types=frozenset({"2fa_pending"}),
            expected_audience=current_realm.audience,
            expected_realm_key=current_realm.realm_key,
            allow_legacy_without_realm=True,
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_2FA_TOKEN", "message": "Invalid or expired 2FA login session"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_2FA_TOKEN", "message": "Invalid or expired 2FA login session"},
        )

    claims = result.claims or {}
    device_id = claims.get("device_id")
    platform = claims.get("platform")
    platform_id = claims.get("platform_id")
    os_version = claims.get("os_version")
    app_version = claims.get("app_version")
    device_model = claims.get("device_model")

    if not all(
        isinstance(value, str) and value
        for value in [device_id, platform, platform_id, os_version, app_version, device_model]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_2FA_TOKEN", "message": "2FA login session is missing device data"},
        )

    repo = MobileUserRepository(db)
    user = await repo.get_by_id(UUID(result.user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_INACTIVE", "message": "Inactive user"},
        )

    return PendingMobile2FAContext(
        user=user,
        device=DeviceInfoDTO(
            device_id=device_id,
            platform=MobilePlatform(platform),
            platform_id=platform_id,
            os_version=os_version,
            app_version=app_version,
            device_model=device_model,
            push_token=claims.get("push_token"),
        ),
        auth_method=claims.get("auth_method") if isinstance(claims.get("auth_method"), str) else None,
    )


async def get_current_principal_actor(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    current_realm: RealmResolution = Depends(get_request_auth_realm),
) -> CurrentPrincipalActor:
    token: str | None = credentials.credentials if credentials else get_access_token_cookie(
        request.cookies,
        current_realm.cookie_namespace,
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid token"},
        )

    try:
        result = await _validate_token(
            token,
            auth_service,
            redis_client,
            check_revocation=True,
            expected_audience=current_realm.audience,
            expected_realm_key=current_realm.realm_key,
            allow_legacy_without_realm=current_realm.realm_key in {"admin", "customer"},
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Invalid token"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"},
        )

    principal_id = UUID(result.user_id)
    if current_realm.realm_type in {"admin", "partner"}:
        repo = AdminUserRepository(db)
        actor = await repo.get_by_id(principal_id)
        if not actor or not actor.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "USER_NOT_FOUND", "message": "User not found or inactive"},
            )
        fallback_principal_type = (
            PrincipalClass.PARTNER_OPERATOR.value
            if current_realm.realm_type == "partner"
            else PrincipalClass.ADMIN.value
        )
    elif current_realm.realm_type == "customer":
        repo = MobileUserRepository(db)
        actor = await repo.get_by_id(principal_id)
        if not actor or not actor.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "USER_NOT_FOUND", "message": "User not found or inactive"},
            )
        fallback_principal_type = PrincipalClass.CUSTOMER.value
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "UNSUPPORTED_PRINCIPAL", "message": "Unsupported principal realm"},
        )

    return CurrentPrincipalActor(
        principal_id=principal_id,
        principal_type=result.principal_type or fallback_principal_type,
        auth_realm_id=current_realm.auth_realm.id,
        auth_realm_key=current_realm.realm_key,
        audience=current_realm.audience,
    )
