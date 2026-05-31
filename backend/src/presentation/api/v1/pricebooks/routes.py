from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.offers import CreatePricebookUseCase, ListPricebooksUseCase
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.api.v1.admin.audit import write_required_commercial_catalog_audit_entry
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

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
    _current_user: AdminUserModel = Depends(require_permission(Permission.MANAGE_PLANS)),
):
    use_case = ListPricebooksUseCase(db)
    return await use_case.execute(include_inactive=include_inactive)


@router.post("/", response_model=PricebookResponse, status_code=status.HTTP_201_CREATED)
async def create_pricebook(
    payload: CreatePricebookRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.MANAGE_PLANS)),
):
    use_case = CreatePricebookUseCase(db)
    try:
        created = await use_case.execute(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    after = PricebookResponse.model_validate(created).model_dump(mode="json")
    await write_required_commercial_catalog_audit_entry(
        db=db,
        action="commercial_catalog.pricebook.created",
        resource_type="pricebook_version",
        resource_id=created.id,
        actor=current_user,
        request=request,
        before=None,
        after=after,
    )
    return created
