from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.merchant_billing import (
    CreateBillingDescriptorUseCase,
    ListBillingDescriptorsUseCase,
    ResolveBillingDescriptorUseCase,
)
from src.domain.enums import AdminRole
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import BillingDescriptorResponse, CreateBillingDescriptorRequest

router = APIRouter(prefix="/billing-descriptors", tags=["billing-descriptors"])


@router.get("/", response_model=list[BillingDescriptorResponse])
async def list_billing_descriptors(
    merchant_profile_id: UUID | None = Query(None),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(AdminRole.ADMIN)),
):
    use_case = ListBillingDescriptorsUseCase(db)
    return await use_case.execute(
        merchant_profile_id=merchant_profile_id,
        include_inactive=include_inactive,
    )


@router.get("/resolve", response_model=BillingDescriptorResponse)
async def resolve_billing_descriptor(
    merchant_profile_id: UUID = Query(...),
    invoice_profile_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    use_case = ResolveBillingDescriptorUseCase(db)
    resolved = await use_case.execute(
        merchant_profile_id=merchant_profile_id,
        invoice_profile_id=invoice_profile_id,
    )
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing descriptor not found")
    return resolved


@router.post("/", response_model=BillingDescriptorResponse, status_code=status.HTTP_201_CREATED)
async def create_billing_descriptor(
    payload: CreateBillingDescriptorRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(AdminRole.ADMIN)),
):
    use_case = CreateBillingDescriptorUseCase(db)
    try:
        return await use_case.execute(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
