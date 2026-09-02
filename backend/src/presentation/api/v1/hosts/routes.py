"""Admin proxy for the exact Remnawave 3.4.3 host contract."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.domain.enums import AdminRole
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.control_plane_gateways import (
    RemnawaveHostControlPlaneGateway,
    RemnawaveHostCreateSafetyDisabled,
    RemnawaveHostMutationAcceptedPending,
)
from src.presentation.api.v1.remnawave_degraded import optional_remnawave_read
from src.presentation.dependencies import get_remnawave_client, require_role

from .schemas import CreateHostRequest, HostResponse, UpdateHostRequest

router = APIRouter(prefix="/hosts", tags=["hosts"])


@router.get("/", response_model=list[HostResponse])
async def list_hosts(
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> list[HostResponse]:
    """List all VPN hosts (admin only)"""
    return await optional_remnawave_read(
        route="hosts",
        action="list",
        fetch=lambda: client.get_collection_validated("/hosts", "hosts", HostResponse),
        fallback=[],
    )


@router.post(
    "/",
    response_model=HostResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Host creation is safety-disabled pending durable settlement",
        }
    },
)
async def create_host(
    host_data: CreateHostRequest,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> HostResponse:
    """Refuse duplicate-prone create until CyberVPN owns durable settlement."""
    try:
        return await RemnawaveHostControlPlaneGateway(client).create(host_data.to_upstream_payload())
    except RemnawaveHostCreateSafetyDisabled as exc:
        route_operations_total.labels(route="hosts", action="create", status="safety_disabled").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.error_code},
        ) from exc


@router.get("/{uuid}", response_model=HostResponse)
async def get_host(
    uuid: UUID,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> HostResponse:
    """Get host details (admin only)"""
    result = await client.get_validated(f"/hosts/{uuid}", HostResponse)
    route_operations_total.labels(route="hosts", action="get", status="success").inc()
    return result


@router.put(
    "/{uuid}",
    response_model=HostResponse,
    responses={202: {"description": "Update accepted by Remnawave without a response body"}},
)
async def update_host(
    uuid: UUID,
    host_data: UpdateHostRequest,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> HostResponse | Response:
    """Update host configuration (admin only)"""
    try:
        result = await RemnawaveHostControlPlaneGateway(client).update(uuid, host_data.to_upstream_payload())
    except RemnawaveHostMutationAcceptedPending:
        route_operations_total.labels(route="hosts", action="update", status="pending").inc()
        return Response(status_code=status.HTTP_202_ACCEPTED, headers={"Retry-After": "30"})
    route_operations_total.labels(route="hosts", action="update", status="success").inc()
    return HostResponse.model_validate(result.model_dump(by_alias=True, mode="json"))


@router.delete("/{uuid}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_host(
    uuid: UUID,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> Response:
    """Delete a host (admin only)"""
    await client.delete_validated(f"/hosts/{uuid}")
    route_operations_total.labels(route="hosts", action="delete", status="success").inc()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
