from fastapi import APIRouter, Depends
from src.presentation.dependencies import require_role, get_remnawave_client
from src.infrastructure.remnawave.client import RemnawaveClient

from .schemas import CreateSettingRequest, UpdateSettingRequest

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/")
async def get_settings(
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Get system settings (admin only)"""
    return await client.get("/settings")

@router.post("/")
async def create_setting(
    setting_data: CreateSettingRequest,
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Create a new system setting (admin only)"""
    return await client.post("/settings", json=setting_data.model_dump())

@router.put("/{id}")
async def update_setting(
    id: int,
    setting_data: UpdateSettingRequest,
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Update system setting (admin only)"""
    return await client.put(f"/settings/{id}", json=setting_data.model_dump(exclude_none=True))
