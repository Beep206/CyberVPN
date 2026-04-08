from __future__ import annotations

import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SharedListDto(BaseModel):
    name: str
    type: Literal["ipList"]
    items: List[str]


class TorrentBlockerIgnoreListsDto(BaseModel):
    ip: Optional[List[str]] = None
    user_id: Optional[List[int]] = Field(default=None, alias="userId")


class TorrentBlockerPluginConfigDto(BaseModel):
    enabled: bool
    block_duration: int = Field(alias="blockDuration")
    ignore_lists: TorrentBlockerIgnoreListsDto = Field(alias="ignoreLists")
    include_rule_tags: Optional[List[str]] = Field(default=None, alias="includeRuleTags")


class ConnectionDropPluginConfigDto(BaseModel):
    enabled: bool
    whitelist_ips: List[str] = Field(alias="whitelistIps")


class IngressFilterPluginConfigDto(BaseModel):
    enabled: bool
    blocked_ips: List[str] = Field(alias="blockedIps")


class EgressFilterPluginConfigDto(BaseModel):
    enabled: bool
    blocked_ips: Optional[List[str]] = Field(default=None, alias="blockedIps")
    blocked_ports: Optional[List[int]] = Field(default=None, alias="blockedPorts")


class NodePluginConfigDto(BaseModel):
    model_config = {"extra": "allow"}

    shared_lists: List[SharedListDto] = Field(default_factory=list, alias="sharedLists")
    torrent_blocker: Optional[TorrentBlockerPluginConfigDto] = Field(default=None, alias="torrentBlocker")
    ingress_filter: Optional[IngressFilterPluginConfigDto] = Field(default=None, alias="ingressFilter")
    egress_filter: Optional[EgressFilterPluginConfigDto] = Field(default=None, alias="egressFilter")
    connection_drop: Optional[ConnectionDropPluginConfigDto] = Field(default=None, alias="connectionDrop")


class NodePluginDto(BaseModel):
    uuid: str
    view_position: int = Field(alias="viewPosition")
    name: str
    plugin_config: NodePluginConfigDto | Dict[str, Any] | None = Field(default=None, alias="pluginConfig")


class GetNodePluginsResponseDto(BaseModel):
    total: int
    node_plugins: List[NodePluginDto] = Field(alias="nodePlugins")


class GetNodePluginResponseDto(NodePluginDto):
    pass


class CreateNodePluginRequestDto(BaseModel):
    name: str


class CreateNodePluginResponseDto(NodePluginDto):
    pass


class UpdateNodePluginRequestDto(BaseModel):
    uuid: str
    name: Optional[str] = None
    plugin_config: NodePluginConfigDto | Dict[str, Any] | None = Field(default=None, alias="pluginConfig")


class UpdateNodePluginResponseDto(NodePluginDto):
    pass


class DeleteNodePluginResponseDto(BaseModel):
    is_deleted: bool = Field(alias="isDeleted")


class ReorderNodePluginItem(BaseModel):
    uuid: str
    view_position: int = Field(alias="viewPosition")


class ReorderNodePluginsRequestDto(BaseModel):
    items: List[ReorderNodePluginItem]


class ReorderNodePluginsResponseDto(BaseModel):
    total: int
    node_plugins: List[NodePluginDto] = Field(alias="nodePlugins")


class CloneNodePluginRequestDto(BaseModel):
    clone_from_uuid: str = Field(alias="cloneFromUuid")


class CloneNodePluginResponseDto(NodePluginDto):
    pass


class PluginExecutorRequestDto(BaseModel):
    command: Dict[str, Any]
    target_nodes: Dict[str, Any] = Field(alias="targetNodes")


class PluginExecutorResponseDto(BaseModel):
    event_sent: bool = Field(alias="eventSent")


class TorrentBlockerUserDto(BaseModel):
    uuid: str
    username: str


class TorrentBlockerNodeDto(BaseModel):
    uuid: str
    name: str
    country_code: str = Field(alias="countryCode")


class TorrentBlockerActionReportDto(BaseModel):
    blocked: bool
    ip: str
    block_duration: int = Field(alias="blockDuration")
    will_unblock_at: datetime.datetime = Field(alias="willUnblockAt")
    user_id: str = Field(alias="userId")
    processed_at: datetime.datetime = Field(alias="processedAt")


class TorrentBlockerXrayReportDto(BaseModel):
    email: Optional[str] = None
    level: Optional[int] = None
    protocol: Optional[str] = None
    network: str
    source: Optional[str] = None
    destination: str
    route_target: Optional[str] = Field(default=None, alias="routeTarget")
    original_target: Optional[str] = Field(default=None, alias="originalTarget")
    inbound_tag: Optional[str] = Field(default=None, alias="inboundTag")
    inbound_name: Optional[str] = Field(default=None, alias="inboundName")
    inbound_local: Optional[str] = Field(default=None, alias="inboundLocal")
    outbound_tag: Optional[str] = Field(default=None, alias="outboundTag")
    ts: int


class TorrentBlockerReportPayloadDto(BaseModel):
    action_report: TorrentBlockerActionReportDto = Field(alias="actionReport")
    xray_report: TorrentBlockerXrayReportDto = Field(alias="xrayReport")


class TorrentBlockerReportDto(BaseModel):
    id: int
    user_id: int = Field(alias="userId")
    node_id: int = Field(alias="nodeId")
    user: TorrentBlockerUserDto
    node: TorrentBlockerNodeDto
    report: TorrentBlockerReportPayloadDto
    created_at: datetime.datetime = Field(alias="createdAt")


class GetTorrentBlockerReportsResponseDto(BaseModel):
    records: List[TorrentBlockerReportDto]
    total: int


class TorrentBlockerStatsDto(BaseModel):
    distinct_nodes: int = Field(alias="distinctNodes")
    distinct_users: int = Field(alias="distinctUsers")
    total_reports: int = Field(alias="totalReports")
    reports_last_24_hours: int = Field(alias="reportsLast24Hours")


class TorrentBlockerTopEntityDto(BaseModel):
    uuid: str
    color: str
    total: int
    username: Optional[str] = None
    name: Optional[str] = None
    country_code: Optional[str] = Field(default=None, alias="countryCode")


class GetTorrentBlockerReportsStatsResponseDto(BaseModel):
    stats: TorrentBlockerStatsDto
    top_users: List[TorrentBlockerTopEntityDto] = Field(alias="topUsers")
    top_nodes: List[TorrentBlockerTopEntityDto] = Field(alias="topNodes")


class TruncateTorrentBlockerReportsResponseDto(GetTorrentBlockerReportsResponseDto):
    pass
