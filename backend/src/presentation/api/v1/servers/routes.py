"""Server management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.servers.manage_servers import ManageServersUseCase
from src.application.use_cases.servers.server_stats import ServerStatsUseCase
from src.infrastructure.monitoring.instrumentation.routes import track_server_query
from src.infrastructure.remnawave.server_gateway import RemnawaveServerGateway
from src.presentation.api.v1.servers.schemas import (
    CreateServerRequest,
    ServerResponse,
    ServerStatsResponse,
    UpdateServerRequest,
)
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("/", response_model=list[ServerResponse])
async def list_servers(
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SERVER_READ)),
) -> list[ServerResponse]:
    """List all Remnawave VPN servers."""
    gateway = RemnawaveServerGateway(client=client)
    use_case = ManageServersUseCase(gateway=gateway)

    servers = await use_case.get_all()
    track_server_query(operation="list")


    return [
        ServerResponse(
            uuid=server.uuid,
            name=server.name,
            address=server.address,
            port=server.port,
            status=server.status,
            is_connected=server.is_connected,
            is_disabled=server.is_disabled,
            created_at=server.created_at,
            updated_at=server.updated_at,
            traffic_used_bytes=server.used_traffic_bytes or 0,
            inbound_count=server.inbound_count or 0,
            users_online=server.users_online or 0,
        )
        for server in servers
    ]


@router.post("/", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
async def create_server(
    request: CreateServerRequest,
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SERVER_CREATE)),
) -> ServerResponse:
    """Create a new Remnawave VPN server."""
    gateway = RemnawaveServerGateway(client=client)
    use_case = ManageServersUseCase(gateway=gateway)

    server = await use_case.create(
        name=request.name,
        address=request.address,
        port=request.port,
    )

    return ServerResponse(
        uuid=server.uuid,
        name=server.name,
        address=server.address,
        port=server.port,
        status=server.status,
        is_connected=server.is_connected,
        is_disabled=server.is_disabled,
        created_at=server.created_at,
        updated_at=server.updated_at,
        traffic_used_bytes=server.used_traffic_bytes or 0,
        inbound_count=server.inbound_count or 0,
        users_online=server.users_online or 0,
    )


@router.get("/stats", response_model=ServerStatsResponse)
async def get_server_stats(
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SERVER_READ)),
) -> ServerStatsResponse:
    """Get Remnawave server statistics by status."""
    gateway = RemnawaveServerGateway(client=client)
    use_case = ServerStatsUseCase(gateway=gateway)

    stats = await use_case.execute()

    return ServerStatsResponse(**stats)


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

    return ServerResponse(
        uuid=server.uuid,
        name=server.name,
        address=server.address,
        port=server.port,
        status=server.status,
        is_connected=server.is_connected,
        is_disabled=server.is_disabled,
        created_at=server.created_at,
        updated_at=server.updated_at,
        traffic_used_bytes=server.used_traffic_bytes or 0,
        inbound_count=server.inbound_count or 0,
        users_online=server.users_online or 0,
    )


@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: UUID,
    request: UpdateServerRequest,
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SERVER_UPDATE)),
) -> ServerResponse:
    """Update a Remnawave VPN server."""
    gateway = RemnawaveServerGateway(client=client)
    use_case = ManageServersUseCase(gateway=gateway)

    update_kwargs = {}
    if request.name is not None:
        update_kwargs["name"] = request.name
    if request.address is not None:
        update_kwargs["address"] = request.address
    if request.port is not None:
        update_kwargs["port"] = request.port

    server = await use_case.update(uuid=server_id, **update_kwargs)

    return ServerResponse(
        uuid=server.uuid,
        name=server.name,
        address=server.address,
        port=server.port,
        status=server.status,
        is_connected=server.is_connected,
        is_disabled=server.is_disabled,
        created_at=server.created_at,
        updated_at=server.updated_at,
        traffic_used_bytes=server.used_traffic_bytes or 0,
        inbound_count=server.inbound_count or 0,
        users_online=server.users_online or 0,
    )


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SERVER_DELETE)),
):
    """Delete a Remnawave VPN server."""
    gateway = RemnawaveServerGateway(client=client)
    use_case = ManageServersUseCase(gateway=gateway)

    await use_case.delete(uuid=server_id)
    return None
