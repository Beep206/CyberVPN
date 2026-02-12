from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_remnawave_client, require_role
from src.presentation.schemas.remnawave_responses import RemnawaveXrayConfigResponse

from .schemas import UpdateXrayConfigRequest

router = APIRouter(prefix="/xray", tags=["xray"])


@router.get("/config", response_model=RemnawaveXrayConfigResponse)
async def get_xray_config(
    current_user=Depends(require_role(AdminRole.ADMIN)), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Get current Xray configuration (admin only)"""
    result = await client.get("/xray/config")
    route_operations_total.labels(route="xray", action="get_config", status="success").inc()
    return result


@router.post("/update-config", response_model=RemnawaveXrayConfigResponse)
async def update_xray_config(
    config_data: UpdateXrayConfigRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Update Xray configuration (admin only)"""
    result = await client.post("/xray/update-config", json=config_data.model_dump(exclude_none=True))
    route_operations_total.labels(route="xray", action="update_config", status="success").inc()
    return result
