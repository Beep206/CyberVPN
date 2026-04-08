from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_remnawave_client, require_role

from .schemas import (
    CloneNodePluginRequest,
    CreateNodePluginRequest,
    DeleteNodePluginResponse,
    NodePluginCollectionResponse,
    NodePluginResponse,
    PluginExecutorRequest,
    PluginExecutorResponse,
    ReorderNodePluginsRequest,
    TorrentBlockerReportsQuery,
    TorrentBlockerReportsResponse,
    TorrentBlockerReportsStatsResponse,
    UpdateNodePluginRequest,
)

router = APIRouter(prefix="/node-plugins", tags=["node-plugins"])


@router.get("/torrent-blocker/reports", response_model=TorrentBlockerReportsResponse)
async def get_torrent_blocker_reports(
    query: TorrentBlockerReportsQuery = Depends(),
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> TorrentBlockerReportsResponse:
    result = await client.get_validated(
        "/node-plugins/torrent-blocker",
        TorrentBlockerReportsResponse,
        params=query.model_dump(by_alias=True, exclude_none=True),
    )
    route_operations_total.labels(route="node_plugins", action="torrent_reports", status="success").inc()
    return result


@router.get("/torrent-blocker/stats", response_model=TorrentBlockerReportsStatsResponse)
async def get_torrent_blocker_stats(
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> TorrentBlockerReportsStatsResponse:
    result = await client.get_validated(
        "/node-plugins/torrent-blocker/reports/stats",
        TorrentBlockerReportsStatsResponse,
    )
    route_operations_total.labels(route="node_plugins", action="torrent_stats", status="success").inc()
    return result


@router.delete("/torrent-blocker/reports", response_model=TorrentBlockerReportsResponse)
async def truncate_torrent_blocker_reports(
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> TorrentBlockerReportsResponse:
    result = await client.delete_validated(
        "/node-plugins/torrent-blocker/truncate",
        TorrentBlockerReportsResponse,
    )
    route_operations_total.labels(route="node_plugins", action="torrent_truncate", status="success").inc()
    return result


@router.get("/", response_model=NodePluginCollectionResponse)
async def list_node_plugins(
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> NodePluginCollectionResponse:
    result = await client.get_validated("/node-plugins", NodePluginCollectionResponse)
    route_operations_total.labels(route="node_plugins", action="list", status="success").inc()
    return result


@router.post("/", response_model=NodePluginResponse)
async def create_node_plugin(
    body: CreateNodePluginRequest,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> NodePluginResponse:
    result = await client.post_validated("/node-plugins", NodePluginResponse, json=body.model_dump(by_alias=True))
    route_operations_total.labels(route="node_plugins", action="create", status="success").inc()
    return result


@router.post("/reorder", response_model=NodePluginCollectionResponse)
async def reorder_node_plugins(
    body: ReorderNodePluginsRequest,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> NodePluginCollectionResponse:
    result = await client.post_validated(
        "/node-plugins/actions/reorder",
        NodePluginCollectionResponse,
        json=body.model_dump(by_alias=True),
    )
    route_operations_total.labels(route="node_plugins", action="reorder", status="success").inc()
    return result


@router.post("/clone", response_model=NodePluginResponse)
async def clone_node_plugin(
    body: CloneNodePluginRequest,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> NodePluginResponse:
    result = await client.post_validated(
        "/node-plugins/actions/clone",
        NodePluginResponse,
        json=body.model_dump(by_alias=True),
    )
    route_operations_total.labels(route="node_plugins", action="clone", status="success").inc()
    return result


@router.post("/execute", response_model=PluginExecutorResponse)
async def execute_node_plugin(
    body: PluginExecutorRequest,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> PluginExecutorResponse:
    result = await client.post_validated(
        "/node-plugins/executor",
        PluginExecutorResponse,
        json=body.model_dump(by_alias=True),
    )
    route_operations_total.labels(route="node_plugins", action="execute", status="success").inc()
    return result


@router.get("/{uuid}", response_model=NodePluginResponse)
async def get_node_plugin(
    uuid: str,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> NodePluginResponse:
    result = await client.get_validated(f"/node-plugins/{uuid}", NodePluginResponse)
    route_operations_total.labels(route="node_plugins", action="get", status="success").inc()
    return result


@router.put("/{uuid}", response_model=NodePluginResponse)
async def update_node_plugin(
    uuid: str,
    body: UpdateNodePluginRequest,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> NodePluginResponse:
    payload = body.model_dump(by_alias=True, exclude_none=True)
    payload["uuid"] = uuid
    result = await client.patch_validated("/node-plugins", NodePluginResponse, json=payload)
    route_operations_total.labels(route="node_plugins", action="update", status="success").inc()
    return result


@router.delete("/{uuid}", response_model=DeleteNodePluginResponse)
async def delete_node_plugin(
    uuid: str,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> DeleteNodePluginResponse:
    result = await client.delete_validated(f"/node-plugins/{uuid}", DeleteNodePluginResponse)
    route_operations_total.labels(route="node_plugins", action="delete", status="success").inc()
    return result
