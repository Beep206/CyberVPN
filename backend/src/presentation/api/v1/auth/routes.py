"""Authentication routes for login, logout, token refresh, OTP verification, and user info."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.otp_service import OtpService
from src.application.use_cases.auth.login import LoginUseCase
from src.application.use_cases.auth.logout import LogoutUseCase
from src.application.use_cases.auth.refresh_token import RefreshTokenUseCase
from src.application.use_cases.auth.resend_otp import ResendOtpUseCase
from src.application.use_cases.auth.verify_otp import VerifyOtpUseCase
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
from src.presentation.api.v1.auth.schemas import (
    AdminUserResponse,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    ResendOtpRequest,
    ResendOtpResponse,
    TokenResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"description": "Invalid credentials"},
        422: {"description": "Validation error"},
    },
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate user and return access and refresh tokens."""
    user_repo = AdminUserRepository(db)

    use_case = LoginUseCase(
        user_repo=user_repo,
        auth_service=auth_service,
        session=db,
    )

    result = await use_case.execute(
        login_or_email=request.login_or_email,
        password=request.password,
    )

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
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Refresh access token using refresh token."""

    use_case = RefreshTokenUseCase(
        auth_service=auth_service,
        session=db,
    )

    result = await use_case.execute(refresh_token=request.refresh_token)

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
        status_code = status.HTTP_429_TOO_MANY_REQUESTS if result.error_code == "OTP_EXHAUSTED" else status.HTTP_400_BAD_REQUEST
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User not found after verification")

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
                "next_resend_available_at": result.next_resend_available_at.isoformat() if result.next_resend_available_at else None,
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
