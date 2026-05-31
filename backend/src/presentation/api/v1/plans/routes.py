from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.stage1_plan_policy import filter_stage1_public_paid_plans
from src.application.use_cases.auth.permissions import Permission
from src.domain.enums import CatalogVisibility
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.monitoring.instrumentation.routes import track_plan_query
from src.infrastructure.remnawave.contracts import StatusMessageResponse
from src.presentation.api.v1.admin.audit import write_required_commercial_catalog_audit_entry
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

from .schemas import CreatePlanRequest, PlanResponse, UpdatePlanRequest

router = APIRouter(prefix="/plans", tags=["plans"])


def _serialize_plan(plan: SubscriptionPlanModel) -> PlanResponse:
    return PlanResponse(
        uuid=str(plan.id),
        name=plan.name,
        plan_code=plan.plan_code or "",
        display_name=plan.display_name or plan.name,
        catalog_visibility=plan.catalog_visibility,
        duration_days=plan.duration_days,
        traffic_limit_bytes=plan.traffic_limit_bytes,
        devices_included=plan.device_limit,
        price_usd=float(plan.price_usd),
        price_rub=float(plan.price_rub) if plan.price_rub is not None else None,
        traffic_policy=plan.traffic_policy or {"mode": "fair_use", "display_label": "Unlimited"},
        connection_modes=plan.connection_modes or [],
        server_pool=plan.server_pool or [],
        support_sla=plan.support_sla,
        dedicated_ip=plan.dedicated_ip or {"included": 0, "eligible": False},
        sale_channels=plan.sale_channels or [],
        invite_bundle=plan.invite_bundle or {"count": 0, "friend_days": 0, "expiry_days": 0},
        trial_eligible=plan.trial_eligible,
        features=plan.features or {},
        is_active=plan.is_active,
        sort_order=plan.sort_order,
    )


@router.get("", response_model=list[PlanResponse], include_in_schema=False)
@router.get("/", response_model=list[PlanResponse])
async def list_plans(
    channel: str = Query("web", description="Public sale channel filter"),
    db: AsyncSession = Depends(get_db),
):
    """List public subscription plans from the backend-owned pricing catalog."""
    track_plan_query(operation="list")
    repo = SubscriptionPlanRepository(db)
    plans = await repo.list_catalog(
        visibility=CatalogVisibility.PUBLIC,
        sale_channel=channel,
        active_only=True,
    )
    return [_serialize_plan(plan) for plan in filter_stage1_public_paid_plans(plans, sale_channel=channel)]


@router.get("/admin", response_model=list[PlanResponse])
async def list_admin_plans(
    include_inactive: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_permission(Permission.MANAGE_PLANS)),
):
    """List all typed catalog plans, including hidden plans, for admin tooling."""
    repo = SubscriptionPlanRepository(db)
    plans = await repo.get_all(active_only=not include_inactive, include_untyped=False)
    return [_serialize_plan(plan) for plan in plans]


@router.post("/", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan_data: CreatePlanRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.MANAGE_PLANS)),
):
    """Create a new subscription plan in the canonical pricing catalog."""
    repo = SubscriptionPlanRepository(db)
    existing = await repo.get_by_name(plan_data.name)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plan name already exists")

    model = SubscriptionPlanModel(
        name=plan_data.name,
        plan_code=plan_data.plan_code,
        display_name=plan_data.display_name,
        catalog_visibility=plan_data.catalog_visibility,
        duration_days=plan_data.duration_days,
        traffic_limit_bytes=plan_data.traffic_limit_bytes,
        device_limit=plan_data.devices_included,
        price_usd=plan_data.price_usd,
        price_rub=plan_data.price_rub,
        sale_channels=plan_data.sale_channels,
        traffic_policy=plan_data.traffic_policy.model_dump(),
        connection_modes=plan_data.connection_modes,
        server_pool=plan_data.server_pool,
        support_sla=plan_data.support_sla,
        dedicated_ip=plan_data.dedicated_ip.model_dump(),
        invite_bundle=plan_data.invite_bundle.model_dump(),
        trial_eligible=plan_data.trial_eligible,
        features=plan_data.features,
        is_active=plan_data.is_active,
        sort_order=plan_data.sort_order,
    )
    created = await repo.create(model)
    after = _serialize_plan(created).model_dump(mode="json")
    await write_required_commercial_catalog_audit_entry(
        db=db,
        action="commercial_catalog.plan.created",
        resource_type="subscription_plan",
        resource_id=created.id,
        actor=current_user,
        request=request,
        before=None,
        after=after,
    )
    return _serialize_plan(created)


@router.put("/{uuid}", response_model=PlanResponse)
async def update_plan(
    uuid: str,
    plan_data: UpdatePlanRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.MANAGE_PLANS)),
):
    """Update subscription plan (admin only)."""
    repo = SubscriptionPlanRepository(db)
    try:
        plan_id = UUID(uuid)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan UUID") from exc

    model = await repo.get_by_id(plan_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    before = _serialize_plan(model).model_dump(mode="json")
    payload = plan_data.model_dump(exclude_none=True)
    scalar_mapping = {
        "name": "name",
        "plan_code": "plan_code",
        "display_name": "display_name",
        "catalog_visibility": "catalog_visibility",
        "duration_days": "duration_days",
        "traffic_limit_bytes": "traffic_limit_bytes",
        "devices_included": "device_limit",
        "price_usd": "price_usd",
        "price_rub": "price_rub",
        "connection_modes": "connection_modes",
        "server_pool": "server_pool",
        "support_sla": "support_sla",
        "sale_channels": "sale_channels",
        "trial_eligible": "trial_eligible",
        "features": "features",
        "is_active": "is_active",
        "sort_order": "sort_order",
    }
    for source_key, target_attr in scalar_mapping.items():
        if source_key in payload:
            setattr(model, target_attr, payload[source_key])

    if "traffic_policy" in payload:
        model.traffic_policy = payload["traffic_policy"]
    if "dedicated_ip" in payload:
        model.dedicated_ip = payload["dedicated_ip"]
    if "invite_bundle" in payload:
        model.invite_bundle = payload["invite_bundle"]

    updated = await repo.update(model)
    after = _serialize_plan(updated).model_dump(mode="json")
    await write_required_commercial_catalog_audit_entry(
        db=db,
        action="commercial_catalog.plan.updated",
        resource_type="subscription_plan",
        resource_id=updated.id,
        actor=current_user,
        request=request,
        before=before,
        after=after,
    )
    return _serialize_plan(updated)


@router.delete("/{uuid}", response_model=StatusMessageResponse)
async def delete_plan(
    uuid: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.MANAGE_PLANS)),
):
    """Delete subscription plan (admin only)"""
    repo = SubscriptionPlanRepository(db)
    try:
        plan_id = UUID(uuid)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan UUID") from exc

    model = await repo.get_by_id(plan_id)
    before = _serialize_plan(model).model_dump(mode="json") if model is not None else None
    await repo.delete(plan_id)
    if before is not None:
        await write_required_commercial_catalog_audit_entry(
            db=db,
            action="commercial_catalog.plan.deleted",
            resource_type="subscription_plan",
            resource_id=plan_id,
            actor=current_user,
            request=request,
            before=before,
            after=None,
        )
    return StatusMessageResponse(status="ok", message="Plan deleted")
