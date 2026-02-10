"""Invite code API routes.

Provides:
- ``POST /invites/redeem``        -- mobile user redeems an invite code
- ``GET  /invites/my``            -- mobile user lists their invite codes
- ``POST /admin/invite-codes``    -- admin creates invite codes
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService
from src.application.use_cases.invites.admin_create_invite import AdminCreateInviteUseCase
from src.application.use_cases.invites.redeem_invite import RedeemInviteUseCase
from src.domain.enums import AdminRole
from src.domain.exceptions import (
    InviteCodeAlreadyUsedError,
    InviteCodeExpiredError,
    InviteCodeNotFoundError,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import AdminCreateInviteRequest, InviteCodeResponse, RedeemInviteRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invites", tags=["invites"])


@router.post(
    "/redeem",
    response_model=InviteCodeResponse,
    summary="Redeem an invite code",
    responses={
        404: {"description": "Invite code not found"},
        409: {"description": "Invite code already used"},
        410: {"description": "Invite code expired"},
    },
)
async def redeem_invite(
    body: RedeemInviteRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> InviteCodeResponse:
    """Redeem an invite code for the authenticated mobile user."""
    repo = InviteCodeRepository(db)
    use_case = RedeemInviteUseCase(repo)

    try:
        result = await use_case.execute(code=body.code, user_id=user_id)
    except InviteCodeNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite code not found") from None
    except InviteCodeAlreadyUsedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invite code already used") from None
    except InviteCodeExpiredError:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite code expired") from None

    return InviteCodeResponse.model_validate(result)


@router.get(
    "/my",
    response_model=list[InviteCodeResponse],
    summary="List my invite codes",
)
async def list_my_invites(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> list[InviteCodeResponse]:
    """List invite codes owned by the authenticated mobile user."""
    repo = InviteCodeRepository(db)
    invites = await repo.get_by_owner(owner_user_id=user_id, offset=offset, limit=limit)
    return [InviteCodeResponse.model_validate(inv) for inv in invites]


admin_router = APIRouter(prefix="/admin/invite-codes", tags=["invites"])


@admin_router.post(
    "",
    response_model=list[InviteCodeResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Admin: create invite codes",
)
async def admin_create_invites(
    body: AdminCreateInviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> list[InviteCodeResponse]:
    """Create one or more invite codes (admin only)."""
    invite_repo = InviteCodeRepository(db)
    config_repo = SystemConfigRepository(db)
    config_service = ConfigService(config_repo)
    use_case = AdminCreateInviteUseCase(invite_repo=invite_repo, config_service=config_service)

    created = await use_case.execute(
        owner_user_id=body.user_id,
        free_days=body.free_days,
        count=body.count,
        plan_id=body.plan_id,
    )

    return [InviteCodeResponse.model_validate(inv) for inv in created]
