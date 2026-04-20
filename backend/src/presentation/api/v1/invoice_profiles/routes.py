from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.merchant_billing import CreateInvoiceProfileUseCase, ListInvoiceProfilesUseCase
from src.domain.enums import AdminRole
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import CreateInvoiceProfileRequest, InvoiceProfileResponse

router = APIRouter(prefix="/invoice-profiles", tags=["invoice-profiles"])


@router.get("/", response_model=list[InvoiceProfileResponse])
async def list_invoice_profiles(
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(AdminRole.ADMIN)),
):
    use_case = ListInvoiceProfilesUseCase(db)
    return await use_case.execute(include_inactive=include_inactive)


@router.post("/", response_model=InvoiceProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice_profile(
    payload: CreateInvoiceProfileRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(AdminRole.ADMIN)),
):
    use_case = CreateInvoiceProfileUseCase(db)
    try:
        return await use_case.execute(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
