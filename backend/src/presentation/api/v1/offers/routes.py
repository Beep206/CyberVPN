from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.offers import CreateOfferUseCase, ListOffersUseCase
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.api.v1.admin.audit import write_required_commercial_catalog_audit_entry
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

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
    _current_user: AdminUserModel = Depends(require_permission(Permission.MANAGE_PLANS)),
):
    use_case = ListOffersUseCase(db)
    return await use_case.execute(include_inactive=include_inactive)


@router.post("/", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
async def create_offer(
    payload: CreateOfferRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.MANAGE_PLANS)),
):
    use_case = CreateOfferUseCase(db)
    try:
        created = await use_case.execute(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    after = OfferResponse.model_validate(created).model_dump(mode="json")
    await write_required_commercial_catalog_audit_entry(
        db=db,
        action="commercial_catalog.offer.created",
        resource_type="offer_version",
        resource_id=created.id,
        actor=current_user,
        request=request,
        before=None,
        after=after,
    )
    return created
