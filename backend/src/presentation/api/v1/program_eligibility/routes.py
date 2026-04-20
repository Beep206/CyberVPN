from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.offers import (
    CreateProgramEligibilityPolicyUseCase,
    ListProgramEligibilityPoliciesUseCase,
)
from src.domain.enums import AdminRole
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import CreateProgramEligibilityPolicyRequest, ProgramEligibilityPolicyResponse

router = APIRouter(prefix="/program-eligibility", tags=["program-eligibility"])


@router.get("/", response_model=list[ProgramEligibilityPolicyResponse])
async def list_program_eligibility(
    subject_type: str | None = Query(None),
    subscription_plan_id: UUID | None = Query(None),
    plan_addon_id: UUID | None = Query(None),
    offer_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    use_case = ListProgramEligibilityPoliciesUseCase(db)
    return await use_case.execute(
        subject_type=subject_type,
        subscription_plan_id=subscription_plan_id,
        plan_addon_id=plan_addon_id,
        offer_id=offer_id,
    )


@router.get("/admin", response_model=list[ProgramEligibilityPolicyResponse])
async def list_admin_program_eligibility(
    include_inactive: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(AdminRole.ADMIN)),
):
    use_case = ListProgramEligibilityPoliciesUseCase(db)
    return await use_case.execute(include_inactive=include_inactive)


@router.post("/", response_model=ProgramEligibilityPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_program_eligibility_policy(
    payload: CreateProgramEligibilityPolicyRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(AdminRole.ADMIN)),
):
    use_case = CreateProgramEligibilityPolicyUseCase(db)
    try:
        return await use_case.execute(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
