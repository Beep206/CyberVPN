"""Host management routes with response validation (HIGH-4).

Security improvements:
- All Remnawave responses are validated against schemas
- Unexpected fields are stripped
- Validation failures return 502 Bad Gateway
"""

from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_remnawave_client, require_role
from src.presentation.schemas.remnawave_responses import StatusMessageResponse

from .schemas import CreateHostRequest, HostResponse, UpdateHostRequest

router = APIRouter(prefix="/hosts", tags=["hosts"])


@router.get("/", response_model=list[HostResponse])
async def list_hosts(
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> list[HostResponse]:
    """List all VPN hosts (admin only)"""
    result = await client.get_list_validated("/hosts", HostResponse)
    route_operations_total.labels(route="hosts", action="list", status="success").inc()
    return result


@router.post("/", response_model=HostResponse)
async def create_host(
    host_data: CreateHostRequest,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> HostResponse:
    """Create a new VPN host (admin only)"""
    result = await client.post_validated("/hosts", HostResponse, json=host_data.model_dump())
    route_operations_total.labels(route="hosts", action="create", status="success").inc()
    return result


@router.get("/{uuid}", response_model=HostResponse)
async def get_host(
    uuid: str,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> HostResponse:
    """Get host details (admin only)"""
    result = await client.get_validated(f"/hosts/{uuid}", HostResponse)
    route_operations_total.labels(route="hosts", action="get", status="success").inc()
    return result


@router.put("/{uuid}", response_model=HostResponse)
async def update_host(
    uuid: str,
    host_data: UpdateHostRequest,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> HostResponse:
    """Update host configuration (admin only)"""
    result = await client.put_validated(
        f"/hosts/{uuid}",
        HostResponse,
        json=host_data.model_dump(exclude_none=True),
    )
    route_operations_total.labels(route="hosts", action="update", status="success").inc()
    return result


@router.delete("/{uuid}", response_model=StatusMessageResponse)
async def delete_host(
    uuid: str,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> StatusMessageResponse:
    """Delete a host (admin only)"""
    await client.delete(f"/hosts/{uuid}")
    route_operations_total.labels(route="hosts", action="delete", status="success").inc()
    return StatusMessageResponse(status="deleted", message="Host deleted successfully")
