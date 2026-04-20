from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.governance import (
    CreateDisputeCaseUseCase,
    GetDisputeCaseUseCase,
    ListDisputeCasesUseCase,
)
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import CreateDisputeCaseRequest, DisputeCaseResponse

router = APIRouter(prefix="/dispute-cases", tags=["dispute-cases"])


@router.post("/", response_model=DisputeCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_dispute_case(
    payload: CreateDisputeCaseRequest,
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> DisputeCaseResponse:
    try:
        created = await CreateDisputeCaseUseCase(db).execute(
            partner_account_id=payload.partner_account_id,
            payment_dispute_id=payload.payment_dispute_id,
            order_id=payload.order_id,
            case_kind=payload.case_kind.value,
            case_status=payload.case_status.value,
            summary=payload.summary,
            case_payload=payload.case_payload,
            notes=payload.notes,
            opened_by_admin_user_id=current_admin.id,
            assigned_to_admin_user_id=payload.assigned_to_admin_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DisputeCaseResponse.model_validate(created)


@router.get("/", response_model=list[DisputeCaseResponse])
async def list_dispute_cases(
    partner_account_id: UUID | None = Query(None),
    payment_dispute_id: UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> list[DisputeCaseResponse]:
    items = await ListDisputeCasesUseCase(db).execute(
        partner_account_id=partner_account_id,
        payment_dispute_id=payment_dispute_id,
        limit=limit,
        offset=offset,
    )
    return [DisputeCaseResponse.model_validate(item) for item in items]


@router.get("/{dispute_case_id}", response_model=DisputeCaseResponse)
async def get_dispute_case(
    dispute_case_id: UUID,
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> DisputeCaseResponse:
    item = await GetDisputeCaseUseCase(db).execute(dispute_case_id=dispute_case_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute case not found")
    return DisputeCaseResponse.model_validate(item)
