from fastapi import APIRouter, Depends
from src.presentation.dependencies import get_current_active_user, require_role, get_remnawave_client
from src.infrastructure.remnawave.client import RemnawaveClient

from .schemas import CreatePlanRequest, UpdatePlanRequest

router = APIRouter(prefix="/plans", tags=["plans"])

@router.get("/")
async def list_plans(
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List all available subscription plans (public)"""
    return await client.get("/plans")

@router.post("/")
async def create_plan(
    plan_data: CreatePlanRequest,
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Create a new subscription plan (admin only)"""
    return await client.post("/plans", json=plan_data.model_dump())

@router.put("/{uuid}")
async def update_plan(
    uuid: str,
    plan_data: UpdatePlanRequest,
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Update subscription plan (admin only)"""
    return await client.put(f"/plans/{uuid}", json=plan_data.model_dump(exclude_none=True))

@router.delete("/{uuid}")
async def delete_plan(
    uuid: str,
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Delete subscription plan (admin only)"""
    return await client.delete(f"/plans/{uuid}")
