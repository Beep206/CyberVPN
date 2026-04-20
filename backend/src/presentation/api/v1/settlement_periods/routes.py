from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.settlement import (
    CloseSettlementPeriodUseCase,
    CreateSettlementPeriodUseCase,
    GetSettlementPeriodUseCase,
    ListSettlementPeriodsUseCase,
    ReopenSettlementPeriodUseCase,
)
from src.domain.enums import AdminRole, SettlementPeriodStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import CreateSettlementPeriodRequest, SettlementPeriodResponse

router = APIRouter(prefix="/settlement-periods", tags=["settlement-periods"])


def _serialize_period(model) -> SettlementPeriodResponse:
    return SettlementPeriodResponse(
        id=model.id,
        partner_account_id=model.partner_account_id,
        period_key=model.period_key,
        period_status=model.period_status,
        currency_code=model.currency_code,
        window_start=model.window_start,
        window_end=model.window_end,
        closed_at=model.closed_at,
        closed_by_admin_user_id=model.closed_by_admin_user_id,
        reopened_at=model.reopened_at,
        reopened_by_admin_user_id=model.reopened_by_admin_user_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post("/", response_model=SettlementPeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_settlement_period(
    payload: CreateSettlementPeriodRequest,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> SettlementPeriodResponse:
    try:
        item = await CreateSettlementPeriodUseCase(db).execute(
            partner_account_id=payload.partner_account_id,
            period_key=payload.period_key,
            window_start=payload.window_start,
            window_end=payload.window_end,
            currency_code=payload.currency_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_period(item)


@router.get("/", response_model=list[SettlementPeriodResponse])
async def list_settlement_periods(
    partner_account_id: UUID | None = Query(None),
    period_status: SettlementPeriodStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[SettlementPeriodResponse]:
    items = await ListSettlementPeriodsUseCase(db).execute(
        partner_account_id=partner_account_id,
        period_status=period_status.value if period_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_period(item) for item in items]


@router.get("/{settlement_period_id}", response_model=SettlementPeriodResponse)
async def get_settlement_period(
    settlement_period_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> SettlementPeriodResponse:
    item = await GetSettlementPeriodUseCase(db).execute(settlement_period_id=settlement_period_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settlement period not found")
    return _serialize_period(item)


@router.post("/{settlement_period_id}/close", response_model=SettlementPeriodResponse)
async def close_settlement_period(
    settlement_period_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> SettlementPeriodResponse:
    try:
        item = await CloseSettlementPeriodUseCase(db).execute(
            settlement_period_id=settlement_period_id,
            closed_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_period(item)


@router.post("/{settlement_period_id}/reopen", response_model=SettlementPeriodResponse)
async def reopen_settlement_period(
    settlement_period_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> SettlementPeriodResponse:
    try:
        item = await ReopenSettlementPeriodUseCase(db).execute(
            settlement_period_id=settlement_period_id,
            reopened_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_period(item)
