from fastapi import APIRouter, Depends
from src.presentation.dependencies import require_role, get_remnawave_client
from src.infrastructure.remnawave.client import RemnawaveClient

from .schemas import UpdateXrayConfigRequest

router = APIRouter(prefix="/xray", tags=["xray"])

@router.get("/config")
async def get_xray_config(
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Get current Xray configuration (admin only)"""
    return await client.get("/xray/config")

@router.post("/update-config")
async def update_xray_config(
    config_data: UpdateXrayConfigRequest,
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Update Xray configuration (admin only)"""
    return await client.post("/xray/update-config", json=config_data.model_dump(exclude_none=True))
