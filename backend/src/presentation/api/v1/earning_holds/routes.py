from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.settlement import (
    GetEarningHoldUseCase,
    ListEarningHoldsUseCase,
    ReleaseEarningHoldUseCase,
)
from src.domain.enums import AdminRole, EarningHoldStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import EarningHoldResponse, ReleaseEarningHoldRequest

router = APIRouter(prefix="/earning-holds", tags=["earning-holds"])


def _serialize_hold(model) -> EarningHoldResponse:
    return EarningHoldResponse(
        id=model.id,
        earning_event_id=model.earning_event_id,
        partner_account_id=model.partner_account_id,
        hold_reason_type=model.hold_reason_type,
        hold_status=model.hold_status,
        reason_code=model.reason_code,
        hold_until=model.hold_until,
        released_at=model.released_at,
        released_by_admin_user_id=model.released_by_admin_user_id,
        created_by_admin_user_id=model.created_by_admin_user_id,
        hold_payload=dict(model.hold_payload or {}),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.get("/", response_model=list[EarningHoldResponse])
async def list_earning_holds(
    earning_event_id: UUID | None = Query(None),
    hold_status: EarningHoldStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[EarningHoldResponse]:
    items = await ListEarningHoldsUseCase(db).execute(
        earning_event_id=earning_event_id,
        hold_status=hold_status.value if hold_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_hold(item) for item in items]


@router.get("/{hold_id}", response_model=EarningHoldResponse)
async def get_earning_hold(
    hold_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> EarningHoldResponse:
    item = await GetEarningHoldUseCase(db).execute(hold_id=hold_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Earning hold not found")
    return _serialize_hold(item)


@router.post("/{hold_id}/release", response_model=EarningHoldResponse)
async def release_earning_hold(
    hold_id: UUID,
    payload: ReleaseEarningHoldRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> EarningHoldResponse:
    try:
        item = await ReleaseEarningHoldUseCase(db).execute(
            hold_id=hold_id,
            released_by_admin_user_id=current_admin.id,
            release_reason_code=payload.release_reason_code,
            force=payload.force,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_hold(item)
