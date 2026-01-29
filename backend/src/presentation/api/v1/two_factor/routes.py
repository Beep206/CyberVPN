from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.two_factor import TwoFactorUseCase
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db

router = APIRouter(prefix="/2fa", tags=["two-factor"])


class VerifyCodeRequest(BaseModel):
    code: str


@router.post("/setup")
async def setup_2fa(
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    uc = TwoFactorUseCase(db)
    result = await uc.setup(user.id)
    return result


@router.post("/verify")
async def verify_2fa(
    body: VerifyCodeRequest,
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    uc = TwoFactorUseCase(db)
    success = await uc.verify_and_enable(user.id, body.code)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    return {"status": "enabled"}


@router.post("/validate")
async def validate_2fa(
    body: VerifyCodeRequest,
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    uc = TwoFactorUseCase(db)
    valid = await uc.verify_code(user.id, body.code)
    return {"valid": valid}


@router.delete("/disable")
async def disable_2fa(
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    uc = TwoFactorUseCase(db)
    await uc.disable(user.id)
    return {"status": "disabled"}
