"""User registration route with OTP email verification and invite token system (CRIT-1)."""

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.invite_service import InviteTokenService
from src.application.services.otp_service import OtpRateLimitError, OtpService
from src.application.services.public_registration_policy import PublicRegistrationDisabledError
from src.application.services.registration_access_service import (
    REGISTRATION_ACCESS_EXCHANGE_SESSION_TTL_SECONDS,
    RegistrationAccessGrantService,
    registration_access_email_hint_matches,
)
from src.application.use_cases.auth.register import RegisterUseCase
from src.application.use_cases.auth_realms import RealmResolution
from src.config.settings import settings
from src.domain.enums import AdminRole
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.audit_log_repo import AuditLogRepository
from src.infrastructure.database.repositories.otp_code_repo import OtpCodeRepository
from src.infrastructure.monitoring.client_context import resolve_web_client_context
from src.infrastructure.monitoring.instrumentation.routes import (
    sync_auth_security_posture,
    track_auth_flow_event,
    track_auth_password_identifier_event,
    track_registration,
    track_registration_funnel_step,
)
from src.infrastructure.tasks.email_task_dispatcher import (
    EmailTaskDispatcher,
    get_email_dispatcher,
)
from src.presentation.api.v1.auth.schemas import (
    RegisterRequest,
    RegisterResponse,
    RegistrationAccessExchangeRequest,
    RegistrationAccessExchangeResponse,
    RegistrationAccessPolicyResponse,
)
from src.presentation.dependencies.auth_realms import get_request_web_auth_realm
from src.presentation.dependencies.database import get_db
from src.shared.logging.sanitization import sanitize_email, sanitize_username

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])
REGISTRATION_ACCESS_COOKIE_NAME = "__Host-cvpn_registration_access"
REGISTRATION_ACCESS_COOKIE_PATH = "/"


async def _release_invite_registration_reservation(
    invite_service: InviteTokenService,
    *,
    invite_token: str | None,
    reservation_id: str | None,
) -> None:
    if not invite_token or not reservation_id:
        return
    try:
        await invite_service.release_registration_reservation(invite_token, reservation_id)
    except Exception:  # noqa: S110
        logger.warning(
            "invite_token_registration_reservation_release_failed",
            exc_info=True,
        )


async def _release_registration_access_reservation(
    *,
    registration_access_service: RegistrationAccessGrantService,
    invite_service: InviteTokenService,
    invite_token: str | None,
    reservation_id: str | None,
    reservation_source: str | None,
    reason: str,
    request_host: str,
) -> None:
    if not invite_token or not reservation_id:
        return
    if reservation_source == "registration_access_grants":
        try:
            await registration_access_service.release_registration_reservation(
                token=invite_token,
                reservation_id=reservation_id,
                reason=reason,
            )
        except Exception:  # noqa: S110
            logger.warning(
                "registration_access_reservation_release_failed",
                exc_info=True,
            )
        return
    if reservation_source == "registration_access_exchange_session":
        try:
            await registration_access_service.release_exchange_session_registration_reservation(
                session_token=invite_token,
                reservation_id=reservation_id,
                reason=reason,
                host=request_host,
            )
        except Exception:  # noqa: S110
            logger.warning(
                "registration_access_exchange_reservation_release_failed",
                exc_info=True,
            )
        return
    if reservation_source == "legacy_redis_invite":
        await _release_invite_registration_reservation(
            invite_service,
            invite_token=invite_token,
            reservation_id=reservation_id,
        )


def _request_host(request: Request) -> str:
    return (request.url.hostname or request.headers.get("host") or "unknown").split(":", 1)[0].lower()


def _set_registration_access_cookie(
    response: Response,
    *,
    session_token: str,
    max_age: int,
) -> None:
    response.set_cookie(
        key=REGISTRATION_ACCESS_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=REGISTRATION_ACCESS_COOKIE_PATH,
        max_age=max(0, min(max_age, REGISTRATION_ACCESS_EXCHANGE_SESSION_TTL_SECONDS)),
        domain=None,
    )


def _clear_registration_access_cookie(response: Response) -> None:
    response.set_cookie(
        key=REGISTRATION_ACCESS_COOKIE_NAME,
        value="",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=REGISTRATION_ACCESS_COOKIE_PATH,
        max_age=0,
        domain=None,
    )


async def _log_registration_attempt(
    audit_repo: AuditLogRepository,
    success: bool,
    email: str | None,
    login: str,
    reason: str | None = None,
    invite_token: str | None = None,
) -> None:
    """Log registration attempt for audit trail.

    SEC-007: PII is sanitized before storing in audit logs.
    """
    try:
        await audit_repo.create(
            event_type="registration_attempt",
            actor_id=None,  # Anonymous user
            resource_type="user",
            resource_id=None,
            details={
                "success": success,
                "email": sanitize_email(email),  # SEC-007: Sanitize PII
                "login": sanitize_username(login),  # SEC-007: Sanitize PII
                "reason": reason,
                "invite_token_used": bool(invite_token),
            },
        )
    except Exception as e:
        # Don't fail registration if audit logging fails
        logger.error(f"Failed to log registration attempt: {e}")


@router.post(
    "/registration-access/exchange",
    response_model=RegistrationAccessExchangeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        403: {"description": "Invalid, expired, or already exchanged registration access token"},
    },
)
async def exchange_registration_access(
    request: RegistrationAccessExchangeRequest,
    http_request: Request,
    response: Response,
    idempotency_key: UUID = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_realm: RealmResolution = Depends(get_request_web_auth_realm),
) -> RegistrationAccessExchangeResponse:
    """Exchange a raw pre-registration access token for a host-bound cookie grant."""

    service = RegistrationAccessGrantService(db)
    result = await service.exchange_for_browser(
        token=request.registration_access_token,
        idempotency_key=str(idempotency_key),
        host=_request_host(http_request),
        auth_realm_id=current_realm.auth_realm.id,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "detail": "Invalid or expired registration access token.",
                "code": "REGISTRATION_ACCESS_INVALID",
            },
        )

    max_age = int((result.expires_at - datetime.now(UTC)).total_seconds())
    _set_registration_access_cookie(
        response,
        session_token=result.session_token,
        max_age=max_age,
    )
    return RegistrationAccessExchangeResponse(
        status="exchanged",
        email_hint_present=result.grant.email_hint_hash is not None,
        email_hint_masked=None,
        expires_at=result.expires_at,
        registration_policy=RegistrationAccessPolicyResponse(
            invite_required=settings.registration_invite_required,
            auth_realm_key=current_realm.realm_key,
        ),
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    http_request: Request,
    response: Response,
    invite_token: str | None = Query(
        default=None,
        description="Deprecated legacy invite token. Registration access tokens must be exchanged first.",
    ),
    db: AsyncSession = Depends(get_db),
    current_realm: RealmResolution = Depends(get_request_web_auth_realm),
    email_dispatcher: EmailTaskDispatcher = Depends(get_email_dispatcher),
    redis_client: redis.Redis = Depends(get_redis),
) -> RegisterResponse:
    """
    Register a new user with email verification.

    Creates user with is_active=False, is_email_verified=False.
    Sends OTP verification email to the provided address.
    User must verify email before logging in.

    Security:
    - Registration is disabled by default (REGISTRATION_ENABLED=false)
    - When enabled with invite-only mode, requires valid invite token
    - All registration attempts are logged for audit
    """
    audit_repo = AuditLogRepository(db)

    # CRIT-1: Check if registration is enabled
    if not settings.registration_enabled:
        logger.warning(
            "Registration attempt blocked - registration disabled",
            extra={"reason": "registration_disabled"},
        )
        await _log_registration_attempt(
            audit_repo=audit_repo,
            success=False,
            email=request.email,
            login=request.login,
            reason="registration_disabled",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PublicRegistrationDisabledError("web_password").public_detail(),
        )

    # CRIT-1: Check for invite token if required
    invite_service = InviteTokenService(redis_client)
    registration_access_service = RegistrationAccessGrantService(db)
    invite_data = None
    invite_reservation_id: str | None = None
    invite_reservation_source: str | None = None
    request_host = _request_host(http_request)
    registration_access_session_token = http_request.cookies.get(REGISTRATION_ACCESS_COOKIE_NAME)

    if settings.registration_invite_required:
        if not registration_access_session_token and not invite_token:
            logger.warning(
                "Registration attempt blocked - missing invite token",
                extra={"reason": "invite_token_required"},
            )
            await _log_registration_attempt(
                audit_repo=audit_repo,
                success=False,
                email=request.email,
                login=request.login,
                reason="invite_token_required",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration requires a valid invite token.",
            )

        invite_reservation_id = str(uuid4())
        if registration_access_session_token:
            grant_data = await registration_access_service.reserve_exchange_session_for_registration(
                session_token=registration_access_session_token,
                reservation_id=invite_reservation_id,
                host=request_host,
                registration_idempotency_key=http_request.headers.get("Idempotency-Key"),
            )
            if grant_data is not None:
                invite_token = registration_access_session_token
                invite_data = grant_data.as_invite_data()
                invite_reservation_source = "registration_access_exchange_session"

        if invite_data is None and invite_token:
            if await registration_access_service.has_token(invite_token):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "detail": "Registration access token must be exchanged before registration.",
                        "code": "REGISTRATION_ACCESS_EXCHANGE_REQUIRED",
                    },
                )
            invite_data = await invite_service.reserve_for_registration(
                invite_token,
                invite_reservation_id,
            )
            if invite_data is not None:
                invite_reservation_source = "legacy_redis_invite"

        if not invite_data:
            logger.warning(
                "Registration attempt blocked - invalid/expired invite token",
                extra={
                    "email": sanitize_email(request.email),
                    "login": sanitize_username(request.login),
                },
            )
            await _log_registration_attempt(
                audit_repo=audit_repo,
                success=False,
                email=request.email,
                login=request.login,
                reason="invalid_invite_token",
                invite_token=invite_token,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired invite token.",
            )

        # Check if invite is restricted to specific email
        if not registration_access_email_hint_matches(invite_data, request.email):
            logger.warning(
                "Registration attempt blocked - email mismatch",
                extra={
                    "email": sanitize_email(request.email),
                    "expected_email": sanitize_email(invite_data.get("email_hint")),
                },
            )
            await _log_registration_attempt(
                audit_repo=audit_repo,
                success=False,
                email=request.email,
                login=request.login,
                reason="email_mismatch",
                invite_token=invite_token,
            )
            await _release_registration_access_reservation(
                registration_access_service=registration_access_service,
                invite_service=invite_service,
                invite_token=invite_token,
                reservation_id=invite_reservation_id,
                reservation_source=invite_reservation_source,
                reason="email_mismatch",
                request_host=request_host,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This invite token is not valid for this email address.",
            )

    # Determine role from invite or default to VIEWER
    role = AdminRole.VIEWER
    if invite_data and invite_data.get("role"):
        try:
            role = AdminRole(invite_data["role"])
        except ValueError:
            role = AdminRole.VIEWER

    user_repo = AdminUserRepository(db)
    otp_repo = OtpCodeRepository(db)
    auth_service = AuthService()
    otp_service = OtpService(otp_repo)

    use_case = RegisterUseCase(
        user_repo=user_repo,
        auth_service=auth_service,
        otp_service=otp_service,
        email_dispatcher=email_dispatcher,
    )

    try:
        result = await use_case.execute(
            login=request.login,
            email=request.email,
            password=request.password,
            tos_accepted=request.tos_accepted,
            marketing_consent=request.marketing_consent,
            role=role,
            locale=request.locale or "en-EN",
            auth_realm_id=current_realm.auth_realm.id,
            include_legacy_default=current_realm.realm_key == "admin",
        )
    except OtpRateLimitError as exc:
        await _release_registration_access_reservation(
            registration_access_service=registration_access_service,
            invite_service=invite_service,
            invite_token=invite_token,
            reservation_id=invite_reservation_id,
            reservation_source=invite_reservation_source,
            reason="otp_rate_limited",
            request_host=request_host,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "detail": str(exc),
                "code": "RATE_LIMITED",
                "next_resend_available_at": exc.next_available_at.isoformat() if exc.next_available_at else None,
            },
        ) from exc
    except Exception:
        await _release_registration_access_reservation(
            registration_access_service=registration_access_service,
            invite_service=invite_service,
            invite_token=invite_token,
            reservation_id=invite_reservation_id,
            reservation_source=invite_reservation_source,
            reason="registration_failed",
            request_host=request_host,
        )
        raise

    if invite_token and invite_reservation_id:
        if invite_reservation_source == "registration_access_exchange_session":
            consumed_grant_data = await registration_access_service.consume_reserved_exchange_session_for_registration(
                session_token=invite_token,
                reservation_id=invite_reservation_id,
                consumed_user_id=result.user.id,
                host=request_host,
            )
            consumed_invite_data = consumed_grant_data.as_invite_data() if consumed_grant_data is not None else None
        else:
            consumed_invite_data = await invite_service.consume_reserved_for_registration(
                invite_token,
                invite_reservation_id,
            )
        if not consumed_invite_data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "detail": "Invite token reservation expired or was already used.",
                    "code": "INVITE_TOKEN_RESERVATION_CONFLICT",
                },
            )
        invite_data = consumed_invite_data
        if invite_reservation_source == "registration_access_exchange_session":
            _clear_registration_access_cookie(response)

    registration_method = "email" if request.email else "username"
    password_identifier_type = "email" if request.email else "username"
    client_context = resolve_web_client_context(
        http_request.headers.get("User-Agent"),
        http_request.headers.get("sec-ch-ua-mobile"),
    )

    track_registration(method=registration_method)
    track_registration_funnel_step("started")
    track_auth_password_identifier_event(
        channel="web",
        identifier_type=password_identifier_type,
        client_context=client_context,
        step="registered",
    )
    track_auth_flow_event(
        channel="web",
        method="password",
        provider="native",
        locale=request.locale,
        client_context=client_context,
        step="registered",
    )
    if result.otp_sent:
        track_registration_funnel_step("email_sent")
        track_auth_password_identifier_event(
            channel="web",
            identifier_type="email",
            client_context=client_context,
            step="email_sent",
        )
        track_auth_flow_event(
            channel="web",
            method="password",
            provider="native",
            locale=request.locale,
            client_context=client_context,
            step="email_sent",
        )
    elif request.email is None:
        track_registration_funnel_step("activated")
        track_auth_password_identifier_event(
            channel="web",
            identifier_type="username",
            client_context=client_context,
            step="activated",
        )
        track_auth_flow_event(
            channel="web",
            method="password",
            provider="native",
            locale=request.locale,
            client_context=client_context,
            step="activated",
        )
    await sync_auth_security_posture(db, redis_client)

    # Log successful registration
    await _log_registration_attempt(
        audit_repo=audit_repo,
        success=True,
        email=request.email,
        login=request.login,
        invite_token=invite_token,
    )

    logger.info(
        "User registration flow completed",
        extra={
            "user_id": str(result.user.id),
            "login": sanitize_username(result.user.login),
            "email": sanitize_email(result.user.email),
            "role": role.value,
            "invite_used": bool(invite_token),
            "resumed_unverified_registration": result.resumed_unverified_registration,
        },
    )

    if result.resumed_unverified_registration:
        message = "Verification code sent. Please check your email and enter the code."
    elif request.email:
        message = "Registration successful. Please check your email for verification code."
    else:
        message = "Registration successful. You can sign in with your username and password."

    return RegisterResponse(
        id=result.user.id,
        login=result.user.login,
        email=result.user.email or "",
        is_active=result.user.is_active,
        is_email_verified=result.user.is_email_verified,
        message=message,
    )
