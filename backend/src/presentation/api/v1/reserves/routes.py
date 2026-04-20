from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.settlement import (
    CreateReserveUseCase,
    GetReserveUseCase,
    ListReservesUseCase,
    ReleaseReserveUseCase,
)
from src.domain.enums import AdminRole, ReserveStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import CreateReserveRequest, ReleaseReserveRequest, ReserveResponse

router = APIRouter(prefix="/reserves", tags=["reserves"])


def _serialize_reserve(model) -> ReserveResponse:
    return ReserveResponse(
        id=model.id,
        partner_account_id=model.partner_account_id,
        source_earning_event_id=model.source_earning_event_id,
        reserve_scope=model.reserve_scope,
        reserve_reason_type=model.reserve_reason_type,
        reserve_status=model.reserve_status,
        amount=float(model.amount),
        currency_code=model.currency_code,
        reason_code=model.reason_code,
        reserve_payload=dict(model.reserve_payload or {}),
        released_at=model.released_at,
        released_by_admin_user_id=model.released_by_admin_user_id,
        created_by_admin_user_id=model.created_by_admin_user_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post("/", response_model=ReserveResponse, status_code=status.HTTP_201_CREATED)
async def create_reserve(
    payload: CreateReserveRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> ReserveResponse:
    try:
        item = await CreateReserveUseCase(db).execute(
            partner_account_id=payload.partner_account_id,
            amount=payload.amount,
            currency_code=payload.currency_code,
            reserve_scope=payload.reserve_scope.value,
            reserve_reason_type=payload.reserve_reason_type.value,
            source_earning_event_id=payload.source_earning_event_id,
            reason_code=payload.reason_code,
            reserve_payload=payload.reserve_payload,
            created_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_reserve(item)


@router.get("/", response_model=list[ReserveResponse])
async def list_reserves(
    partner_account_id: UUID | None = Query(None),
    source_earning_event_id: UUID | None = Query(None),
    reserve_status: ReserveStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[ReserveResponse]:
    items = await ListReservesUseCase(db).execute(
        partner_account_id=partner_account_id,
        source_earning_event_id=source_earning_event_id,
        reserve_status=reserve_status.value if reserve_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_reserve(item) for item in items]


@router.get("/{reserve_id}", response_model=ReserveResponse)
async def get_reserve(
    reserve_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> ReserveResponse:
    item = await GetReserveUseCase(db).execute(reserve_id=reserve_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserve not found")
    return _serialize_reserve(item)


@router.post("/{reserve_id}/release", response_model=ReserveResponse)
async def release_reserve(
    reserve_id: UUID,
    payload: ReleaseReserveRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> ReserveResponse:
    try:
        item = await ReleaseReserveUseCase(db).execute(
            reserve_id=reserve_id,
            released_by_admin_user_id=current_admin.id,
            release_reason_code=payload.release_reason_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_reserve(item)
