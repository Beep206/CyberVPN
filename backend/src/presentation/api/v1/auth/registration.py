"""User registration route with OTP email verification and invite token system (CRIT-1)."""

import logging

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.invite_service import InviteTokenService
from src.application.services.otp_service import OtpService
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
from src.presentation.api.v1.auth.schemas import RegisterRequest, RegisterResponse
from src.presentation.dependencies.auth_realms import get_request_admin_realm
from src.presentation.dependencies.database import get_db
from src.shared.logging.sanitization import sanitize_email, sanitize_username

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


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


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    http_request: Request,
    invite_token: str | None = Query(
        default=None,
        description="Invite token required for registration when invite-only mode is enabled",
    ),
    db: AsyncSession = Depends(get_db),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
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
            extra={"email": request.email, "login": request.login},
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
            detail="Registration is currently disabled. Contact an administrator for access.",
        )

    # CRIT-1: Check for invite token if required
    invite_service = InviteTokenService(redis_client)
    invite_data = None

    if settings.registration_invite_required:
        if not invite_token:
            logger.warning(
                "Registration attempt blocked - missing invite token",
                extra={"email": request.email, "login": request.login},
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

        # Validate and consume the invite token (single-use)
        invite_data = await invite_service.validate_and_consume(invite_token)

        if not invite_data:
            logger.warning(
                "Registration attempt blocked - invalid/expired invite token",
                extra={
                    "email": request.email,
                    "login": request.login,
                    "token_prefix": invite_token[:8] if len(invite_token) >= 8 else invite_token,
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
        if invite_data.get("email_hint") and invite_data["email_hint"] != request.email:
            logger.warning(
                "Registration attempt blocked - email mismatch",
                extra={
                    "email": request.email,
                    "expected_email": invite_data.get("email_hint"),
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
        "User registered successfully",
        extra={
            "user_id": str(result.user.id),
            "login": result.user.login,
            "email": result.user.email,
            "role": role.value,
            "invite_used": bool(invite_token),
        },
    )

    return RegisterResponse(
        id=result.user.id,
        login=result.user.login,
        email=result.user.email or "",
        is_active=result.user.is_active,
        is_email_verified=result.user.is_email_verified,
        message=(
            "Registration successful. Please check your email for verification code."
            if request.email
            else "Registration successful. You can sign in with your username and password."
        ),
    )
