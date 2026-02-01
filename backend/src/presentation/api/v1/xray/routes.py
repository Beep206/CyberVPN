from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_remnawave_client, require_role

from .schemas import UpdateXrayConfigRequest, XrayConfigResponse

router = APIRouter(prefix="/xray", tags=["xray"])


@router.get("/config", response_model=XrayConfigResponse)
async def get_xray_config(
    current_user=Depends(require_role(AdminRole.ADMIN)), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Get current Xray configuration (admin only)"""
    return await client.get("/xray/config")


@router.post("/update-config", response_model=XrayConfigResponse)
async def update_xray_config(
    config_data: UpdateXrayConfigRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Update Xray configuration (admin only)"""
    return await client.post("/xray/update-config", json=config_data.model_dump(exclude_none=True))
