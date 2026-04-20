from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.policies import (
    ApprovePolicyVersionUseCase,
    CreatePolicyVersionUseCase,
    ListPolicyVersionsUseCase,
)
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import ApprovePolicyVersionRequest, CreatePolicyVersionRequest, PolicyVersionResponse

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("/", response_model=list[PolicyVersionResponse])
async def list_policy_versions(
    policy_family: str | None = Query(None),
    policy_key: str | None = Query(None),
    subject_type: str | None = Query(None),
    subject_id: UUID | None = Query(None),
    approval_state: str | None = Query(None),
    include_inactive: bool = Query(False),
    at: datetime | None = Query(None),
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[PolicyVersionResponse]:
    use_case = ListPolicyVersionsUseCase(db)
    return await use_case.execute(
        policy_family=policy_family,
        policy_key=policy_key,
        subject_type=subject_type,
        subject_id=subject_id,
        approval_state=approval_state,
        include_inactive=include_inactive,
        at=at,
    )


@router.post("/", response_model=PolicyVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_policy_version(
    payload: CreatePolicyVersionRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PolicyVersionResponse:
    use_case = CreatePolicyVersionUseCase(db)
    try:
        return await use_case.execute(
            **payload.model_dump(),
            created_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{policy_version_id}/approve", response_model=PolicyVersionResponse)
async def approve_policy_version(
    policy_version_id: UUID,
    payload: ApprovePolicyVersionRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PolicyVersionResponse:
    use_case = ApprovePolicyVersionUseCase(db)
    try:
        return await use_case.execute(
            policy_version_id,
            approved_by_admin_user_id=current_user.id,
            **payload.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
