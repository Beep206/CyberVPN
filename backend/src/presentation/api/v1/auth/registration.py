"""User registration route with OTP email verification."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.otp_service import OtpService
from src.application.use_cases.auth.register import RegisterUseCase
from src.domain.enums import AdminRole
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.otp_code_repo import OtpCodeRepository
from src.infrastructure.tasks.email_task_dispatcher import (
    EmailTaskDispatcher,
    get_email_dispatcher,
)
from src.presentation.api.v1.auth.schemas import RegisterRequest, RegisterResponse
from src.presentation.dependencies.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    email_dispatcher: EmailTaskDispatcher = Depends(get_email_dispatcher),
) -> RegisterResponse:
    """
    Register a new user with email verification.

    Creates user with is_active=False, is_email_verified=False.
    Sends OTP verification email to the provided address.
    User must verify email before logging in.
    """
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
        role=AdminRole.VIEWER,
        locale=request.locale or "en-EN",
    )

    return RegisterResponse(
        id=result.user.id,
        login=result.user.login,
        email=result.user.email or "",
        is_active=result.user.is_active,
        is_email_verified=result.user.is_email_verified,
        message="Registration successful. Please check your email for verification code.",
    )
