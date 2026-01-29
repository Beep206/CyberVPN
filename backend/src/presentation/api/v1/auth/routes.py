"""Authentication routes for login, logout, token refresh, and user info."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.use_cases.auth.login import LoginUseCase
from src.application.use_cases.auth.logout import LogoutUseCase
from src.application.use_cases.auth.refresh_token import RefreshTokenUseCase
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.presentation.api.v1.auth.schemas import (
    LoginRequest,
    TokenResponse,
    AdminUserResponse,
    RefreshTokenRequest,
    LogoutRequest,
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
        created_at=current_user.created_at,
    )
