from fastapi import APIRouter, Depends
from src.presentation.dependencies import get_current_active_user, require_role, get_remnawave_client
from src.infrastructure.remnawave.client import RemnawaveClient

from .schemas import CreateConfigProfileRequest

router = APIRouter(prefix="/config-profiles", tags=["config-profiles"])

@router.get("/")
async def list_config_profiles(
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List available configuration profiles"""
    return await client.get("/config-profiles")

@router.post("/")
async def create_config_profile(
    profile_data: CreateConfigProfileRequest,
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Create a new configuration profile (admin only)"""
    return await client.post("/config-profiles", json=profile_data.model_dump())
