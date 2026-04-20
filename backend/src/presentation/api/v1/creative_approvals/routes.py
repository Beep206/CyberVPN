from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.governance import (
    CreateCreativeApprovalUseCase,
    GetCreativeApprovalUseCase,
    ListCreativeApprovalsUseCase,
)
from src.domain.enums import AdminRole, CreativeApprovalKind
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import CreateCreativeApprovalRequest, CreativeApprovalResponse

router = APIRouter(prefix="/creative-approvals", tags=["creative-approvals"])


@router.post("/", response_model=CreativeApprovalResponse, status_code=status.HTTP_201_CREATED)
async def create_creative_approval(
    payload: CreateCreativeApprovalRequest,
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> CreativeApprovalResponse:
    try:
        created = await CreateCreativeApprovalUseCase(db).execute(
            partner_account_id=payload.partner_account_id,
            approval_kind=payload.approval_kind.value,
            approval_status=payload.approval_status.value,
            scope_label=payload.scope_label,
            creative_ref=payload.creative_ref,
            approval_payload=payload.approval_payload,
            notes=payload.notes,
            expires_at=payload.expires_at,
            submitted_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CreativeApprovalResponse.model_validate(created)


@router.get("/", response_model=list[CreativeApprovalResponse])
async def list_creative_approvals(
    partner_account_id: UUID | None = Query(None),
    approval_kind: CreativeApprovalKind | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> list[CreativeApprovalResponse]:
    items = await ListCreativeApprovalsUseCase(db).execute(
        partner_account_id=partner_account_id,
        approval_kind=approval_kind.value if approval_kind else None,
        limit=limit,
        offset=offset,
    )
    return [CreativeApprovalResponse.model_validate(item) for item in items]


@router.get("/{creative_approval_id}", response_model=CreativeApprovalResponse)
async def get_creative_approval(
    creative_approval_id: UUID,
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> CreativeApprovalResponse:
    item = await GetCreativeApprovalUseCase(db).execute(creative_approval_id=creative_approval_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creative approval not found")
    return CreativeApprovalResponse.model_validate(item)
