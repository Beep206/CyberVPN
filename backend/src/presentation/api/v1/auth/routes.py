"""Authentication routes with brute force protection (HIGH-1).

Includes device fingerprint support for token binding (MED-002).
"""

import asyncio
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.login_protection import AccountLockedException, LoginProtectionService
from src.application.services.magic_link_service import MagicLinkService, RateLimitExceededError
from src.application.services.otp_service import OtpService
from src.application.use_cases.auth.delete_account import DeleteAccountUseCase
from src.application.use_cases.auth.forgot_password import ForgotPasswordUseCase
from src.application.use_cases.auth.login import LoginUseCase
from src.application.use_cases.auth.logout import LogoutUseCase
from src.application.use_cases.auth.refresh_token import RefreshTokenUseCase
from src.application.use_cases.auth.resend_otp import ResendOtpUseCase
from src.application.use_cases.auth.reset_password import ResetPasswordUseCase
from src.application.use_cases.auth.telegram_bot_link import TelegramBotLinkUseCase
from src.application.use_cases.auth.telegram_miniapp import TelegramMiniAppUseCase
from src.application.use_cases.auth.verify_otp import VerifyOtpUseCase
from src.infrastructure.cache.redis_client import get_redis
from src.shared.security.fingerprint import generate_client_fingerprint

logger = logging.getLogger(__name__)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.otp_code_repo import OtpCodeRepository
from src.infrastructure.remnawave.adapters import (
    RemnawaveUserAdapter,
    get_remnawave_adapter,
)
from src.infrastructure.tasks.email_task_dispatcher import (
    EmailTaskDispatcher,
    get_email_dispatcher,
)
from src.application.services.jwt_revocation_service import JWTRevocationService
from src.infrastructure.oauth.telegram import TelegramOAuthProvider
from src.presentation.api.v1.auth.schemas import (
    AdminUserResponse,
    DeleteAccountResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    GenerateLoginLinkRequest,
    GenerateLoginLinkResponse,
    LoginRequest,
    LogoutAllResponse,
    LogoutRequest,
    MagicLinkRequest,
    MagicLinkResponse,
    MagicLinkVerifyRequest,
    RefreshTokenRequest,
    ResendOtpRequest,
    ResendOtpResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TelegramBotLinkRequest,
    TelegramBotLinkResponse,
    TelegramMiniAppRequest,
    TelegramMiniAppResponse,
    TokenResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from src.infrastructure.cache.bot_link_tokens import generate_bot_link_token
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_auth_service
from src.presentation.dependencies.telegram_rate_limit import (
    GenerateLinkRateLimit,
    TelegramBotLinkRateLimit,
    TelegramMiniAppRateLimit,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"description": "Invalid credentials"},
        422: {"description": "Validation error"},
        423: {"description": "Account locked"},
    },
)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    redis_client: redis.Redis = Depends(get_redis),
) -> TokenResponse:
    """Authenticate user and return access and refresh tokens.

    Security:
    - Brute force protection with progressive lockout
    - Constant-time response to prevent user enumeration
    """
    identifier = request.login_or_email.lower()
    protection = LoginProtectionService(redis_client)

    # Check if account is locked (HIGH-1)
    try:
        await protection.check_and_raise_if_locked(identifier)
    except AccountLockedException as e:
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
    start_time = time.time()
    min_response_time = 0.1  # 100ms minimum

    # MED-002: Generate client fingerprint for token device binding
    fingerprint = generate_client_fingerprint(http_request)

    try:
        result = await use_case.execute(
            login_or_email=request.login_or_email,
            password=request.password,
            client_fingerprint=fingerprint,
        )
    except Exception:
        # Record failed attempt
        attempts = await protection.record_failed_attempt(identifier)

        # Ensure constant response time (LOW-002: use asyncio.sleep instead of blocking time.sleep)
        elapsed = time.time() - start_time
        if elapsed < min_response_time:
            # Use asyncio.sleep for non-blocking delay with random jitter
            jitter = secrets.randbelow(50) / 1000  # 0-50ms random jitter
            await asyncio.sleep(min_response_time - elapsed + jitter)

        logger.warning(
            "Failed login attempt",
            extra={"identifier": identifier, "attempts": attempts},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # Successful login - reset attempts
    await protection.reset_on_success(identifier)

    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={401: {"description": "Invalid or expired refresh token"}},
)
async def refresh_token(
    request: RefreshTokenRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Refresh access token using refresh token.

    MED-002: Validates device fingerprint when ENFORCE_TOKEN_BINDING is enabled.
    """
    # MED-002: Generate client fingerprint for token binding validation
    fingerprint = generate_client_fingerprint(http_request)

    use_case = RefreshTokenUseCase(
        auth_service=auth_service,
        session=db,
    )

    result = await use_case.execute(
        refresh_token=request.refresh_token,
        client_fingerprint=fingerprint,
    )

    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: LogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    """Logout user by invalidating refresh token."""
    use_case = LogoutUseCase(session=db)

    await use_case.execute(refresh_token=request.refresh_token)
    return None


@router.post(
    "/logout-all",
    response_model=LogoutAllResponse,
    responses={401: {"description": "Not authenticated"}},
)
async def logout_all_devices(
    current_user=Depends(get_current_active_user),
    redis_client: redis.Redis = Depends(get_redis),
) -> LogoutAllResponse:
    """Logout from all devices by revoking all user tokens (HIGH-6).

    Revokes all access and refresh tokens for the current user.
    """
    revocation_service = JWTRevocationService(redis_client)
    revoked_count = await revocation_service.revoke_all_user_tokens(str(current_user.id))

    logger.info(
        "User logged out from all devices",
        extra={"user_id": str(current_user.id), "sessions_revoked": revoked_count},
    )

    return LogoutAllResponse(
        message="All sessions terminated",
        sessions_revoked=revoked_count,
    )


@router.get(
    "/me",
    response_model=AdminUserResponse,
    responses={401: {"description": "Not authenticated"}},
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
async def verify_otp(
    request: VerifyOtpRequest,
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
    """
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

    result = await use_case.execute(email=request.email, code=request.code)

    if not result.success:
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

    # Get user for response
    user = await user_repo.get_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User not found after verification"
        )

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
async def resend_otp(
    request: ResendOtpRequest,
    db: AsyncSession = Depends(get_db),
    email_dispatcher: EmailTaskDispatcher = Depends(get_email_dispatcher),
) -> ResendOtpResponse:
    """
    Resend OTP verification code.

    Uses Brevo (secondary provider) for resend requests.
    Rate limited to 3 resends per hour per email.
    """
    user_repo = AdminUserRepository(db)
    otp_repo = OtpCodeRepository(db)
    otp_service = OtpService(otp_repo)

    use_case = ResendOtpUseCase(
        user_repo=user_repo,
        otp_service=otp_service,
        email_dispatcher=email_dispatcher,
    )

    result = await use_case.execute(email=request.email)

    if not result.success and result.error_code == "RATE_LIMITED":
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
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    email_dispatcher: EmailTaskDispatcher = Depends(get_email_dispatcher),
) -> MagicLinkResponse:
    """Request a magic link for passwordless login.

    Always returns success to prevent email enumeration.
    """
    service = MagicLinkService(redis_client)
    user_repo = AdminUserRepository(db)

    try:
        # Check if email is registered (but always return same response)
        user = await user_repo.get_by_email(request.email)
        if user:
            token = await service.generate(
                email=request.email,
                ip_address=_get_client_ip(http_request),
            )
            # Dispatch magic link email
            try:
                await email_dispatcher.dispatch_magic_link_email(
                    email=request.email,
                    token=token,
                )
            except Exception:
                logger.exception("Failed to dispatch magic link email")
    except RateLimitExceededError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    return MagicLinkResponse()


@router.post(
    "/magic-link/verify",
    response_model=TokenResponse,
    responses={400: {"description": "Invalid or expired token"}},
)
async def verify_magic_link(
    request: MagicLinkVerifyRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Verify magic link token and return JWT tokens.

    If user doesn't exist, creates a new account with verified email.
    """
    service = MagicLinkService(redis_client)
    payload = await service.validate_and_consume(request.token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired magic link token.",
        )

    email = payload["email"]
    user_repo = AdminUserRepository(db)
    user = await user_repo.get_by_email(email)

    if not user:
        # Auto-register: create user with verified email
        password_hash = await auth_service.hash_password(secrets.token_urlsafe(32))
        user = AdminUserModel(
            login=email.split("@")[0],
            email=email,
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        user = await user_repo.create(user)

    # Issue JWT tokens
    access_token, _, access_exp = auth_service.create_access_token(
        subject=str(user.id),
        role=user.role if isinstance(user.role, str) else user.role.value,
    )
    refresh_token, _, _ = auth_service.create_refresh_token(subject=str(user.id))
    expires_in = int((access_exp - datetime.now(UTC)).total_seconds())

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
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
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    remnawave_adapter: RemnawaveUserAdapter = Depends(get_remnawave_adapter),
) -> TelegramMiniAppResponse:
    """Authenticate via Telegram Mini App initData.

    Validates HMAC-SHA256 signature, checks auth_date freshness,
    auto-registers or auto-logs-in the Telegram user.
    """
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return TelegramMiniAppResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
        user=AdminUserResponse.model_validate(result.user),
        is_new_user=result.is_new_user,
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
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    redis_client: redis.Redis = Depends(get_redis),
) -> TelegramBotLinkResponse:
    """Authenticate via one-time Telegram bot login link token.

    The bot generates a /login link containing a one-time token.
    This endpoint consumes the token and issues JWT tokens.
    """
    user_repo = AdminUserRepository(db)

    use_case = TelegramBotLinkUseCase(
        user_repo=user_repo,
        auth_service=auth_service,
        redis_client=redis_client,
    )

    try:
        result = await use_case.execute(token=request.token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return TelegramBotLinkResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
        user=AdminUserResponse.model_validate(result.user),
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

    await use_case.execute(email=request.email)

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

    return ResetPasswordResponse()
