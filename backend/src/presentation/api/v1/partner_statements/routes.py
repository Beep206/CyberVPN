from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.settlement import (
    ClosePartnerStatementUseCase,
    CreateStatementAdjustmentUseCase,
    GeneratePartnerStatementUseCase,
    GetPartnerStatementUseCase,
    ListPartnerStatementsUseCase,
    ListStatementAdjustmentsUseCase,
    ReopenPartnerStatementUseCase,
)
from src.domain.enums import AdminRole, PartnerStatementStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    CreateStatementAdjustmentRequest,
    GeneratePartnerStatementRequest,
    PartnerStatementResponse,
    StatementAdjustmentResponse,
)

router = APIRouter(prefix="/partner-statements", tags=["partner-statements"])


def _serialize_statement(model) -> PartnerStatementResponse:
    return PartnerStatementResponse(
        id=model.id,
        partner_account_id=model.partner_account_id,
        settlement_period_id=model.settlement_period_id,
        statement_key=model.statement_key,
        statement_version=model.statement_version,
        statement_status=model.statement_status,
        reopened_from_statement_id=model.reopened_from_statement_id,
        superseded_by_statement_id=model.superseded_by_statement_id,
        currency_code=model.currency_code,
        accrual_amount=float(model.accrual_amount),
        on_hold_amount=float(model.on_hold_amount),
        reserve_amount=float(model.reserve_amount),
        adjustment_net_amount=float(model.adjustment_net_amount),
        available_amount=float(model.available_amount),
        source_event_count=model.source_event_count,
        held_event_count=model.held_event_count,
        active_reserve_count=model.active_reserve_count,
        adjustment_count=model.adjustment_count,
        statement_snapshot=dict(model.statement_snapshot or {}),
        closed_at=model.closed_at,
        closed_by_admin_user_id=model.closed_by_admin_user_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_adjustment(model) -> StatementAdjustmentResponse:
    return StatementAdjustmentResponse(
        id=model.id,
        partner_statement_id=model.partner_statement_id,
        partner_account_id=model.partner_account_id,
        source_reference_type=model.source_reference_type,
        source_reference_id=model.source_reference_id,
        carried_from_adjustment_id=model.carried_from_adjustment_id,
        adjustment_type=model.adjustment_type,
        adjustment_direction=model.adjustment_direction,
        amount=float(model.amount),
        currency_code=model.currency_code,
        reason_code=model.reason_code,
        adjustment_payload=dict(model.adjustment_payload or {}),
        created_by_admin_user_id=model.created_by_admin_user_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post("/generate", response_model=PartnerStatementResponse, status_code=status.HTTP_201_CREATED)
async def generate_partner_statement(
    payload: GeneratePartnerStatementRequest,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PartnerStatementResponse:
    try:
        item = await GeneratePartnerStatementUseCase(db).execute(
            settlement_period_id=payload.settlement_period_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_statement(item)


@router.get("/", response_model=list[PartnerStatementResponse])
async def list_partner_statements(
    partner_account_id: UUID | None = Query(None),
    settlement_period_id: UUID | None = Query(None),
    statement_status: PartnerStatementStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[PartnerStatementResponse]:
    items = await ListPartnerStatementsUseCase(db).execute(
        partner_account_id=partner_account_id,
        settlement_period_id=settlement_period_id,
        statement_status=statement_status.value if statement_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_statement(item) for item in items]


@router.get("/{statement_id}", response_model=PartnerStatementResponse)
async def get_partner_statement(
    statement_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> PartnerStatementResponse:
    item = await GetPartnerStatementUseCase(db).execute(statement_id=statement_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner statement not found")
    return _serialize_statement(item)


@router.post("/{statement_id}/close", response_model=PartnerStatementResponse)
async def close_partner_statement(
    statement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PartnerStatementResponse:
    try:
        item = await ClosePartnerStatementUseCase(db).execute(
            statement_id=statement_id,
            closed_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_statement(item)


@router.post("/{statement_id}/reopen", response_model=PartnerStatementResponse)
async def reopen_partner_statement(
    statement_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PartnerStatementResponse:
    try:
        item = await ReopenPartnerStatementUseCase(db).execute(statement_id=statement_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_statement(item)


@router.get("/{statement_id}/adjustments", response_model=list[StatementAdjustmentResponse])
async def list_statement_adjustments(
    statement_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[StatementAdjustmentResponse]:
    items = await ListStatementAdjustmentsUseCase(db).execute(partner_statement_id=statement_id)
    return [_serialize_adjustment(item) for item in items]


@router.post(
    "/{statement_id}/adjustments",
    response_model=StatementAdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_statement_adjustment(
    statement_id: UUID,
    payload: CreateStatementAdjustmentRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> StatementAdjustmentResponse:
    try:
        item = await CreateStatementAdjustmentUseCase(db).execute(
            partner_statement_id=statement_id,
            adjustment_type=payload.adjustment_type.value,
            adjustment_direction=payload.adjustment_direction.value,
            amount=float(payload.amount),
            currency_code=payload.currency_code,
            reason_code=payload.reason_code,
            adjustment_payload=payload.adjustment_payload,
            source_reference_type=payload.source_reference_type,
            source_reference_id=payload.source_reference_id,
            created_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_adjustment(item)
