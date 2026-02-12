from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_remnawave_client, require_role
from src.presentation.schemas.remnawave_responses import RemnawaveInboundResponse

router = APIRouter(prefix="/inbounds", tags=["inbounds"])


@router.get("/", response_model=list[RemnawaveInboundResponse])
async def list_inbounds(
    current_user=Depends(require_role(AdminRole.ADMIN)), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List all inbound configurations (admin only)"""
    result = await client.get("/inbounds")
    route_operations_total.labels(route="inbounds", action="list", status="success").inc()
    return result


@router.get("/{uuid}", response_model=RemnawaveInboundResponse)
async def get_inbound(
    uuid: str,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Get inbound configuration details (admin only)"""
    result = await client.get(f"/inbounds/{uuid}")
    route_operations_total.labels(route="inbounds", action="get", status="success").inc()
    return result
