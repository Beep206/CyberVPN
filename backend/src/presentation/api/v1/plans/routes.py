from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_remnawave_client, require_role
from src.presentation.schemas.remnawave_responses import (
    RemnavwavePlanResponse,
    StatusMessageResponse,
)

from .schemas import CreatePlanRequest, UpdatePlanRequest

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/", response_model=list[RemnavwavePlanResponse])
async def list_plans(client: RemnawaveClient = Depends(get_remnawave_client)):
    """List all available subscription plans (public)"""
    return await client.get("/plans")


@router.post("/", response_model=RemnavwavePlanResponse)
async def create_plan(
    plan_data: CreatePlanRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Create a new subscription plan (admin only)"""
    return await client.post("/plans", json=plan_data.model_dump())


@router.put("/{uuid}", response_model=RemnavwavePlanResponse)
async def update_plan(
    uuid: str,
    plan_data: UpdatePlanRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Update subscription plan (admin only)"""
    return await client.put(f"/plans/{uuid}", json=plan_data.model_dump(exclude_none=True))


@router.delete("/{uuid}", response_model=StatusMessageResponse)
async def delete_plan(
    uuid: str,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Delete subscription plan (admin only)"""
    return await client.delete(f"/plans/{uuid}")
