from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_remnawave_client, require_role

from .schemas import CreateHostRequest, UpdateHostRequest, HostResponse

router = APIRouter(prefix="/hosts", tags=["hosts"])


@router.get("/", response_model=list[HostResponse])
async def list_hosts(
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """List all VPN hosts (admin only)"""
    return await client.get("/hosts")


@router.post("/", response_model=HostResponse)
async def create_host(
    host_data: CreateHostRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Create a new VPN host (admin only)"""
    return await client.post("/hosts", json=host_data.model_dump())


@router.get("/{uuid}", response_model=HostResponse)
async def get_host(
    uuid: str,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Get host details (admin only)"""
    return await client.get(f"/hosts/{uuid}")


@router.put("/{uuid}", response_model=HostResponse)
async def update_host(
    uuid: str,
    host_data: UpdateHostRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Update host configuration (admin only)"""
    return await client.put(f"/hosts/{uuid}", json=host_data.model_dump(exclude_none=True))


@router.delete("/{uuid}")
async def delete_host(
    uuid: str,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Delete a host (admin only)"""
    return await client.delete(f"/hosts/{uuid}")
