from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NodePluginBaseModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="allow",
    )


class SharedListResponse(NodePluginBaseModel):
    name: str
    type: Literal["ipList"]
    items: list[str]


class TorrentBlockerIgnoreListsResponse(NodePluginBaseModel):
    ip: list[str] | None = None
    user_id: list[int] | None = Field(default=None, alias="userId")


class TorrentBlockerPluginConfigResponse(NodePluginBaseModel):
    enabled: bool
    block_duration: int = Field(alias="blockDuration")
    ignore_lists: TorrentBlockerIgnoreListsResponse = Field(alias="ignoreLists")
    include_rule_tags: list[str] | None = Field(default=None, alias="includeRuleTags")


class ConnectionDropPluginConfigResponse(NodePluginBaseModel):
    enabled: bool
    whitelist_ips: list[str] = Field(alias="whitelistIps")


class IngressFilterPluginConfigResponse(NodePluginBaseModel):
    enabled: bool
    blocked_ips: list[str] = Field(alias="blockedIps")


class EgressFilterPluginConfigResponse(NodePluginBaseModel):
    enabled: bool
    blocked_ips: list[str] | None = Field(default=None, alias="blockedIps")
    blocked_ports: list[int] | None = Field(default=None, alias="blockedPorts")


class NodePluginConfigResponse(NodePluginBaseModel):
    shared_lists: list[SharedListResponse] = Field(default_factory=list, alias="sharedLists")
    torrent_blocker: TorrentBlockerPluginConfigResponse | None = Field(default=None, alias="torrentBlocker")
    ingress_filter: IngressFilterPluginConfigResponse | None = Field(default=None, alias="ingressFilter")
    egress_filter: EgressFilterPluginConfigResponse | None = Field(default=None, alias="egressFilter")
    connection_drop: ConnectionDropPluginConfigResponse | None = Field(default=None, alias="connectionDrop")


class NodePluginResponse(NodePluginBaseModel):
    uuid: str
    view_position: int = Field(alias="viewPosition")
    name: str
    plugin_config: NodePluginConfigResponse | dict[str, Any] | None = Field(default=None, alias="pluginConfig")


class NodePluginCollectionResponse(NodePluginBaseModel):
    total: int
    node_plugins: list[NodePluginResponse] = Field(alias="nodePlugins")


class CreateNodePluginRequest(NodePluginBaseModel):
    name: str


class UpdateNodePluginRequest(NodePluginBaseModel):
    uuid: str | None = None
    name: str | None = None
    plugin_config: NodePluginConfigResponse | dict[str, Any] | None = Field(default=None, alias="pluginConfig")


class DeleteNodePluginResponse(NodePluginBaseModel):
    is_deleted: bool = Field(alias="isDeleted")


class ReorderNodePluginItem(NodePluginBaseModel):
    uuid: str
    view_position: int = Field(alias="viewPosition")


class ReorderNodePluginsRequest(NodePluginBaseModel):
    items: list[ReorderNodePluginItem]


class CloneNodePluginRequest(NodePluginBaseModel):
    clone_from_uuid: str = Field(alias="cloneFromUuid")


class PluginExecutorRequest(NodePluginBaseModel):
    command: dict[str, Any]
    target_nodes: dict[str, Any] = Field(alias="targetNodes")


class PluginExecutorResponse(NodePluginBaseModel):
    event_sent: bool = Field(alias="eventSent")


class TorrentBlockerReportsQuery(NodePluginBaseModel):
    start: int | None = None
    size: int | None = None
    filters: str | None = None
    filter_modes: str | None = Field(default=None, alias="filterModes")
    global_filter_mode: str | None = Field(default=None, alias="globalFilterMode")
    sorting: str | None = None


class TorrentBlockerUserResponse(NodePluginBaseModel):
    uuid: str
    username: str


class TorrentBlockerNodeResponse(NodePluginBaseModel):
    uuid: str
    name: str
    country_code: str = Field(alias="countryCode")


class TorrentBlockerActionReportResponse(NodePluginBaseModel):
    blocked: bool
    ip: str
    block_duration: int = Field(alias="blockDuration")
    will_unblock_at: datetime = Field(alias="willUnblockAt")
    user_id: str = Field(alias="userId")
    processed_at: datetime = Field(alias="processedAt")


class TorrentBlockerXrayReportResponse(NodePluginBaseModel):
    email: str | None = None
    level: int | None = None
    protocol: str | None = None
    network: str
    source: str | None = None
    destination: str
    route_target: str | None = Field(default=None, alias="routeTarget")
    original_target: str | None = Field(default=None, alias="originalTarget")
    inbound_tag: str | None = Field(default=None, alias="inboundTag")
    inbound_name: str | None = Field(default=None, alias="inboundName")
    inbound_local: str | None = Field(default=None, alias="inboundLocal")
    outbound_tag: str | None = Field(default=None, alias="outboundTag")
    ts: int


class TorrentBlockerReportPayloadResponse(NodePluginBaseModel):
    action_report: TorrentBlockerActionReportResponse = Field(alias="actionReport")
    xray_report: TorrentBlockerXrayReportResponse = Field(alias="xrayReport")


class TorrentBlockerReportResponse(NodePluginBaseModel):
    id: int
    user_id: int = Field(alias="userId")
    node_id: int = Field(alias="nodeId")
    user: TorrentBlockerUserResponse
    node: TorrentBlockerNodeResponse
    report: TorrentBlockerReportPayloadResponse
    created_at: datetime = Field(alias="createdAt")


class TorrentBlockerReportsResponse(NodePluginBaseModel):
    records: list[TorrentBlockerReportResponse]
    total: int


class TorrentBlockerStatsResponse(NodePluginBaseModel):
    distinct_nodes: int = Field(alias="distinctNodes")
    distinct_users: int = Field(alias="distinctUsers")
    total_reports: int = Field(alias="totalReports")
    reports_last_24_hours: int = Field(alias="reportsLast24Hours")


class TorrentBlockerTopEntityResponse(NodePluginBaseModel):
    uuid: str
    color: str
    total: int
    username: str | None = None
    name: str | None = None
    country_code: str | None = Field(default=None, alias="countryCode")


class TorrentBlockerReportsStatsResponse(NodePluginBaseModel):
    stats: TorrentBlockerStatsResponse
    top_users: list[TorrentBlockerTopEntityResponse] = Field(alias="topUsers")
    top_nodes: list[TorrentBlockerTopEntityResponse] = Field(alias="topNodes")
