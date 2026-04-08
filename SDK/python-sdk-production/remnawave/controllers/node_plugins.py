from typing import Annotated, Optional

from rapid_api_client import Path, Query
from rapid_api_client.annotations import PydanticBody

from remnawave.models import (
    CloneNodePluginRequestDto,
    CloneNodePluginResponseDto,
    CreateNodePluginRequestDto,
    CreateNodePluginResponseDto,
    DeleteNodePluginResponseDto,
    GetNodePluginResponseDto,
    GetNodePluginsResponseDto,
    GetTorrentBlockerReportsResponseDto,
    GetTorrentBlockerReportsStatsResponseDto,
    PluginExecutorRequestDto,
    PluginExecutorResponseDto,
    ReorderNodePluginsRequestDto,
    ReorderNodePluginsResponseDto,
    TruncateTorrentBlockerReportsResponseDto,
    UpdateNodePluginRequestDto,
    UpdateNodePluginResponseDto,
)
from remnawave.rapid import BaseController, delete, get, patch, post


class NodePluginsController(BaseController):
    @get("/node-plugins", response_class=GetNodePluginsResponseDto)
    async def get_node_plugins(
        self,
        start: Annotated[int, Query(default=0, ge=0, description="Offset for pagination")] = 0,
        size: Annotated[int, Query(default=25, ge=1, description="Page size for pagination")] = 25,
        filters: Annotated[Optional[str], Query(default=None, description="Tanstack filters JSON")] = None,
        filter_modes: Annotated[
            Optional[str], Query(default=None, alias="filterModes", description="Tanstack filter modes JSON")
        ] = None,
        global_filter_mode: Annotated[
            Optional[str], Query(default=None, alias="globalFilterMode", description="Global filter mode")
        ] = None,
        sorting: Annotated[Optional[str], Query(default=None, description="Tanstack sorting JSON")] = None,
    ) -> GetNodePluginsResponseDto:
        """Get Node Plugins"""
        ...

    @get("/node-plugins/{uuid}", response_class=GetNodePluginResponseDto)
    async def get_node_plugin(
        self,
        uuid: Annotated[str, Path(description="UUID of the node plugin")],
    ) -> GetNodePluginResponseDto:
        """Get Node Plugin"""
        ...

    @post("/node-plugins", response_class=CreateNodePluginResponseDto)
    async def create_node_plugin(
        self,
        body: Annotated[CreateNodePluginRequestDto, PydanticBody()],
    ) -> CreateNodePluginResponseDto:
        """Create Node Plugin"""
        ...

    @patch("/node-plugins", response_class=UpdateNodePluginResponseDto)
    async def update_node_plugin(
        self,
        body: Annotated[UpdateNodePluginRequestDto, PydanticBody()],
    ) -> UpdateNodePluginResponseDto:
        """Update Node Plugin"""
        ...

    @delete("/node-plugins/{uuid}", response_class=DeleteNodePluginResponseDto)
    async def delete_node_plugin(
        self,
        uuid: Annotated[str, Path(description="UUID of the node plugin")],
    ) -> DeleteNodePluginResponseDto:
        """Delete Node Plugin"""
        ...

    @post("/node-plugins/actions/reorder", response_class=ReorderNodePluginsResponseDto)
    async def reorder_node_plugins(
        self,
        body: Annotated[ReorderNodePluginsRequestDto, PydanticBody()],
    ) -> ReorderNodePluginsResponseDto:
        """Reorder Node Plugins"""
        ...

    @post("/node-plugins/actions/clone", response_class=CloneNodePluginResponseDto)
    async def clone_node_plugin(
        self,
        body: Annotated[CloneNodePluginRequestDto, PydanticBody()],
    ) -> CloneNodePluginResponseDto:
        """Clone Node Plugin"""
        ...

    @post("/node-plugins/executor", response_class=PluginExecutorResponseDto)
    async def execute_node_plugins_command(
        self,
        body: Annotated[PluginExecutorRequestDto, PydanticBody()],
    ) -> PluginExecutorResponseDto:
        """Execute Node Plugin Command"""
        ...

    @get("/node-plugins/torrent-blocker", response_class=GetTorrentBlockerReportsResponseDto)
    async def get_torrent_blocker_reports(
        self,
        start: Annotated[int, Query(default=0, ge=0, description="Offset for pagination")] = 0,
        size: Annotated[int, Query(default=25, ge=1, description="Page size for pagination")] = 25,
        filters: Annotated[Optional[str], Query(default=None, description="Tanstack filters JSON")] = None,
        filter_modes: Annotated[
            Optional[str], Query(default=None, alias="filterModes", description="Tanstack filter modes JSON")
        ] = None,
        global_filter_mode: Annotated[
            Optional[str], Query(default=None, alias="globalFilterMode", description="Global filter mode")
        ] = None,
        sorting: Annotated[Optional[str], Query(default=None, description="Tanstack sorting JSON")] = None,
    ) -> GetTorrentBlockerReportsResponseDto:
        """Get Torrent Blocker Reports"""
        ...

    @get("/node-plugins/torrent-blocker/stats", response_class=GetTorrentBlockerReportsStatsResponseDto)
    async def get_torrent_blocker_reports_stats(
        self,
    ) -> GetTorrentBlockerReportsStatsResponseDto:
        """Get Torrent Blocker Reports Stats"""
        ...

    @delete("/node-plugins/torrent-blocker/truncate", response_class=TruncateTorrentBlockerReportsResponseDto)
    async def truncate_torrent_blocker_reports(
        self,
    ) -> TruncateTorrentBlockerReportsResponseDto:
        """Truncate Torrent Blocker Reports"""
        ...
