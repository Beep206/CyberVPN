from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PublicNetworkEnvelope(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_version: str = Field(..., alias="schemaVersion")
    generated_at: datetime = Field(..., alias="generatedAt")
    expires_at: datetime = Field(..., alias="expiresAt")
    freshness_status: Literal["fresh", "stale", "degraded"] = Field(..., alias="freshnessStatus")


class PublicNetworkOverviewGlobalResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: Literal["online", "degraded", "major_outage"] = Field(...)
    total_users: int = Field(..., alias="totalUsers")
    active_users: int = Field(..., alias="activeUsers")
    total_servers: int = Field(..., alias="totalServers")
    online_servers: int = Field(..., alias="onlineServers")
    total_nodes: int = Field(..., alias="totalNodes")
    distinct_countries: int = Field(..., alias="distinctCountries")
    total_traffic_bytes: int = Field(..., alias="totalTrafficBytes")
    monthly_traffic_bytes: int = Field(..., alias="monthlyTrafficBytes")
    today_bytes_in: int = Field(..., alias="todayBytesIn")
    today_bytes_out: int = Field(..., alias="todayBytesOut")


class PublicNetworkOverviewResponse(PublicNetworkEnvelope):
    global_metrics: PublicNetworkOverviewGlobalResponse = Field(..., alias="global")


class PublicNetworkRegionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    country_code: str = Field(..., alias="countryCode")
    public_name: str = Field(..., alias="publicName")
    status: Literal["online", "degraded", "offline"]
    total_servers: int = Field(..., alias="totalServers")
    online_servers: int = Field(..., alias="onlineServers")
    active_users: int = Field(..., alias="activeUsers")
    total_traffic_bytes: int = Field(..., alias="totalTrafficBytes")


class PublicNetworkRegionsResponse(PublicNetworkEnvelope):
    regions: list[PublicNetworkRegionResponse]


class PublicNetworkRegionDetailResponse(PublicNetworkEnvelope):
    region: PublicNetworkRegionResponse


class PublicNetworkLeaderboardEntryResponse(PublicNetworkRegionResponse):
    rank: int


class PublicNetworkLeaderboardResponse(PublicNetworkEnvelope):
    leaderboard: list[PublicNetworkLeaderboardEntryResponse]


class PublicNetworkUptimeSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: Literal["online", "degraded", "major_outage"] = Field(...)
    current_availability_pct: float = Field(..., alias="currentAvailabilityPct")
    history_available: bool = Field(..., alias="historyAvailable")
    window_days: int = Field(..., alias="windowDays")
    coverage_days: int = Field(..., alias="coverageDays")


class PublicNetworkUptimeHistoryDayResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    date: str
    status: Literal["nominal", "warning", "outage", "maintenance"]


class PublicNetworkUptimeResponse(PublicNetworkEnvelope):
    summary: PublicNetworkUptimeSummaryResponse
    history: list[PublicNetworkUptimeHistoryDayResponse]


class PublicNetworkIncidentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    severity: Literal["minor", "major", "critical"]
    status: Literal["investigating", "identified", "monitoring", "resolved"]
    public_title: str = Field(..., alias="publicTitle")
    public_summary: str = Field(..., alias="publicSummary")
    affected_regions: list[str] = Field(default_factory=list, alias="affectedRegions")
    started_at: datetime = Field(..., alias="startedAt")
    resolved_at: datetime | None = Field(None, alias="resolvedAt")


class PublicNetworkIncidentsResponse(PublicNetworkEnvelope):
    incidents: list[PublicNetworkIncidentResponse]


class PublicNetworkWidgetSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: Literal["online", "degraded", "major_outage"] = Field(...)
    current_availability_pct: float = Field(..., alias="currentAvailabilityPct")
    online_servers: int = Field(..., alias="onlineServers")
    active_users: int = Field(..., alias="activeUsers")
    monthly_traffic_bytes: int = Field(..., alias="monthlyTrafficBytes")
    incidents_count: int = Field(..., alias="incidentsCount")


class PublicNetworkWidgetResponse(PublicNetworkEnvelope):
    widget_type: Literal["network_card", "uptime_badge", "speed_badge"] = Field(..., alias="widgetType")
    locale: str
    theme_variant: Literal["cyber", "matrix", "graphite"] = Field(..., alias="themeVariant")
    recommended_height: int = Field(..., alias="recommendedHeight")
    summary: PublicNetworkWidgetSummaryResponse
    focus_region: PublicNetworkRegionResponse | None = Field(None, alias="focusRegion")
    top_regions: list[PublicNetworkLeaderboardEntryResponse] = Field(default_factory=list, alias="topRegions")


class PublicNetworkDpiMeasurementWindowResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    hours: int
    minimum_probe_count: int = Field(..., alias="minimumProbeCount")


class PublicNetworkDpiProtocolResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    protocol: str
    success_rate: float = Field(..., alias="successRate")
    median_handshake_ms: int | None = Field(None, alias="medianHandshakeMs")
    https_baseline_success_rate: float | None = Field(None, alias="httpsBaselineSuccessRate")
    median_https_baseline_ms: int | None = Field(None, alias="medianHttpsBaselineMs")
    last_probe_at: datetime | None = Field(None, alias="lastProbeAt")


class PublicNetworkDpiCountryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    country_code: str = Field(..., alias="countryCode")
    public_name: str = Field(..., alias="publicName")
    score: int
    confidence: Literal["low", "medium", "high"]
    last_updated_at: datetime | None = Field(None, alias="lastUpdatedAt")
    protocols: list[PublicNetworkDpiProtocolResponse] = Field(default_factory=list)


class PublicNetworkDpiScoreResponse(PublicNetworkEnvelope):
    methodology_version: str = Field(..., alias="methodologyVersion")
    measurement_window: PublicNetworkDpiMeasurementWindowResponse = Field(..., alias="measurementWindow")
    enabled: bool
    confidence: Literal["low", "medium", "high"]
    last_updated_at: datetime | None = Field(None, alias="lastUpdatedAt")
    reason_code: str | None = Field(None, alias="reasonCode")
    countries_tracked: int = Field(..., alias="countriesTracked")
    countries: list[PublicNetworkDpiCountryResponse] = Field(default_factory=list)


class PublicNetworkDpiScorePublishRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: str
    snapshot: PublicNetworkDpiScoreResponse


class PublicNetworkDpiScorePublishResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    published: bool
    source: str
    cache_key: str = Field(..., alias="cacheKey")
    expires_at: datetime = Field(..., alias="expiresAt")
