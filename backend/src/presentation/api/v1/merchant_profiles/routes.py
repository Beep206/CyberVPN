from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.merchant_billing import (
    CreateMerchantProfileUseCase,
    ListMerchantProfilesUseCase,
    ResolveMerchantProfileUseCase,
)
from src.domain.enums import AdminRole
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import CreateMerchantProfileRequest, MerchantProfileResponse

router = APIRouter(prefix="/merchant-profiles", tags=["merchant-profiles"])


@router.get("/", response_model=list[MerchantProfileResponse])
async def list_merchant_profiles(
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(AdminRole.ADMIN)),
):
    use_case = ListMerchantProfilesUseCase(db)
    return await use_case.execute(include_inactive=include_inactive)


@router.get("/resolve", response_model=MerchantProfileResponse)
async def resolve_merchant_profile(
    storefront_id: UUID | None = Query(None),
    storefront_key: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    use_case = ResolveMerchantProfileUseCase(db)
    try:
        resolved = await use_case.execute(storefront_id=storefront_id, storefront_key=storefront_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant profile not found")
    return resolved


@router.post("/", response_model=MerchantProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_merchant_profile(
    payload: CreateMerchantProfileRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(AdminRole.ADMIN)),
):
    use_case = CreateMerchantProfileUseCase(db)
    try:
        return await use_case.execute(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
