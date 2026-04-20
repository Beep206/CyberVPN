from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.growth_rewards import (
    CreateGrowthRewardAllocationUseCase,
    GetGrowthRewardAllocationUseCase,
    ListGrowthRewardAllocationsUseCase,
)
from src.domain.enums import AdminRole, GrowthRewardAllocationStatus, GrowthRewardType
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import CreateGrowthRewardAllocationRequest, GrowthRewardAllocationResponse

router = APIRouter(prefix="/growth-rewards", tags=["growth-rewards"])


def _serialize_allocation(model) -> GrowthRewardAllocationResponse:
    return GrowthRewardAllocationResponse(
        id=model.id,
        reward_type=model.reward_type,
        allocation_status=model.allocation_status,
        beneficiary_user_id=model.beneficiary_user_id,
        auth_realm_id=model.auth_realm_id,
        storefront_id=model.storefront_id,
        order_id=model.order_id,
        invite_code_id=model.invite_code_id,
        referral_commission_id=model.referral_commission_id,
        source_key=model.source_key,
        quantity=float(model.quantity),
        unit=model.unit,
        currency_code=model.currency_code,
        reward_payload=model.reward_payload or {},
        created_by_admin_user_id=model.created_by_admin_user_id,
        allocated_at=model.allocated_at,
        reversed_at=model.reversed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post("/allocations", response_model=GrowthRewardAllocationResponse, status_code=status.HTTP_201_CREATED)
async def create_growth_reward_allocation(
    payload: CreateGrowthRewardAllocationRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> GrowthRewardAllocationResponse:
    use_case = CreateGrowthRewardAllocationUseCase(db)
    try:
        created = await use_case.execute(
            reward_type=payload.reward_type.value,
            beneficiary_user_id=payload.beneficiary_user_id,
            quantity=payload.quantity,
            unit=payload.unit,
            currency_code=payload.currency_code,
            storefront_id=payload.storefront_id,
            order_id=payload.order_id,
            invite_code_id=payload.invite_code_id,
            referral_commission_id=payload.referral_commission_id,
            source_key=payload.source_key,
            reward_payload=payload.reward_payload,
            created_by_admin_user_id=current_admin.id,
            allocated_at=payload.allocated_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_allocation(created)


@router.get("/allocations", response_model=list[GrowthRewardAllocationResponse])
async def list_growth_reward_allocations(
    beneficiary_user_id: UUID | None = Query(None),
    order_id: UUID | None = Query(None),
    reward_type: GrowthRewardType | None = Query(None),
    allocation_status: GrowthRewardAllocationStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[GrowthRewardAllocationResponse]:
    use_case = ListGrowthRewardAllocationsUseCase(db)
    items = await use_case.execute(
        beneficiary_user_id=beneficiary_user_id,
        order_id=order_id,
        reward_type=reward_type.value if reward_type else None,
        allocation_status=allocation_status.value if allocation_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_allocation(item) for item in items]


@router.get("/allocations/{allocation_id}", response_model=GrowthRewardAllocationResponse)
async def get_growth_reward_allocation(
    allocation_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> GrowthRewardAllocationResponse:
    use_case = GetGrowthRewardAllocationUseCase(db)
    item = await use_case.execute(allocation_id=allocation_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Growth reward allocation not found")
    return _serialize_allocation(item)
