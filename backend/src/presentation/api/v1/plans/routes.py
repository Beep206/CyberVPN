from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.monitoring.instrumentation.routes import track_plan_query
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import (
    RemnavwavePlanResponse,
    StatusMessageResponse,
)
from src.presentation.dependencies import get_remnawave_client, require_role

from .schemas import CreatePlanRequest, UpdatePlanRequest

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/", response_model=list[RemnavwavePlanResponse])
async def list_plans(client: RemnawaveClient = Depends(get_remnawave_client)):
    """List all available subscription plans (public)"""
    track_plan_query(operation="list")
    return await client.get_list_validated("/plans", RemnavwavePlanResponse)


@router.post("/", response_model=RemnavwavePlanResponse)
async def create_plan(
    plan_data: CreatePlanRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Create a new subscription plan (admin only)"""
    return await client.post_validated("/plans", RemnavwavePlanResponse, json=plan_data.model_dump())


@router.put("/{uuid}", response_model=RemnavwavePlanResponse)
async def update_plan(
    uuid: str,
    plan_data: UpdatePlanRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Update subscription plan (admin only)"""
    return await client.put_validated(
        f"/plans/{uuid}",
        RemnavwavePlanResponse,
        json=plan_data.model_dump(exclude_none=True),
    )


@router.delete("/{uuid}", response_model=StatusMessageResponse)
async def delete_plan(
    uuid: str,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Delete subscription plan (admin only)"""
    return await client.delete_validated(f"/plans/{uuid}", StatusMessageResponse)
