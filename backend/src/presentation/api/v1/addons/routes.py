from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.stage1_plan_policy import filter_stage1_public_addons
from src.application.use_cases.auth.permissions import Permission
from src.config.settings import settings
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.plan_addon_model import PlanAddonModel
from src.infrastructure.database.repositories.plan_addon_repo import PlanAddonRepository
from src.presentation.api.v1.admin.audit import write_required_commercial_catalog_audit_entry
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

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
    return [
        _serialize_addon(addon)
        for addon in filter_stage1_public_addons(
            addons,
            sale_channel=channel,
            enabled=settings.stage1_addons_enabled,
        )
    ]


@router.get("", response_model=list[AddonResponse])
async def list_admin_addons(
    include_inactive: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_permission(Permission.MANAGE_PLANS)),
) -> list[AddonResponse]:
    repo = PlanAddonRepository(db)
    addons = await repo.list_catalog(active_only=not include_inactive)
    return [_serialize_addon(addon) for addon in addons]


@router.post("", response_model=AddonResponse, status_code=status.HTTP_201_CREATED)
async def create_addon(
    body: CreateAddonRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.MANAGE_PLANS)),
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
    after = _serialize_addon(created).model_dump(mode="json")
    await write_required_commercial_catalog_audit_entry(
        db=db,
        action="commercial_catalog.addon.created",
        resource_type="plan_addon",
        resource_id=created.id,
        actor=current_user,
        request=request,
        before=None,
        after=after,
    )
    return _serialize_addon(created)


@router.put("/{addon_id}", response_model=AddonResponse)
async def update_addon(
    addon_id: UUID,
    body: UpdateAddonRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.MANAGE_PLANS)),
) -> AddonResponse:
    repo = PlanAddonRepository(db)
    addon = await repo.get_by_id(addon_id)
    if addon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Addon not found")

    before = _serialize_addon(addon).model_dump(mode="json")
    payload = body.model_dump(exclude_none=True)
    for key, value in payload.items():
        setattr(addon, key, value)

    updated = await repo.update(addon)
    after = _serialize_addon(updated).model_dump(mode="json")
    await write_required_commercial_catalog_audit_entry(
        db=db,
        action="commercial_catalog.addon.updated",
        resource_type="plan_addon",
        resource_id=updated.id,
        actor=current_user,
        request=request,
        before=before,
        after=after,
    )
    return _serialize_addon(updated)
