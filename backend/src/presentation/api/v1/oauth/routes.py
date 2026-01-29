from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.account_linking import AccountLinkingUseCase
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/telegram/authorize")
async def telegram_authorize():
    return {"authorize_url": "https://oauth.telegram.org/auth"}


@router.get("/github/authorize")
async def github_authorize():
    return {"authorize_url": "https://github.com/login/oauth/authorize"}


@router.post("/telegram/callback")
async def telegram_callback(
    code: str,
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    uc = AccountLinkingUseCase(db)
    account = await uc.link_account(
        user_id=user.id, provider="telegram", provider_user_id=code
    )
    return {"status": "linked", "provider": "telegram"}


@router.post("/github/callback")
async def github_callback(
    code: str,
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    uc = AccountLinkingUseCase(db)
    account = await uc.link_account(
        user_id=user.id, provider="github", provider_user_id=code
    )
    return {"status": "linked", "provider": "github"}


@router.delete("/{provider}")
async def unlink_provider(
    provider: str,
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    uc = AccountLinkingUseCase(db)
    await uc.unlink_account(user.id, provider)
    return {"status": "unlinked", "provider": provider}
