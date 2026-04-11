"""Authentication routes with brute force protection (HIGH-1).

Includes device fingerprint support for token binding (MED-002).
"""

import asyncio
import logging
import secrets
from datetime import UTC, datetime, timedelta
from time import perf_counter

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.jwt_revocation_service import JWTRevocationService
from src.application.services.login_protection import AccountLockedException, LoginProtectionService
from src.application.services.magic_link_service import MagicLinkService, RateLimitExceededError
from src.application.services.otp_service import OtpService
from src.application.services.telegram_auth import TelegramAuthService
from src.application.use_cases.auth.change_password import ChangePasswordUseCase
from src.application.use_cases.auth.delete_account import DeleteAccountUseCase
from src.application.use_cases.auth.forgot_password import ForgotPasswordUseCase
from src.application.use_cases.auth.login import LoginUseCase
from src.application.use_cases.auth.logout import LogoutUseCase
from src.application.use_cases.auth.refresh_token import RefreshTokenUseCase
from src.application.use_cases.auth.resend_otp import ResendOtpUseCase
from src.application.use_cases.auth.reset_password import ResetPasswordUseCase
from src.application.use_cases.auth.telegram_bot_link import TelegramBotLinkUseCase
from src.application.use_cases.auth.telegram_miniapp import TelegramMiniAppUseCase
from src.application.use_cases.auth.telegram_web_auth import TelegramWebAuthUseCase
from src.application.use_cases.auth.verify_otp import VerifyOtpUseCase
from src.domain.exceptions import InvalidCredentialsError
from src.infrastructure.cache.bot_link_tokens import generate_bot_link_token
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.otp_code_repo import OtpCodeRepository
from src.infrastructure.monitoring.client_context import resolve_web_client_context
from src.infrastructure.monitoring.instrumentation.routes import (
    observe_auth_activation_duration,
    observe_auth_request_duration,
    sync_active_sessions,
    sync_auth_security_posture,
    track_auth_attempt,
    track_auth_bruteforce_event,
    track_auth_error,
    track_auth_flow_event,
    track_auth_password_identifier_event,
    track_auth_security_event,
    track_auth_session_detail,
    track_auth_session_operation,
    track_email_verification,
    track_first_login_after_activation,
    track_magic_link_request,
    track_password_reset,
    track_registration,
    track_registration_funnel_step,
)
from src.infrastructure.oauth.telegram import TelegramOAuthProvider
from src.infrastructure.remnawave.adapters import (
    RemnawaveUserAdapter,
    get_remnawave_adapter,
)
from src.infrastructure.tasks.email_task_dispatcher import (
    EmailTaskDispatcher,
    get_email_dispatcher,
)
from src.presentation.api.v1.auth.cookies import clear_auth_cookies, set_auth_cookies
from src.presentation.api.v1.auth.schemas import (
    AdminUserResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    DeleteAccountResponse,
    DeviceSessionListResponse,
    DeviceSessionResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    GenerateLoginLinkRequest,
    GenerateLoginLinkResponse,
    LoginRequest,
    LoginResponse,
    LogoutAllResponse,
    LogoutRequest,
    MagicLinkRequest,
    MagicLinkResponse,
    MagicLinkVerifyOtpRequest,
    MagicLinkVerifyRequest,
    MagicLinkVerifyResponse,
    RefreshTokenRequest,
    ResendOtpRequest,
    ResendOtpResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    RevokeDeviceResponse,
    TelegramBotLinkRequest,
    TelegramBotLinkResponse,
    TelegramMiniAppRequest,
    TelegramMiniAppResponse,
    TelegramWebLoginRequest,
    TelegramWebLoginResponse,
    TokenResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from src.presentation.api.v1.auth.session_tokens import store_refresh_token
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_auth_service
from src.presentation.dependencies.telegram_rate_limit import (
    GenerateLinkRateLimit,
    TelegramBotLinkRateLimit,
    TelegramMiniAppRateLimit,
    TelegramWebLoginRateLimit,
)
from src.shared.security.fingerprint import generate_client_fingerprint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _resolve_locale(*, user: AdminUserModel | None = None, fallback: str | None = None) -> str:
    if fallback:
        return fallback
    if user and user.language:
        return user.language
    return "unknown"


def _resolve_password_identifier_type(identifier: str) -> str:
    normalized_identifier = identifier.strip().lower()
    return "email" if "@" in normalized_identifier else "username"


def _lockout_tier_from_remaining(remaining_seconds: int | None, permanent: bool) -> str:
    if permanent:
        return "permanent"
    if not remaining_seconds:
        return "tier_1_30s"
    if remaining_seconds >= 1800:
        return "tier_3_30m"
    if remaining_seconds >= 300:
        return "tier_2_5m"
    return "tier_1_30s"


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"description": "Invalid credentials"},
        422: {"description": "Validation error"},
        423: {"description": "Account locked"},
    },
)
async def login(
    request: LoginRequest,
    http_request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    redis_client: redis.Redis = Depends(get_redis),
) -> LoginResponse:
    """Authenticate user and return access and refresh tokens.

    Security:
    - Brute force protection with progressive lockout
    - Constant-time response to prevent user enumeration
    """
    started_at = perf_counter()
    identifier = request.login_or_email.lower()
    password_identifier_type = _resolve_password_identifier_type(request.login_or_email)
    client_context = resolve_web_client_context(
        http_request.headers.get("User-Agent"),
        http_request.headers.get("sec-ch-ua-mobile"),
    )
    protection = LoginProtectionService(redis_client)

    # Check if account is locked (HIGH-1)
    try:
        await protection.check_and_raise_if_locked(identifier)
    except AccountLockedException as e:
        track_auth_attempt(method="password", success=False)
        track_auth_error("account_locked")
        track_auth_password_identifier_event(
            channel="web",
            identifier_type=password_identifier_type,
            step="login",
            client_context=client_context,
            status="failure",
        )
        track_auth_flow_event(
            channel="web",
            method="password",
            provider="native",
            locale="unknown",
            client_context=client_context,
            step="login",
            status="failure",
        )
        track_auth_bruteforce_event(
            channel="web",
            identifier_type=password_identifier_type,
            outcome="blocked_locked_account",
            lockout_tier=_lockout_tier_from_remaining(e.remaining_seconds, e.permanent),
        )
        await sync_auth_security_posture(db, redis_client)
        track_auth_security_event(
            channel="web",
            method="password",
            provider="native",
            locale="unknown",
            error_type="account_locked",
        )
        observe_auth_request_duration("password", started_at)
        logger.warning(
            "Login attempt on locked account",
            extra={"identifier": identifier, "permanent": e.permanent},
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(e),
        )

    user_repo = AdminUserRepository(db)
    use_case = LoginUseCase(
        user_repo=user_repo,
        auth_service=auth_service,
        session=db,
    )

    # Constant-time base delay to prevent timing attacks (HIGH-1)
    min_response_time = 0.1  # 100ms minimum

    # MED-002: Generate client fingerprint for token device binding
    fingerprint = generate_client_fingerprint(http_request)

    try:
        result = await use_case.execute(
            login_or_email=request.login_or_email,
            password=request.password,
            client_fingerprint=fingerprint,
            client_ip=_get_client_ip(http_request),
            user_agent=http_request.headers.get("User-Agent"),
        )
    except Exception as e:
        # Record failed attempt
        logger.warning("Login attempt failed: %s", e)
        protection_result = await protection.record_failed_attempt(identifier)
        await db.commit()

        # Track failed auth attempt metric
        track_auth_attempt(method="password", success=False)
        track_auth_error("invalid_credentials")
        track_auth_password_identifier_event(
            channel="web",
            identifier_type=password_identifier_type,
            step="login",
            client_context=client_context,
            status="failure",
        )
        track_auth_flow_event(
            channel="web",
            method="password",
            provider="native",
            locale="unknown",
            client_context=client_context,
            step="login",
            status="failure",
        )
        track_auth_bruteforce_event(
            channel="web",
            identifier_type=password_identifier_type,
            outcome="failed_attempt",
            lockout_tier=protection_result.lockout_tier,
        )
        if protection_result.lockout_applied:
            track_auth_bruteforce_event(
                channel="web",
                identifier_type=password_identifier_type,
                outcome="permanent_lockout" if protection_result.lockout_tier == "permanent" else "temporary_lockout",
                lockout_tier=protection_result.lockout_tier,
            )
        await sync_auth_security_posture(db, redis_client)
        track_auth_security_event(
            channel="web",
            method="password",
            provider="native",
            locale="unknown",
            error_type="invalid_credentials",
        )

        # Ensure constant response time (LOW-002: use asyncio.sleep instead of blocking time.sleep)
        elapsed = perf_counter() - started_at
        if elapsed < min_response_time:
            # Use asyncio.sleep for non-blocking delay with random jitter
            jitter = secrets.randbelow(50) / 1000  # 0-50ms random jitter
            await asyncio.sleep(min_response_time - elapsed + jitter)

        observe_auth_request_duration("password", started_at)
        logger.warning(
            "Failed login attempt",
            extra={"identifier": identifier, "attempts": protection_result.attempts},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # Successful login - reset attempts
    previous_attempts = await protection.reset_on_success(identifier)

    # Track successful auth attempt metric
    track_auth_attempt(method="password", success=True)
    user = await user_repo.get_by_login_or_email(request.login_or_email)
    locale = _resolve_locale(user=user)
    track_auth_password_identifier_event(
        channel="web",
        identifier_type=password_identifier_type,
        step="login",
        client_context=client_context,
        status="success",
    )
    track_auth_flow_event(
        channel="web",
        method="password",
        provider="native",
        locale=locale,
        client_context=client_context,
        step="login",
        status="success",
    )
    if previous_attempts > 0:
        track_auth_bruteforce_event(
            channel="web",
            identifier_type=password_identifier_type,
            outcome="reset_after_success",
            lockout_tier="none",
        )
    if result.get("is_first_username_only_login"):
        track_first_login_after_activation("password")
        track_auth_password_identifier_event(
            channel="web",
            identifier_type="username",
            step="first_successful_login",
            client_context=client_context,
            status="success",
        )
        track_auth_flow_event(
            channel="web",
            method="password",
            provider="native",
            locale=locale,
            client_context=client_context,
            step="first_successful_login",
            status="success",
        )

    if result["requires_2fa"]:
        track_auth_flow_event(
            channel="web",
            method="password",
            provider="native",
            locale=locale,
            client_context=client_context,
            step="2fa_required",
            status="success",
        )
    else:
        track_auth_flow_event(
            channel="web",
            method="password",
            provider="native",
            locale=locale,
            client_context=client_context,
            step="session_started",
            status="success",
        )
        track_auth_password_identifier_event(
            channel="web",
            identifier_type=password_identifier_type,
            step="session_started",
            client_context=client_context,
            status="success",
        )
        set_auth_cookies(response, result["access_token"], result["refresh_token"])
        await sync_active_sessions(db)

    await sync_auth_security_posture(db, redis_client)
    observe_auth_request_duration("password", started_at)

    return LoginResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
        requires_2fa=result["requires_2fa"],
        tfa_token=result["tfa_token"],
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={401: {"description": "Invalid or expired refresh token"}},
)
async def refresh_token(
    request: RefreshTokenRequest,
    http_request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Refresh access token using refresh token.

    SEC-01: Accepts refresh_token from request body (mobile) or httpOnly cookie (web).
    MED-002: Validates device fingerprint when ENFORCE_TOKEN_BINDING is enabled.
    """
    started_at = perf_counter()
    # SEC-01: Resolve refresh token from body or cookie
    token = request.refresh_token
    if not token:
        token = http_request.cookies.get("refresh_token")
    if not token:
        track_auth_error("expired_token")
        track_auth_session_operation("refresh", "missing_token")
        track_auth_session_detail(
            channel="web",
            method="session",
            operation="refresh",
            status="missing_token",
            reason="missing_token",
        )
        track_auth_security_event(
            channel="web",
            method="session",
            provider="native",
            locale="unknown",
            error_type="expired_token",
        )
        observe_auth_request_duration("refresh_token", started_at)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not provided",
        )

    # MED-002: Generate client fingerprint for token binding validation
    fingerprint = generate_client_fingerprint(http_request)

    use_case = RefreshTokenUseCase(
        auth_service=auth_service,
        session=db,
    )

    try:
        result = await use_case.execute(
            refresh_token=token,
            client_fingerprint=fingerprint,
            client_ip=_get_client_ip(http_request),
            user_agent=http_request.headers.get("User-Agent"),
        )
    except InvalidCredentialsError as exc:
        track_auth_error("expired_token")
        track_auth_session_operation("refresh", "failure")
        track_auth_session_detail(
            channel="web",
            method="session",
            operation="refresh",
            status="failure",
            reason="expired_token",
        )
        track_auth_security_event(
            channel="web",
            method="session",
            provider="native",
            locale="unknown",
            error_type="expired_token",
        )
        observe_auth_request_duration("refresh_token", started_at)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc

    set_auth_cookies(response, result["access_token"], result["refresh_token"])
    await sync_active_sessions(db)
    track_auth_session_operation("refresh", "success")
    track_auth_session_detail(
        channel="web",
        method="session",
        operation="refresh",
        status="success",
        reason="none",
    )
    observe_auth_request_duration("refresh_token", started_at)

    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: LogoutRequest,
    http_request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Logout user by invalidating refresh token and clearing auth cookies.

    SEC-01: Accepts refresh_token from request body (mobile) or httpOnly cookie (web).
    """
    # SEC-01: Resolve refresh token from body or cookie
    token = request.refresh_token
    if not token:
        token = http_request.cookies.get("refresh_token")

    if token:
        use_case = LogoutUseCase(session=db)
        await use_case.execute(refresh_token=token)
        await sync_active_sessions(db)
        track_auth_session_operation("logout", "success")
        track_auth_session_detail(
            channel="web",
            method="session",
            operation="logout",
            status="success",
            reason="none",
        )
    else:
        track_auth_session_operation("logout", "missing_token")
        track_auth_session_detail(
            channel="web",
            method="session",
            operation="logout",
            status="missing_token",
            reason="missing_token",
        )

    clear_auth_cookies(response)
    return None


@router.post(
    "/logout-all",
    response_model=LogoutAllResponse,
    responses={401: {"description": "Not authenticated"}},
)
async def logout_all_devices(
    response: Response,
    current_user=Depends(get_current_active_user),
    redis_client: redis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> LogoutAllResponse:
    """Logout from all devices by revoking all user tokens (HIGH-6).

    Revokes all access and refresh tokens for the current user.
    """
    logout_use_case = LogoutUseCase(session=db)
    refresh_sessions_revoked = await logout_use_case.execute_all(current_user.id)

    revocation_service = JWTRevocationService(redis_client)
    revoked_count = await revocation_service.revoke_all_user_tokens(str(current_user.id))
    sessions_revoked = max(refresh_sessions_revoked, revoked_count)
    await sync_active_sessions(db)
    track_auth_session_operation("logout_all", "success")
    track_auth_session_detail(
        channel="web",
        method="session",
        operation="logout_all",
        status="success",
        reason="none",
        amount=max(sessions_revoked, 1),
    )

    clear_auth_cookies(response)

    logger.info(
        "User logged out from all devices",
        extra={
            "user_id": str(current_user.id),
            "sessions_revoked": sessions_revoked,
            "refresh_sessions_revoked": refresh_sessions_revoked,
            "jwt_tokens_revoked": revoked_count,
        },
    )

    return LogoutAllResponse(
        message="All sessions terminated",
        sessions_revoked=sessions_revoked,
    )


@router.get(
    "/me",
    response_model=AdminUserResponse,
    responses={401: {"description": "Not authenticated"}},
)
@router.get(
    "/session",
    response_model=AdminUserResponse,
    include_in_schema=False,
)
@router.get(
    "/me/",
    response_model=AdminUserResponse,
    include_in_schema=False,
)
@router.get(
    "/session/",
    response_model=AdminUserResponse,
    include_in_schema=False,
)
async def get_me(
    current_user=Depends(get_current_active_user),
) -> AdminUserResponse:
    """Get current authenticated user information."""
    return AdminUserResponse(
        id=current_user.id,
        login=current_user.login,
        email=current_user.email,
        role=current_user.role,
        telegram_id=current_user.telegram_id,
        is_active=current_user.is_active,
        is_email_verified=current_user.is_email_verified,
        created_at=current_user.created_at,
    )


@router.delete(
    "/me",
    response_model=DeleteAccountResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "User not found"},
    },
)
@router.delete(
    "/me/",
    response_model=DeleteAccountResponse,
    include_in_schema=False,
)
async def delete_account(
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> DeleteAccountResponse:
    """Soft-delete the current user's account (FEAT-03).

    Sets is_active=False and deleted_at, then revokes all refresh tokens
    and JWT access tokens. The user will be immediately logged out of all
    devices.
    """
    user_repo = AdminUserRepository(db)
    use_case = DeleteAccountUseCase(
        user_repo=user_repo,
        session=db,
        redis_client=redis_client,
    )

    await use_case.execute(current_user.id)

    logger.info(
        "Account deleted by user",
        extra={"user_id": str(current_user.id)},
    )

    return DeleteAccountResponse()


@router.post(
    "/verify-otp",
    response_model=VerifyOtpResponse,
    responses={
        400: {"description": "Invalid or expired OTP code"},
        429: {"description": "Too many attempts"},
    },
)
@router.post(
    "/verify-email",
    response_model=VerifyOtpResponse,
    responses={
        400: {"description": "Invalid or expired OTP code"},
        429: {"description": "Too many attempts"},
    },
)
async def verify_otp(
    request: VerifyOtpRequest,
    http_request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    remnawave_adapter: RemnawaveUserAdapter = Depends(get_remnawave_adapter),
) -> VerifyOtpResponse:
    """
    Verify OTP code for email verification.

    On success:
    1. Activates user account
    2. Creates user in Remnawave VPN backend
    3. Returns access/refresh tokens (auto-login)

    Aliases:
    - POST /auth/verify-otp (primary)
    - POST /auth/verify-email (mobile compatibility)
    """
    started_at = perf_counter()
    client_context = resolve_web_client_context(
        http_request.headers.get("User-Agent"),
        http_request.headers.get("sec-ch-ua-mobile"),
    )
    user_repo = AdminUserRepository(db)
    otp_repo = OtpCodeRepository(db)
    otp_service = OtpService(otp_repo)

    use_case = VerifyOtpUseCase(
        user_repo=user_repo,
        auth_service=auth_service,
        otp_service=otp_service,
        session=db,
        remnawave_gateway=remnawave_adapter,
    )

    result = await use_case.execute(
        email=request.email,
        code=request.code,
        client_fingerprint=generate_client_fingerprint(http_request),
        client_ip=_get_client_ip(http_request),
        user_agent=http_request.headers.get("User-Agent"),
    )

    if not result.success:
        expired = result.error_code == "OTP_EXPIRED"
        track_email_verification(success=False, expired=expired)
        track_auth_flow_event(
            channel="web",
            method="email_verification",
            provider="otp",
            locale="unknown",
            client_context=client_context,
            step="email_verified",
            status="expired" if expired else "failure",
        )
        if result.error_code == "OTP_EXHAUSTED":
            track_auth_error("rate_limited")
            track_auth_security_event(
                channel="web",
                method="email_verification",
                provider="otp",
                locale="unknown",
                error_type="rate_limited",
            )
        elif result.error_code != "ALREADY_VERIFIED":
            track_auth_error("invalid_otp")
            track_auth_security_event(
                channel="web",
                method="email_verification",
                provider="otp",
                locale="unknown",
                error_type="invalid_otp",
            )
        observe_auth_request_duration("email_verification", started_at)

        status_code = (
            status.HTTP_429_TOO_MANY_REQUESTS if result.error_code == "OTP_EXHAUSTED" else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail={
                "detail": result.message,
                "code": result.error_code,
                "attempts_remaining": result.attempts_remaining,
            },
        )

    track_email_verification(success=True)
    track_registration_funnel_step("email_verified")
    track_registration_funnel_step("activated")
    track_first_login_after_activation("email_verification")

    # Get user for response
    user = await user_repo.get_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User not found after verification"
        )

    locale = _resolve_locale(user=user)
    track_auth_flow_event(
        channel="web",
        method="email_verification",
        provider="otp",
        locale=locale,
        client_context=client_context,
        step="email_verified",
    )
    track_auth_flow_event(
        channel="web",
        method="email_verification",
        provider="otp",
        locale=locale,
        client_context=client_context,
        step="activated",
    )
    track_auth_flow_event(
        channel="web",
        method="email_verification",
        provider="otp",
        locale=locale,
        client_context=client_context,
        step="first_successful_login",
    )
    track_auth_flow_event(
        channel="web",
        method="email_verification",
        provider="otp",
        locale=locale,
        client_context=client_context,
        step="session_started",
    )
    observe_auth_activation_duration(
        channel="web",
        method="email_verification",
        locale=locale,
        stage="verify",
        started_at=user.created_at,
    )
    observe_auth_activation_duration(
        channel="web",
        method="email_verification",
        locale=locale,
        stage="first_login",
        started_at=user.created_at,
        ended_at=user.last_login_at,
    )

    if result.access_token and result.refresh_token:
        set_auth_cookies(response, result.access_token, result.refresh_token)

    await sync_active_sessions(db)
    await sync_auth_security_posture(db)
    observe_auth_request_duration("email_verification", started_at)

    return VerifyOtpResponse(
        access_token=result.access_token or "",
        refresh_token=result.refresh_token or "",
        token_type=result.token_type,
        expires_in=result.expires_in,
        user=AdminUserResponse.model_validate(user),
    )


@router.post(
    "/resend-otp",
    response_model=ResendOtpResponse,
    responses={
        429: {"description": "Rate limit exceeded"},
    },
)
@router.post(
    "/resend-verification",
    response_model=ResendOtpResponse,
    responses={
        429: {"description": "Rate limit exceeded"},
    },
)
async def resend_otp(
    request: ResendOtpRequest,
    db: AsyncSession = Depends(get_db),
    email_dispatcher: EmailTaskDispatcher = Depends(get_email_dispatcher),
) -> ResendOtpResponse:
    """
    Resend OTP verification code.

    Uses Brevo (secondary provider) for resend requests.
    Rate limited to 3 resends per hour per email.

    Aliases:
    - POST /auth/resend-otp (primary)
    - POST /auth/resend-verification (mobile compatibility)
    """
    user_repo = AdminUserRepository(db)
    otp_repo = OtpCodeRepository(db)
    otp_service = OtpService(otp_repo)

    use_case = ResendOtpUseCase(
        user_repo=user_repo,
        otp_service=otp_service,
        email_dispatcher=email_dispatcher,
    )

    result = await use_case.execute(email=request.email, locale=request.locale)

    if not result.success and result.error_code == "RATE_LIMITED":
        track_auth_security_event(
            channel="web",
            method="email_verification",
            provider="otp",
            locale=request.locale,
            error_type="rate_limited",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "detail": result.message,
                "code": result.error_code,
                "next_resend_available_at": result.next_resend_available_at.isoformat()
                if result.next_resend_available_at
                else None,
            },
        )

    if not result.success and result.error_code == "ALREADY_VERIFIED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "detail": result.message,
                "code": result.error_code,
            },
        )

    if result.success:
        track_auth_flow_event(
            channel="web",
            method="password",
            provider="native",
            locale=request.locale,
            step="email_sent",
            status="success",
        )

    return ResendOtpResponse(
        message=result.message or "Verification code sent.",
        resends_remaining=result.resends_remaining,
        next_resend_available_at=result.next_resend_available_at,
    )


@router.post(
    "/magic-link",
    response_model=MagicLinkResponse,
    responses={429: {"description": "Rate limit exceeded"}},
)
async def request_magic_link(
    request: MagicLinkRequest,
    http_request: Request,
    redis_client: redis.Redis = Depends(get_redis),
    email_dispatcher: EmailTaskDispatcher = Depends(get_email_dispatcher),
) -> MagicLinkResponse:
    """Request a magic link for passwordless login.

    Sends a magic link to any email address. If the user doesn't exist,
    a new account will be created when the link is verified.
    """
    started_at = perf_counter()
    service = MagicLinkService(redis_client)

    # Normalize email to lowercase
    email = request.email.strip().lower()

    try:
        # Detect resend: if rate counter > 0, this is not the first request
        rate_key = f"{MagicLinkService.RATE_LIMIT_PREFIX}{email}"
        current_count = await redis_client.get(rate_key)
        is_resend = current_count is not None and int(current_count) > 0

        token, otp_code = await service.generate(
            email=email,
            ip_address=_get_client_ip(http_request),
            locale=request.locale,
        )
        # Dispatch magic link email
        try:
            await email_dispatcher.dispatch_magic_link_email(
                email=email,
                token=token,
                otp_code=otp_code,
                locale=request.locale,
                is_resend=is_resend,
                channel="web",
            )
        except Exception as e:
            logger.exception("Failed to dispatch magic link email: %s", e)
            track_magic_link_request("error")
            track_auth_flow_event(
                channel="web",
                method="magic_link",
                provider="email",
                locale=request.locale,
                step="magic_link_requested",
                status="error",
            )
        else:
            track_magic_link_request("sent")
            track_auth_flow_event(
                channel="web",
                method="magic_link",
                provider="email",
                locale=request.locale,
                step="magic_link_requested",
                status="success",
            )
    except RateLimitExceededError:
        track_magic_link_request("rate_limited")
        track_auth_error("rate_limited")
        track_auth_flow_event(
            channel="web",
            method="magic_link",
            provider="email",
            locale=request.locale,
            step="magic_link_requested",
            status="rate_limited",
        )
        track_auth_security_event(
            channel="web",
            method="magic_link",
            provider="email",
            locale=request.locale,
            error_type="rate_limited",
        )
        observe_auth_request_duration("magic_link_request", started_at)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    observe_auth_request_duration("magic_link_request", started_at)
    return MagicLinkResponse()


@router.post(
    "/magic-link/verify",
    response_model=MagicLinkVerifyResponse,
    responses={400: {"description": "Invalid or expired token"}},
)
async def verify_magic_link(
    request: MagicLinkVerifyRequest,
    http_request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    auth_service: AuthService = Depends(get_auth_service),
) -> MagicLinkVerifyResponse:
    """Verify magic link token and return JWT tokens with user data.

    If user doesn't exist, creates a new account with verified email.
    """
    started_at = perf_counter()
    client_context = resolve_web_client_context(
        http_request.headers.get("User-Agent"),
        http_request.headers.get("sec-ch-ua-mobile"),
    )
    service = MagicLinkService(redis_client)
    payload = await service.validate_and_consume(request.token)

    if not payload:
        track_auth_attempt(method="magic_link", success=False)
        track_auth_error("expired_token")
        track_auth_flow_event(
            channel="web",
            method="magic_link",
            provider="email",
            locale="unknown",
            client_context=client_context,
            step="login",
            status="failure",
        )
        track_auth_security_event(
            channel="web",
            method="magic_link",
            provider="email",
            locale="unknown",
            error_type="expired_token",
        )
        observe_auth_request_duration("magic_link", started_at)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired magic link token.",
        )

    email = payload["email"]
    user_repo = AdminUserRepository(db)
    user = await user_repo.get_by_email(email)
    payload_locale = payload.get("locale") if isinstance(payload, dict) else None
    is_new_user = user is None

    if is_new_user:
        # Auto-register: create user with verified email
        password_hash = await auth_service.hash_password(secrets.token_urlsafe(32))
        user = AdminUserModel(
            login=email.split("@")[0],
            email=email,
            password_hash=password_hash,
            role="viewer",
            language=payload_locale or "en-EN",
            is_active=True,
            is_email_verified=True,
        )
        user = await user_repo.create(user)
        # Track registration for new users
        track_registration(method="email")
        track_email_verification(success=True)
        track_first_login_after_activation("magic_link")

    locale = _resolve_locale(user=user, fallback=payload_locale)

    # Issue JWT tokens
    access_token, _, access_exp = auth_service.create_access_token(
        subject=str(user.id),
        role=user.role if isinstance(user.role, str) else user.role.value,
    )
    fingerprint = generate_client_fingerprint(http_request)
    refresh_token, _, refresh_exp = auth_service.create_refresh_token(subject=str(user.id), fingerprint=fingerprint)
    expires_in = int((access_exp - datetime.now(UTC)).total_seconds())
    await store_refresh_token(
        db,
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=refresh_exp,
        device_id=fingerprint,
        ip_address=_get_client_ip(http_request),
        user_agent=http_request.headers.get("User-Agent"),
    )

    # Track successful magic link auth
    track_auth_attempt(method="magic_link", success=True)
    track_auth_flow_event(
        channel="web",
        method="magic_link",
        provider="email",
        locale=locale,
        client_context=client_context,
        step="login",
        status="success",
    )
    track_auth_flow_event(
        channel="web",
        method="magic_link",
        provider="email",
        locale=locale,
        client_context=client_context,
        step="session_started",
        status="success",
    )
    if is_new_user and payload.get("created_at"):
        created_at = datetime.fromisoformat(payload["created_at"])
        track_auth_flow_event(
            channel="web",
            method="magic_link",
            provider="email",
            locale=locale,
            client_context=client_context,
            step="registered",
        )
        track_auth_flow_event(
            channel="web",
            method="magic_link",
            provider="email",
            locale=locale,
            client_context=client_context,
            step="email_verified",
        )
        track_auth_flow_event(
            channel="web",
            method="magic_link",
            provider="email",
            locale=locale,
            client_context=client_context,
            step="activated",
        )
        track_auth_flow_event(
            channel="web",
            method="magic_link",
            provider="email",
            locale=locale,
            client_context=client_context,
            step="first_successful_login",
        )
        observe_auth_activation_duration(
            channel="web",
            method="magic_link",
            locale=locale,
            stage="first_login",
            started_at=created_at,
        )

    set_auth_cookies(response, access_token, refresh_token)
    await sync_active_sessions(db)
    await sync_auth_security_posture(db, redis_client)
    observe_auth_request_duration("magic_link", started_at)

    return MagicLinkVerifyResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=AdminUserResponse.model_validate(user),
    )


@router.post(
    "/magic-link/verify-otp",
    response_model=MagicLinkVerifyResponse,
    responses={400: {"description": "Invalid or expired OTP code"}},
)
async def verify_magic_link_otp(
    request: MagicLinkVerifyOtpRequest,
    http_request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    auth_service: AuthService = Depends(get_auth_service),
) -> MagicLinkVerifyResponse:
    """Verify magic link via 6-digit OTP code and return JWT tokens with user data.

    Alternative to clicking the magic link URL. The user enters the OTP code
    from the email instead.

    If user doesn't exist, creates a new account with verified email.
    """
    started_at = perf_counter()
    client_context = resolve_web_client_context(
        http_request.headers.get("User-Agent"),
        http_request.headers.get("sec-ch-ua-mobile"),
    )
    service = MagicLinkService(redis_client)
    email = request.email.strip().lower()
    payload = await service.validate_otp(email=email, code=request.code)

    if not payload:
        track_auth_attempt(method="magic_link_otp", success=False)
        track_auth_error("invalid_otp")
        track_auth_flow_event(
            channel="web",
            method="magic_link_otp",
            provider="email",
            locale="unknown",
            client_context=client_context,
            step="login",
            status="failure",
        )
        track_auth_security_event(
            channel="web",
            method="magic_link_otp",
            provider="email",
            locale="unknown",
            error_type="invalid_otp",
        )
        observe_auth_request_duration("magic_link_otp", started_at)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code.",
        )

    payload_email = payload["email"]
    user_repo = AdminUserRepository(db)
    user = await user_repo.get_by_email(payload_email)
    payload_locale = payload.get("locale") if isinstance(payload, dict) else None
    is_new_user = user is None

    if is_new_user:
        # Auto-register: create user with verified email
        password_hash = await auth_service.hash_password(secrets.token_urlsafe(32))
        user = AdminUserModel(
            login=payload_email.split("@")[0],
            email=payload_email,
            password_hash=password_hash,
            role="viewer",
            language=payload_locale or "en-EN",
            is_active=True,
            is_email_verified=True,
        )
        user = await user_repo.create(user)

        # Track registration for new users
        track_registration(method="email")
        track_email_verification(success=True)
        track_first_login_after_activation("magic_link")

    locale = _resolve_locale(user=user, fallback=payload_locale)

    # Issue JWT tokens
    access_token, _, access_exp = auth_service.create_access_token(
        subject=str(user.id),
        role=user.role if isinstance(user.role, str) else user.role.value,
    )
    fingerprint = generate_client_fingerprint(http_request)
    refresh_token, _, refresh_exp = auth_service.create_refresh_token(subject=str(user.id), fingerprint=fingerprint)
    expires_in = int((access_exp - datetime.now(UTC)).total_seconds())

    await store_refresh_token(
        db,
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=refresh_exp,
        device_id=fingerprint,
        ip_address=_get_client_ip(http_request),
        user_agent=http_request.headers.get("User-Agent"),
    )

    # Track successful magic link OTP auth
    track_auth_attempt(method="magic_link_otp", success=True)
    track_auth_flow_event(
        channel="web",
        method="magic_link_otp",
        provider="email",
        locale=locale,
        client_context=client_context,
        step="login",
        status="success",
    )
    track_auth_flow_event(
        channel="web",
        method="magic_link_otp",
        provider="email",
        locale=locale,
        client_context=client_context,
        step="session_started",
        status="success",
    )
    if is_new_user and payload.get("created_at"):
        created_at = datetime.fromisoformat(payload["created_at"])
        track_auth_flow_event(
            channel="web",
            method="magic_link_otp",
            provider="email",
            locale=locale,
            client_context=client_context,
            step="registered",
        )
        track_auth_flow_event(
            channel="web",
            method="magic_link_otp",
            provider="email",
            locale=locale,
            client_context=client_context,
            step="email_verified",
        )
        track_auth_flow_event(
            channel="web",
            method="magic_link_otp",
            provider="email",
            locale=locale,
            client_context=client_context,
            step="activated",
        )
        track_auth_flow_event(
            channel="web",
            method="magic_link_otp",
            provider="email",
            locale=locale,
            client_context=client_context,
            step="first_successful_login",
        )
        observe_auth_activation_duration(
            channel="web",
            method="magic_link_otp",
            locale=locale,
            stage="first_login",
            started_at=created_at,
        )

    set_auth_cookies(response, access_token, refresh_token)
    await sync_active_sessions(db)
    await sync_auth_security_posture(db, redis_client)
    observe_auth_request_duration("magic_link_otp", started_at)

    return MagicLinkVerifyResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=AdminUserResponse.model_validate(user),
    )


@router.post(
    "/telegram/miniapp",
    response_model=TelegramMiniAppResponse,
    responses={
        401: {"description": "Invalid or expired initData"},
    },
)
async def telegram_miniapp_auth(
    request: TelegramMiniAppRequest,
    _rate_limit: TelegramMiniAppRateLimit,
    http_request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    remnawave_adapter: RemnawaveUserAdapter = Depends(get_remnawave_adapter),
) -> TelegramMiniAppResponse:
    """Authenticate via Telegram Mini App initData.

    Validates HMAC-SHA256 signature, checks auth_date freshness,
    auto-registers or auto-logs-in the Telegram user.
    """
    started_at = perf_counter()
    client_context = resolve_web_client_context(
        http_request.headers.get("User-Agent"),
        http_request.headers.get("sec-ch-ua-mobile"),
    )
    user_repo = AdminUserRepository(db)
    telegram_provider = TelegramOAuthProvider()

    use_case = TelegramMiniAppUseCase(
        user_repo=user_repo,
        auth_service=auth_service,
        session=db,
        telegram_provider=telegram_provider,
        remnawave_gateway=remnawave_adapter,
    )

    try:
        result = await use_case.execute(init_data=request.init_data)
    except ValueError as e:
        track_auth_attempt(method="telegram", success=False)
        track_auth_error("invalid_credentials")
        track_auth_flow_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale="unknown",
            client_context=client_context,
            step="login",
            status="failure",
        )
        track_auth_security_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale="unknown",
            error_type="invalid_credentials",
        )
        observe_auth_request_duration("telegram", started_at)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    track_auth_attempt(method="telegram", success=True)
    locale = _resolve_locale(user=result.user)
    track_auth_flow_event(
        channel="web",
        method="telegram",
        provider="telegram",
        locale=locale,
        client_context=client_context,
        step="login",
        status="success",
    )
    track_auth_flow_event(
        channel="web",
        method="telegram",
        provider="telegram",
        locale=locale,
        client_context=client_context,
        step="session_started",
        status="success",
    )

    # Track registration for new users
    if result.is_new_user:
        track_registration(method="telegram")
        track_first_login_after_activation("telegram")
        track_auth_flow_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale=locale,
            client_context=client_context,
            step="registered",
        )
        track_auth_flow_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale=locale,
            client_context=client_context,
            step="activated",
        )
        track_auth_flow_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale=locale,
            client_context=client_context,
            step="first_successful_login",
        )
        observe_auth_activation_duration(
            channel="web",
            method="telegram",
            locale=locale,
            stage="first_login",
            started_at=result.user.created_at,
        )

    if result.access_token and result.refresh_token:
        refresh_payload = auth_service.decode_token(result.refresh_token)
        refresh_exp = datetime.fromtimestamp(refresh_payload["exp"], UTC)
        await store_refresh_token(
            db,
            user_id=result.user.id,
            refresh_token=result.refresh_token,
            expires_at=refresh_exp,
            device_id=generate_client_fingerprint(http_request),
            ip_address=_get_client_ip(http_request),
            user_agent=http_request.headers.get("User-Agent"),
        )
        set_auth_cookies(response, result.access_token, result.refresh_token)

    await sync_active_sessions(db)
    await sync_auth_security_posture(db)
    observe_auth_request_duration("telegram", started_at)

    return TelegramMiniAppResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
        user=AdminUserResponse.model_validate(result.user),
        is_new_user=result.is_new_user,
        requires_2fa=result.requires_2fa,
        tfa_token=result.tfa_token,
    )


@router.post(
    "/telegram/web",
    response_model=TelegramWebLoginResponse,
    responses={
        401: {"description": "Invalid or expired payload"},
    },
)
async def telegram_web_auth(
    request: TelegramWebLoginRequest,
    _rate_limit: TelegramWebLoginRateLimit,
    http_request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    remnawave_adapter: RemnawaveUserAdapter = Depends(get_remnawave_adapter),
) -> TelegramWebLoginResponse:
    """Authenticate via Telegram Web Widget OAuth payload.

    Validates HMAC-SHA256 signature, checks auth_date freshness,
    auto-registers or auto-logs-in the Telegram user.
    """
    started_at = perf_counter()
    client_context = resolve_web_client_context(
        http_request.headers.get("User-Agent"),
        http_request.headers.get("sec-ch-ua-mobile"),
    )
    user_repo = AdminUserRepository(db)
    telegram_service = TelegramAuthService()

    use_case = TelegramWebAuthUseCase(
        user_repo=user_repo,
        auth_service=auth_service,
        session=db,
        telegram_service=telegram_service,
        remnawave_gateway=remnawave_adapter,
    )

    try:
        result = await use_case.execute(payload=request.model_dump())
    except ValueError as e:
        track_auth_attempt(method="telegram", success=False)
        track_auth_error("invalid_credentials")
        track_auth_flow_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale="unknown",
            client_context=client_context,
            step="login",
            status="failure",
        )
        track_auth_security_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale="unknown",
            error_type="invalid_credentials",
        )
        observe_auth_request_duration("telegram", started_at)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    track_auth_attempt(method="telegram", success=True)
    locale = _resolve_locale(user=result.user)
    track_auth_flow_event(
        channel="web",
        method="telegram",
        provider="telegram",
        locale=locale,
        client_context=client_context,
        step="login",
        status="success",
    )
    track_auth_flow_event(
        channel="web",
        method="telegram",
        provider="telegram",
        locale=locale,
        client_context=client_context,
        step="session_started",
        status="success",
    )
    if result.is_new_user:
        track_registration(method="telegram")
        track_first_login_after_activation("telegram")
        track_auth_flow_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale=locale,
            client_context=client_context,
            step="registered",
        )
        track_auth_flow_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale=locale,
            client_context=client_context,
            step="activated",
        )
        track_auth_flow_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale=locale,
            client_context=client_context,
            step="first_successful_login",
        )
        observe_auth_activation_duration(
            channel="web",
            method="telegram",
            locale=locale,
            stage="first_login",
            started_at=result.user.created_at,
        )

    if result.access_token and result.refresh_token:
        refresh_payload = auth_service.decode_token(result.refresh_token)
        refresh_exp = datetime.fromtimestamp(refresh_payload["exp"], UTC)
        await store_refresh_token(
            db,
            user_id=result.user.id,
            refresh_token=result.refresh_token,
            expires_at=refresh_exp,
            device_id=generate_client_fingerprint(http_request),
            ip_address=_get_client_ip(http_request),
            user_agent=http_request.headers.get("User-Agent"),
        )
        set_auth_cookies(response, result.access_token, result.refresh_token)

    await sync_active_sessions(db)
    await sync_auth_security_posture(db)
    observe_auth_request_duration("telegram", started_at)

    return TelegramWebLoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
        user=AdminUserResponse.model_validate(result.user),
        is_new_user=result.is_new_user,
        requires_2fa=result.requires_2fa,
        tfa_token=result.tfa_token,
    )


@router.post(
    "/telegram/bot-link",
    response_model=TelegramBotLinkResponse,
    responses={
        401: {"description": "Invalid or expired login token"},
    },
)
async def telegram_bot_link_auth(
    request: TelegramBotLinkRequest,
    _rate_limit: TelegramBotLinkRateLimit,
    http_request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    redis_client: redis.Redis = Depends(get_redis),
) -> TelegramBotLinkResponse:
    """Authenticate via one-time Telegram bot login link token.

    The bot generates a /login link containing a one-time token.
    This endpoint consumes the token and issues JWT tokens.
    """
    started_at = perf_counter()
    client_context = resolve_web_client_context(
        http_request.headers.get("User-Agent"),
        http_request.headers.get("sec-ch-ua-mobile"),
    )
    user_repo = AdminUserRepository(db)

    use_case = TelegramBotLinkUseCase(
        user_repo=user_repo,
        auth_service=auth_service,
        redis_client=redis_client,
    )

    try:
        result = await use_case.execute(token=request.token)
    except ValueError as e:
        track_auth_attempt(method="telegram", success=False)
        track_auth_error("expired_token")
        track_auth_flow_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale="unknown",
            client_context=client_context,
            step="login",
            status="failure",
        )
        track_auth_security_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale="unknown",
            error_type="expired_token",
        )
        observe_auth_request_duration("telegram", started_at)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    if result.access_token and result.refresh_token:
        refresh_payload = auth_service.decode_token(result.refresh_token)
        refresh_exp = datetime.fromtimestamp(refresh_payload["exp"], UTC)
        await store_refresh_token(
            db,
            user_id=result.user.id,
            refresh_token=result.refresh_token,
            expires_at=refresh_exp,
            device_id=generate_client_fingerprint(http_request),
            ip_address=_get_client_ip(http_request),
            user_agent=http_request.headers.get("User-Agent"),
        )
        set_auth_cookies(response, result.access_token, result.refresh_token)
        await sync_active_sessions(db)
        await sync_auth_security_posture(db, redis_client)

    track_auth_attempt(method="telegram", success=True)
    locale = _resolve_locale(user=result.user)
    track_auth_flow_event(
        channel="web",
        method="telegram",
        provider="telegram",
        locale=locale,
        client_context=client_context,
        step="login",
        status="success",
    )
    track_auth_flow_event(
        channel="web",
        method="telegram",
        provider="telegram",
        locale=locale,
        client_context=client_context,
        step="session_started",
        status="success",
    )
    observe_auth_request_duration("telegram", started_at)

    return TelegramBotLinkResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
        user=AdminUserResponse.model_validate(result.user),
        requires_2fa=result.requires_2fa,
        tfa_token=result.tfa_token,
    )


@router.post(
    "/telegram/generate-login-link",
    response_model=GenerateLoginLinkResponse,
    responses={
        403: {"description": "Insufficient permissions"},
    },
)
async def generate_login_link(
    request: GenerateLoginLinkRequest,
    _rate_limit: GenerateLinkRateLimit,
    current_user=Depends(get_current_active_user),
    redis_client: redis.Redis = Depends(get_redis),
) -> GenerateLoginLinkResponse:
    """Generate a one-time Telegram bot login link (admin/bot-only).

    Creates a token in Redis with 5-minute TTL, returns a deep link URL.
    """
    from src.config.settings import settings as app_settings

    token = await generate_bot_link_token(
        redis_client,
        telegram_id=request.telegram_id,
    )

    bot_username = app_settings.telegram_bot_username
    url = f"https://t.me/{bot_username}?start=login_{token}"
    expires_at = datetime.now(UTC) + timedelta(seconds=300)

    logger.info(
        "Generated login link",
        extra={"telegram_id": request.telegram_id, "admin_user": str(current_user.id)},
    )

    return GenerateLoginLinkResponse(
        token=token,
        url=url,
        expires_at=expires_at,
    )


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    email_dispatcher: EmailTaskDispatcher = Depends(get_email_dispatcher),
) -> ForgotPasswordResponse:
    """Request password reset OTP code.

    Always returns success to prevent email enumeration.
    """
    user_repo = AdminUserRepository(db)
    otp_repo = OtpCodeRepository(db)
    otp_service = OtpService(otp_repo)

    use_case = ForgotPasswordUseCase(
        user_repo=user_repo,
        otp_service=otp_service,
        email_dispatcher=email_dispatcher,
        session=db,
    )

    await use_case.execute(email=request.email, locale=request.locale)
    track_password_reset(operation="request", success=True)

    return ForgotPasswordResponse()


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    responses={
        400: {"description": "Invalid or expired OTP code"},
        429: {"description": "Too many attempts"},
    },
)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> ResetPasswordResponse:
    """Reset password using OTP code from forgot-password email."""
    started_at = perf_counter()
    user_repo = AdminUserRepository(db)
    otp_repo = OtpCodeRepository(db)
    otp_service = OtpService(otp_repo)

    use_case = ResetPasswordUseCase(
        user_repo=user_repo,
        auth_service=auth_service,
        otp_service=otp_service,
        session=db,
    )

    result = await use_case.execute(
        email=request.email,
        code=request.code,
        new_password=request.new_password,
    )

    if not result.success:
        track_password_reset(operation="complete", success=False)
        if result.error_code == "OTP_EXHAUSTED":
            track_auth_error("rate_limited")
            track_auth_security_event(
                channel="web",
                method="password_reset",
                provider="otp",
                locale="unknown",
                error_type="rate_limited",
            )
        else:
            track_auth_error("invalid_otp")
            track_auth_security_event(
                channel="web",
                method="password_reset",
                provider="otp",
                locale="unknown",
                error_type="invalid_otp",
            )
        observe_auth_request_duration("password_reset", started_at)
        status_code = (
            status.HTTP_429_TOO_MANY_REQUESTS if result.error_code == "OTP_EXHAUSTED" else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail={
                "detail": result.message,
                "code": result.error_code,
                "attempts_remaining": result.attempts_remaining,
            },
        )

    track_password_reset(operation="complete", success=True)
    observe_auth_request_duration("password_reset", started_at)
    return ResetPasswordResponse()


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    responses={
        400: {"description": "Invalid password or validation error"},
        401: {"description": "Not authenticated"},
        429: {"description": "Rate limit exceeded (3 requests per hour)"},
    },
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    redis_client: redis.Redis = Depends(get_redis),
) -> ChangePasswordResponse:
    """Change user password after verifying current password.

    Rate limited to 3 requests per hour per user.
    """
    # Rate limiting: 3 requests per hour per user
    rate_limit_key = f"password_change:{current_user.id}"
    rate_limit_window = 3600  # 1 hour in seconds
    rate_limit_max = 3

    # Check current request count
    current_count = await redis_client.get(rate_limit_key)
    if current_count and int(current_count) >= rate_limit_max:
        ttl = await redis_client.ttl(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
        )

    # Execute password change
    use_case = ChangePasswordUseCase(session=db, auth_service=auth_service)

    try:
        await use_case.execute(
            user_id=current_user.id,
            current_password=request.current_password,
            new_password=request.new_password,
        )
    except ValueError as exc:
        logger.warning(
            "Password change failed",
            extra={"user_id": str(current_user.id), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # Increment rate limit counter
    pipe = redis_client.pipeline()
    await pipe.incr(rate_limit_key)
    await pipe.expire(rate_limit_key, rate_limit_window)
    await pipe.execute()

    logger.info(
        "Password changed via API",
        extra={"user_id": str(current_user.id)},
    )

    return ChangePasswordResponse()


@router.get(
    "/devices",
    response_model=DeviceSessionListResponse,
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def list_devices(
    http_request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DeviceSessionListResponse:
    """List all active sessions/devices for the current user (BF2-4).

    Returns device_id, IP address, user agent, last used time, and marks the current session.
    """
    from sqlalchemy import select

    from src.infrastructure.database.models.refresh_token_model import RefreshToken

    # Get the current device fingerprint to mark the current session
    current_fingerprint = generate_client_fingerprint(http_request)

    # Query all active (non-revoked) refresh tokens for the user
    stmt = (
        select(RefreshToken)
        .where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
        .order_by(RefreshToken.last_used_at.desc())
    )

    result = await db.execute(stmt)
    tokens = result.scalars().all()

    # Convert to response format
    devices = []
    for token in tokens:
        is_current = token.device_id == current_fingerprint
        devices.append(
            DeviceSessionResponse(
                device_id=token.device_id,
                ip_address=token.ip_address,
                user_agent=token.user_agent,
                last_used_at=token.last_used_at,
                created_at=token.created_at,
                is_current=is_current,
            )
        )

    logger.info(
        "Device list requested",
        extra={"user_id": str(current_user.id), "device_count": len(devices)},
    )

    return DeviceSessionListResponse(
        devices=devices,
        total=len(devices),
    )


@router.delete(
    "/devices/{device_id}",
    response_model=RevokeDeviceResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Device not found"},
    },
)
async def revoke_device(
    device_id: str,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> RevokeDeviceResponse:
    """Revoke a specific device session (remote logout) (BF2-4).

    Revokes all refresh tokens associated with the device and revokes all JWT access tokens for the user.
    """
    from sqlalchemy import select, update

    from src.infrastructure.database.models.refresh_token_model import RefreshToken

    # Find tokens for this device
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == current_user.id,
        RefreshToken.device_id == device_id,
        RefreshToken.revoked_at.is_(None),
    )

    result = await db.execute(stmt)
    tokens = result.scalars().all()

    if not tokens:
        logger.warning(
            "Device revocation attempted for non-existent device",
            extra={"user_id": str(current_user.id), "device_id": device_id},
        )
        track_auth_session_operation("revoke_device", "not_found")
        track_auth_session_detail(
            channel="web",
            method="session",
            operation="revoke_device",
            status="not_found",
            reason="device_not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found or already revoked",
        )

    # Revoke all tokens for this device
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.device_id == device_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )

    await db.commit()
    await sync_active_sessions(db)
    track_auth_session_operation("revoke_device", "success")
    track_auth_session_detail(
        channel="web",
        method="session",
        operation="revoke_device",
        status="success",
        reason="none",
        amount=len(tokens),
    )

    # Also revoke JWT access tokens for this user (they'll need to re-login)
    revocation_service = JWTRevocationService(redis_client)
    await revocation_service.revoke_all_user_tokens(str(current_user.id))

    logger.info(
        "Device session revoked",
        extra={"user_id": str(current_user.id), "device_id": device_id, "tokens_revoked": len(tokens)},
    )

    return RevokeDeviceResponse(
        message="Device session revoked successfully",
        device_id=device_id,
    )
