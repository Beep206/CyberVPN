from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.offers import CreatePricebookUseCase, ListPricebooksUseCase
from src.domain.enums import AdminRole
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import CreatePricebookRequest, PricebookResponse

router = APIRouter(prefix="/pricebooks", tags=["pricebooks"])


@router.get("/resolve", response_model=list[PricebookResponse])
async def resolve_pricebooks(
    storefront_id: UUID | None = Query(None),
    storefront_key: str | None = Query(None),
    currency_code: str = Query("USD"),
    region_code: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    use_case = ListPricebooksUseCase(db)
    return await use_case.execute(
        storefront_id=storefront_id,
        storefront_key=storefront_key,
        currency_code=currency_code,
        region_code=region_code,
    )


@router.get("/admin", response_model=list[PricebookResponse])
async def list_admin_pricebooks(
    include_inactive: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(AdminRole.ADMIN)),
):
    use_case = ListPricebooksUseCase(db)
    return await use_case.execute(include_inactive=include_inactive)


@router.post("/", response_model=PricebookResponse, status_code=status.HTTP_201_CREATED)
async def create_pricebook(
    payload: CreatePricebookRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(AdminRole.ADMIN)),
):
    use_case = CreatePricebookUseCase(db)
    try:
        return await use_case.execute(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
