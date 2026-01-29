from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.two_factor import TwoFactorUseCase
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db

from .schemas import (
    TwoFactorSetupResponse,
    TwoFactorStatusResponse,
    TwoFactorValidateResponse,
    VerifyCodeRequest,
)

router = APIRouter(prefix="/2fa", tags=["two-factor"])


@router.post(
    "/setup",
    response_model=TwoFactorSetupResponse,
    responses={400: {"description": "2FA already enabled"}},
)
async def setup_2fa(
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Set up two-factor authentication for the current user."""
    uc = TwoFactorUseCase(db)
    result = await uc.setup(user.id)
    return result


@router.post(
    "/verify",
    response_model=TwoFactorStatusResponse,
    responses={400: {"description": "Invalid verification code"}},
)
async def verify_2fa(
    body: VerifyCodeRequest,
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify 2FA code and enable two-factor authentication."""
    uc = TwoFactorUseCase(db)
    success = await uc.verify_and_enable(user.id, body.code)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    return {"status": "enabled"}


@router.post(
    "/validate",
    response_model=TwoFactorValidateResponse,
    responses={400: {"description": "Validation failed"}},
)
async def validate_2fa(
    body: VerifyCodeRequest,
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate a 2FA code without changing state."""
    uc = TwoFactorUseCase(db)
    valid = await uc.verify_code(user.id, body.code)
    return {"valid": valid}


@router.delete(
    "/disable",
    response_model=TwoFactorStatusResponse,
)
async def disable_2fa(
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable two-factor authentication."""
    uc = TwoFactorUseCase(db)
    await uc.disable(user.id)
    return {"status": "disabled"}
