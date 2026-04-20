from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.offers import CreateOfferUseCase, ListOffersUseCase
from src.domain.enums import AdminRole
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import CreateOfferRequest, OfferResponse

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("/", response_model=list[OfferResponse])
async def list_offers(
    sale_channel: str | None = Query(None),
    subscription_plan_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    use_case = ListOffersUseCase(db)
    return await use_case.execute(
        sale_channel=sale_channel,
        subscription_plan_id=subscription_plan_id,
    )


@router.get("/admin", response_model=list[OfferResponse])
async def list_admin_offers(
    include_inactive: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(AdminRole.ADMIN)),
):
    use_case = ListOffersUseCase(db)
    return await use_case.execute(include_inactive=include_inactive)


@router.post("/", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
async def create_offer(
    payload: CreateOfferRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(AdminRole.ADMIN)),
):
    use_case = CreateOfferUseCase(db)
    try:
        return await use_case.execute(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
