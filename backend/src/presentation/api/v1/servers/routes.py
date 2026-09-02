"""Server management routes."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.servers.manage_servers import ManageServersUseCase
from src.application.use_cases.servers.server_stats import ServerStatsUseCase
from src.infrastructure.cache.response_cache import response_cache
from src.infrastructure.monitoring.instrumentation.routes import track_server_query
from src.infrastructure.remnawave.server_gateway import (
    RemnawaveNodeCreateSafetyDisabled,
    RemnawaveNodeMutationAcceptedPending,
    RemnawaveServerGateway,
)
from src.presentation.api.v1.servers.schemas import (
    CreateServerRequest,
    ServerIpResponse,
    ServerResponse,
    ServerStatsResponse,
    UpdateServerRequest,
)
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/servers", tags=["servers"])


def _serialize_server_response(server) -> ServerResponse:
    return ServerResponse(
        uuid=server.uuid,
        id=server.id,
        name=server.name,
        address=server.address,
        port=server.port,
        status=server.status,
        is_connected=server.is_connected,
        is_disabled=server.is_disabled,
        created_at=server.created_at,
        updated_at=server.updated_at,
        country_code=server.country_code,
        traffic_used_bytes=server.used_traffic_bytes or 0,
        inbound_count=server.inbound_count or 0,
        users_online=server.users_online or 0,
        xray_version=server.xray_version,
        node_version=server.node_version,
        vpn_protocol=server.vpn_protocol,
        active_plugin_uuid=server.active_plugin_uuid,
        ips=[ServerIpResponse(ip=item.ip, status=item.status) for item in server.ips],
        integration_uuids=list(server.integration_uuids),
    )


@router.get("/", response_model=list[ServerResponse])
@router.get("", response_model=list[ServerResponse], include_in_schema=False)
async def list_servers(
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SERVER_READ)),
) -> list[ServerResponse]:
    """List global Remnawave VPN servers for authorized administrators."""

    async def _fetch() -> list[dict]:
        gateway = RemnawaveServerGateway(client=client)
        use_case = ManageServersUseCase(gateway=gateway)

        try:
            servers = await use_case.get_all()
        except Exception:
            logger.warning("Remnawave unavailable for server list")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "remnawave_servers_unavailable"},
            ) from None

        track_server_query(operation="list")

        return [_serialize_server_response(server).model_dump(mode="json") for server in servers]

    return await response_cache.get_or_fetch("servers:list", 30, _fetch)


@router.post(
    "/",
    response_model=ServerResponse,
    status_code=status.HTTP_201_CREATED,
    responses={503: {"description": "Node creation is safety-disabled pending durable settlement"}},
)
async def create_server(
    request: CreateServerRequest,
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SERVER_CREATE)),
) -> ServerResponse | Response:
    """Create a new Remnawave VPN server."""
    gateway = RemnawaveServerGateway(client=client)
    use_case = ManageServersUseCase(gateway=gateway)

    try:
        server = await use_case.create(
            name=request.name,
            address=request.address,
            port=request.port,
        )
    except RemnawaveNodeCreateSafetyDisabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": RemnawaveNodeCreateSafetyDisabled.error_code},
        ) from None

    await response_cache.invalidate("servers:list", "servers:stats")

    if server is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)

    return _serialize_server_response(server)


@router.get("/stats", response_model=ServerStatsResponse)
@router.get("/stats/", response_model=ServerStatsResponse, include_in_schema=False)
async def get_server_stats(
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SERVER_READ)),
) -> ServerStatsResponse:
    """Get global Remnawave server statistics for authorized administrators."""

    async def _fetch() -> dict:
        gateway = RemnawaveServerGateway(client=client)
        use_case = ServerStatsUseCase(gateway=gateway)

        try:
            stats = await use_case.execute()
        except Exception:
            logger.warning("Remnawave unavailable for server stats")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "remnawave_server_stats_unavailable"},
            ) from None

        return ServerStatsResponse(**stats).model_dump()

    return await response_cache.get_or_fetch("servers:stats", 15, _fetch)


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SERVER_READ)),
) -> ServerResponse:
    """Get a specific Remnawave VPN server by UUID."""
    gateway = RemnawaveServerGateway(client=client)
    use_case = ManageServersUseCase(gateway=gateway)

    server = await use_case.get_by_uuid(uuid=server_id)

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server with UUID {server_id} not found",
        )

    return _serialize_server_response(server)


@router.put(
    "/{server_id}",
    response_model=ServerResponse,
    responses={202: {"description": "Update accepted; authoritative node state is not visible yet"}},
)
async def update_server(
    server_id: UUID,
    request: UpdateServerRequest,
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SERVER_UPDATE)),
) -> ServerResponse | Response:
    """Update a Remnawave VPN server."""
    gateway = RemnawaveServerGateway(client=client)
    use_case = ManageServersUseCase(gateway=gateway)

    update_kwargs: dict[str, object] = {}
    if request.name is not None:
        update_kwargs["name"] = request.name
    if request.address is not None:
        update_kwargs["address"] = request.address
    if request.port is not None:
        update_kwargs["port"] = request.port

    try:
        server = await use_case.update(uuid=server_id, **update_kwargs)
    except RemnawaveNodeMutationAcceptedPending:
        return Response(status_code=status.HTTP_202_ACCEPTED)

    await response_cache.invalidate("servers:list", "servers:stats")

    if server is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)

    return _serialize_server_response(server)


@router.delete(
    "/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={202: {"description": "Delete accepted; authoritative absence is not visible yet"}},
)
async def delete_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SERVER_DELETE)),
):
    """Delete a Remnawave VPN server."""
    gateway = RemnawaveServerGateway(client=client)
    use_case = ManageServersUseCase(gateway=gateway)

    try:
        await use_case.delete(uuid=server_id)
    except RemnawaveNodeMutationAcceptedPending:
        return Response(status_code=status.HTTP_202_ACCEPTED)

    await response_cache.invalidate("servers:list", "servers:stats")

    return None
