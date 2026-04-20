from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.governance import (
    CreateTrafficDeclarationUseCase,
    GetTrafficDeclarationUseCase,
    ListTrafficDeclarationsUseCase,
)
from src.domain.entities.partner_permission import PartnerPermission
from src.domain.enums import TrafficDeclarationKind
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_workspace import resolve_partner_workspace_access

from .schemas import CreateTrafficDeclarationRequest, TrafficDeclarationResponse

router = APIRouter(prefix="/traffic-declarations", tags=["traffic-declarations"])


async def _require_workspace_permission(
    *,
    workspace_id: UUID,
    current_user: AdminUserModel,
    db: AsyncSession,
    permission: PartnerPermission,
) -> None:
    access = await resolve_partner_workspace_access(
        workspace_id=workspace_id,
        current_user=current_user,
        db=db,
    )
    if permission.value not in access.permission_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing partner workspace permission: {permission.value}",
        )


@router.post("/", response_model=TrafficDeclarationResponse, status_code=status.HTTP_201_CREATED)
async def create_traffic_declaration(
    payload: CreateTrafficDeclarationRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TrafficDeclarationResponse:
    await _require_workspace_permission(
        workspace_id=payload.partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.TRAFFIC_WRITE,
    )
    try:
        created = await CreateTrafficDeclarationUseCase(db).execute(
            partner_account_id=payload.partner_account_id,
            declaration_kind=payload.declaration_kind.value,
            scope_label=payload.scope_label,
            declaration_payload=payload.declaration_payload,
            notes=payload.notes,
            submitted_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return TrafficDeclarationResponse.model_validate(created)


@router.get("/", response_model=list[TrafficDeclarationResponse])
async def list_traffic_declarations(
    partner_account_id: UUID = Query(...),
    declaration_kind: TrafficDeclarationKind | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[TrafficDeclarationResponse]:
    await _require_workspace_permission(
        workspace_id=partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.TRAFFIC_READ,
    )
    items = await ListTrafficDeclarationsUseCase(db).execute(
        partner_account_id=partner_account_id,
        declaration_kind=declaration_kind.value if declaration_kind else None,
        limit=limit,
        offset=offset,
    )
    return [TrafficDeclarationResponse.model_validate(item) for item in items]


@router.get("/{traffic_declaration_id}", response_model=TrafficDeclarationResponse)
async def get_traffic_declaration(
    traffic_declaration_id: UUID,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TrafficDeclarationResponse:
    item = await GetTrafficDeclarationUseCase(db).execute(
        traffic_declaration_id=traffic_declaration_id,
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Traffic declaration not found")
    await _require_workspace_permission(
        workspace_id=item.partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.TRAFFIC_READ,
    )
    return TrafficDeclarationResponse.model_validate(item)
