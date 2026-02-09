from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_current_active_user, get_remnawave_client, require_role
from src.presentation.schemas.remnawave_responses import RemnawaveConfigProfileResponse

from .schemas import CreateConfigProfileRequest

router = APIRouter(prefix="/config-profiles", tags=["config-profiles"])


@router.get("/", response_model=list[RemnawaveConfigProfileResponse])
async def list_config_profiles(
    current_user=Depends(get_current_active_user), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List available configuration profiles"""
    return await client.get("/config-profiles")


@router.post("/", response_model=RemnawaveConfigProfileResponse)
async def create_config_profile(
    profile_data: CreateConfigProfileRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Create a new configuration profile (admin only)"""
    return await client.post("/config-profiles", json=profile_data.model_dump())
