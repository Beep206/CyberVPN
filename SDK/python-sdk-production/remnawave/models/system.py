import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from remnawave.enums import ResponseType
from remnawave.models.subscriptions_settings import ResponseRule, ResponseRules


class NodeStatistic(BaseModel):
    node_name: str = Field(alias="nodeName")
    date: datetime.date
    total_bytes: int = Field(alias="totalBytes")


class NodesStatisticResponseDto(BaseModel):
    last_seven_days: List[NodeStatistic] = Field(alias="lastSevenDays")


class BandwidthStatistic(BaseModel):
    current: str
    previous: str
    difference: str


class BandwidthStatisticResponseDto(BaseModel):
    last_two_days: BandwidthStatistic = Field(alias="bandwidthLastTwoDays")
    last_seven_days: BandwidthStatistic = Field(alias="bandwidthLastSevenDays")
    last_30_days: BandwidthStatistic = Field(alias="bandwidthLast30Days")
    calendar_month: BandwidthStatistic = Field(alias="bandwidthCalendarMonth")
    current_year: BandwidthStatistic = Field(alias="bandwidthCurrentYear")


class CPUStatistic(BaseModel):
    cores: int


class MemoryStatistic(BaseModel):
    total: int
    free: int
    used: int


class StatusCounts(BaseModel):
    model_config = {"extra": "allow"}

    def __getitem__(self, key: str) -> int:
        return getattr(self, key, 0)

    def get(self, key: str, default: int = 0) -> int:
        return getattr(self, key, default)


class UsersStatistic(BaseModel):
    status_counts: StatusCounts = Field(alias="statusCounts")
    total_users: int = Field(alias="totalUsers")


class OnlineStatistic(BaseModel):
    last_day: int = Field(alias="lastDay")
    last_week: int = Field(alias="lastWeek")
    never_online: int = Field(alias="neverOnline")
    online_now: int = Field(alias="onlineNow")


class NodesStatistic(BaseModel):
    total_online: int = Field(alias="totalOnline")
    total_bytes_lifetime: str = Field(alias="totalBytesLifetime")


class StatisticResponseDto(BaseModel):
    cpu: CPUStatistic
    memory: MemoryStatistic
    uptime: float
    timestamp: int
    users: UsersStatistic
    online_stats: OnlineStatistic = Field(alias="onlineStats")
    nodes: NodesStatistic


class RuntimeMetric(BaseModel):
    rss: int
    heap_used: int = Field(alias="heapUsed")
    heap_total: int = Field(alias="heapTotal")
    external: int
    array_buffers: int = Field(alias="arrayBuffers")
    event_loop_delay_ms: float = Field(alias="eventLoopDelayMs")
    event_loop_p99_ms: float = Field(alias="eventLoopP99Ms")
    active_handles: int = Field(alias="activeHandles")
    uptime: float
    pid: int
    timestamp: int
    instance_id: str = Field(alias="instanceId")
    instance_type: str = Field(alias="instanceType")


class PM2Stat(RuntimeMetric):
    """Backward-compatible alias for the old health payload."""


class GetStatsResponseDto(StatisticResponseDto):
    pass


class GetBandwidthStatsResponseDto(BandwidthStatisticResponseDto):
    pass


class GetNodesStatisticsResponseDto(NodesStatisticResponseDto):
    pass


class GetRemnawaveHealthResponseDto(BaseModel):
    runtime_metrics: List[RuntimeMetric] = Field(alias="runtimeMetrics")


class NodeTrafficStat(BaseModel):
    tag: str
    upload: str
    download: str


class NodeMetric(BaseModel):
    node_uuid: str = Field(alias="nodeUuid")
    node_name: str = Field(alias="nodeName")
    country_emoji: str = Field(alias="countryEmoji")
    provider_name: str = Field(alias="providerName")
    users_online: int = Field(alias="usersOnline")
    inbounds_stats: List[NodeTrafficStat] = Field(alias="inboundsStats")
    outbounds_stats: List[NodeTrafficStat] = Field(alias="outboundsStats")


class GetNodesMetricsResponseDto(BaseModel):
    nodes: List[NodeMetric]


class MetadataBuildInfo(BaseModel):
    time: str
    number: str


class MetadataGitBackendInfo(BaseModel):
    commit_sha: str = Field(alias="commitSha")
    branch: str
    commit_url: str = Field(alias="commitUrl")


class MetadataGitFrontendInfo(BaseModel):
    commit_sha: str = Field(alias="commitSha")
    commit_url: str = Field(alias="commitUrl")


class MetadataGitInfo(BaseModel):
    backend: MetadataGitBackendInfo
    frontend: MetadataGitFrontendInfo


class GetMetadataResponseDto(BaseModel):
    version: str
    build: MetadataBuildInfo
    git: MetadataGitInfo


class RecapPeriodDto(BaseModel):
    users: int
    traffic: str


class RecapTotalDto(BaseModel):
    users: int
    nodes: int
    traffic: str
    nodes_ram: str = Field(alias="nodesRam")
    nodes_cpu_cores: int = Field(alias="nodesCpuCores")
    distinct_countries: int = Field(alias="distinctCountries")


class GetRecapResponseDto(BaseModel):
    this_month: RecapPeriodDto = Field(alias="thisMonth")
    total: RecapTotalDto
    version: str
    init_date: datetime.datetime = Field(alias="initDate")


class X25519KeyPair(BaseModel):
    public_key: str = Field(alias="publicKey")
    private_key: str = Field(alias="privateKey")


class GetX25519KeyPairResponseDto(BaseModel):
    key_pairs: List[X25519KeyPair] = Field(alias="keyPairs")


class EncryptHappCryptoLinkRequestDto(BaseModel):
    link_to_encrypt: str = Field(serialization_alias="linkToEncrypt")


class EncryptHappCryptoLinkData(BaseModel):
    encrypted_link: str = Field(alias="encryptedLink")


class EncryptHappCryptoLinkResponseDto(EncryptHappCryptoLinkData):
    pass


class DebugSrrMatcherRequestDto(BaseModel):
    response_rules: ResponseRules = Field(serialization_alias="responseRules")


class DebugSrrMatcherData(BaseModel):
    matched: bool
    response_type: ResponseType = Field(alias="responseType")
    matched_rule: Optional[ResponseRule] = Field(alias="matchedRule")
    input_headers: Dict[str, str] = Field(alias="inputHeaders")
    output_headers: Dict[str, str] = Field(alias="outputHeaders")


class DebugSrrMatcherResponseDto(DebugSrrMatcherData):
    pass
