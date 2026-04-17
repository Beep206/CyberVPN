from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import AdminRole
from src.infrastructure.database.models.plan_addon_model import PlanAddonModel
from src.infrastructure.database.repositories.plan_addon_repo import PlanAddonRepository
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import AddonResponse, CreateAddonRequest, UpdateAddonRequest

router = APIRouter(prefix="/addons", tags=["addons"])


def _serialize_addon(model: PlanAddonModel) -> AddonResponse:
    return AddonResponse(
        uuid=str(model.id),
        code=model.code,
        display_name=model.display_name,
        duration_mode=model.duration_mode,
        is_stackable=model.is_stackable,
        quantity_step=model.quantity_step,
        price_usd=float(model.price_usd),
        price_rub=float(model.price_rub) if model.price_rub is not None else None,
        max_quantity_by_plan=model.max_quantity_by_plan or {},
        delta_entitlements=model.delta_entitlements or {},
        requires_location=model.requires_location,
        sale_channels=model.sale_channels or [],
        is_active=model.is_active,
    )


@router.get("/catalog", response_model=list[AddonResponse])
async def list_addon_catalog(
    channel: str = Query("web", description="Public sale channel filter"),
    db: AsyncSession = Depends(get_db),
) -> list[AddonResponse]:
    repo = PlanAddonRepository(db)
    addons = await repo.list_catalog(active_only=True, sale_channel=channel)
    return [_serialize_addon(addon) for addon in addons]


@router.get("", response_model=list[AddonResponse])
async def list_admin_addons(
    include_inactive: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(AdminRole.ADMIN)),
) -> list[AddonResponse]:
    repo = PlanAddonRepository(db)
    addons = await repo.list_catalog(active_only=not include_inactive)
    return [_serialize_addon(addon) for addon in addons]


@router.post("", response_model=AddonResponse, status_code=status.HTTP_201_CREATED)
async def create_addon(
    body: CreateAddonRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(AdminRole.ADMIN)),
) -> AddonResponse:
    repo = PlanAddonRepository(db)
    existing = await repo.get_by_code(body.code)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Addon code already exists")

    addon = PlanAddonModel(
        code=body.code,
        display_name=body.display_name,
        duration_mode=body.duration_mode,
        is_stackable=body.is_stackable,
        quantity_step=body.quantity_step,
        price_usd=body.price_usd,
        price_rub=body.price_rub,
        max_quantity_by_plan=body.max_quantity_by_plan,
        delta_entitlements=body.delta_entitlements,
        requires_location=body.requires_location,
        sale_channels=body.sale_channels,
        is_active=body.is_active,
    )
    created = await repo.create(addon)
    return _serialize_addon(created)


@router.put("/{addon_id}", response_model=AddonResponse)
async def update_addon(
    addon_id: UUID,
    body: UpdateAddonRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(AdminRole.ADMIN)),
) -> AddonResponse:
    repo = PlanAddonRepository(db)
    addon = await repo.get_by_id(addon_id)
    if addon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Addon not found")

    payload = body.model_dump(exclude_none=True)
    for key, value in payload.items():
        setattr(addon, key, value)

    updated = await repo.update(addon)
    return _serialize_addon(updated)
