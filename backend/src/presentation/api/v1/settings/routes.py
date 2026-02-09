from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_remnawave_client, require_role
from src.presentation.schemas.remnawave_responses import RemnawaveSettingResponse

from .schemas import CreateSettingRequest, UpdateSettingRequest

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", response_model=list[RemnawaveSettingResponse])
async def get_settings(
    current_user=Depends(require_role(AdminRole.ADMIN)), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Get system settings (admin only)"""
    return await client.get("/settings")


@router.post("/", response_model=RemnawaveSettingResponse)
async def create_setting(
    setting_data: CreateSettingRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Create a new system setting (admin only)"""
    return await client.post("/settings", json=setting_data.model_dump())


@router.put("/{id}", response_model=RemnawaveSettingResponse)
async def update_setting(
    id: int,
    setting_data: UpdateSettingRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Update system setting (admin only)"""
    return await client.put(f"/settings/{id}", json=setting_data.model_dump(exclude_none=True))
