from fastapi import APIRouter, Depends, Response, status

from src.domain.enums import AdminRole
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveXrayConfigResponse
from src.presentation.api.v1.remnawave_degraded import optional_remnawave_read
from src.presentation.dependencies import get_remnawave_client, require_role

from .schemas import UpdateXrayConfigRequest

router = APIRouter(prefix="/xray", tags=["xray"])


@router.get("/config", response_model=RemnawaveXrayConfigResponse)
async def get_xray_config(
    current_user=Depends(require_role(AdminRole.ADMIN)), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Get current Xray configuration (admin only)"""
    return await optional_remnawave_read(
        route="xray",
        action="get_config",
        fetch=lambda: client.get_validated("/xray/config", RemnawaveXrayConfigResponse),
        fallback=RemnawaveXrayConfigResponse(log={}, inbounds=[], outbounds=[], routing={"rules": []}),
    )


@router.post(
    "/update-config",
    response_model=RemnawaveXrayConfigResponse,
    responses={202: {"description": "Configuration update accepted by Remnawave without a response body"}},
)
async def update_xray_config(
    config_data: UpdateXrayConfigRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Update Xray configuration (admin only)"""
    result = await client.post_validated(
        "/xray/update-config",
        RemnawaveXrayConfigResponse,
        json=config_data.model_dump(exclude_none=True),
    )
    route_operations_total.labels(route="xray", action="update_config", status="success").inc()
    if result is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)
    return result
