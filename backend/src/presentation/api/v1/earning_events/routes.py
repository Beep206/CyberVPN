from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.settlement import GetEarningEventUseCase, ListEarningEventsUseCase
from src.domain.enums import AdminRole, EarningEventStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import EarningEventResponse

router = APIRouter(prefix="/earning-events", tags=["earning-events"])


def _serialize_event(model) -> EarningEventResponse:
    return EarningEventResponse(
        id=model.id,
        partner_account_id=model.partner_account_id,
        partner_user_id=model.partner_user_id,
        client_user_id=model.client_user_id,
        order_id=model.order_id,
        payment_id=model.payment_id,
        partner_code_id=model.partner_code_id,
        legacy_partner_earning_id=model.legacy_partner_earning_id,
        order_attribution_result_id=model.order_attribution_result_id,
        owner_type=model.owner_type,
        event_status=model.event_status,
        commission_base_amount=float(model.commission_base_amount),
        markup_amount=float(model.markup_amount),
        commission_pct=float(model.commission_pct),
        commission_amount=float(model.commission_amount),
        total_amount=float(model.total_amount),
        currency_code=model.currency_code,
        available_at=model.available_at,
        source_snapshot=dict(model.source_snapshot or {}),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.get("/", response_model=list[EarningEventResponse])
async def list_earning_events(
    partner_account_id: UUID | None = Query(None),
    order_id: UUID | None = Query(None),
    event_status: EarningEventStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[EarningEventResponse]:
    items = await ListEarningEventsUseCase(db).execute(
        partner_account_id=partner_account_id,
        order_id=order_id,
        event_status=event_status.value if event_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_event(item) for item in items]


@router.get("/{event_id}", response_model=EarningEventResponse)
async def get_earning_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> EarningEventResponse:
    item = await GetEarningEventUseCase(db).execute(event_id=event_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Earning event not found")
    return _serialize_event(item)
