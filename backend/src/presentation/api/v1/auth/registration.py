"""User registration route."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.use_cases.auth.register import RegisterUseCase
from src.domain.enums import AdminRole
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.presentation.api.v1.auth.schemas import RegisterRequest, AdminUserResponse
from src.presentation.dependencies.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    """Register a new admin user."""
    user_repo = AdminUserRepository(db)
    auth_service = AuthService()

    use_case = RegisterUseCase(
        user_repo=user_repo,
        auth_service=auth_service,
    )

    user = await use_case.execute(
        login=request.login,
        email=request.email,
        password=request.password,
        role=AdminRole.VIEWER,
    )

    return AdminUserResponse(
        id=user.id,
        login=user.login,
        email=user.email,
        role=AdminRole(user.role),
        telegram_id=user.telegram_id,
        is_active=user.is_active,
        created_at=user.created_at,
    )
