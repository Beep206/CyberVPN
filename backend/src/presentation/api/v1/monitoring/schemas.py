"""Pydantic schemas for monitoring and health check endpoints."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ComponentStatus(BaseModel):
    """Status information for a single system component."""

    status: Literal["healthy", "unhealthy"] = Field(..., description="Component health status")
    message: str = Field(..., max_length=500, description="Status message")
    response_time_ms: float | None = Field(None, description="Response time in milliseconds")


class HealthResponse(BaseModel):
    """Overall system health check response."""

    model_config = ConfigDict(from_attributes=True)

    status: Literal["healthy", "unhealthy", "degraded"] = Field(..., description="Overall system status")
    components: dict[str, ComponentStatus] = Field(
        default_factory=dict,
        description="Status of individual components",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of health check",
    )


class StatsResponse(BaseModel):
    """System statistics response."""

    model_config = ConfigDict(from_attributes=True)

    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    total_servers: int = Field(..., description="Total number of VPN servers")
    online_servers: int = Field(..., description="Number of online servers")
    total_traffic_bytes: int = Field(..., description="Total traffic in bytes")


class BandwidthResponse(BaseModel):
    """Bandwidth usage response."""

    model_config = ConfigDict(from_attributes=True)

    bytes_in: int = Field(..., description="Incoming bytes")
    bytes_out: int = Field(..., description="Outgoing bytes")
    period: Literal["today", "week", "month"] = Field(..., description="Time period for analytics")


class MetadataBuildResponse(BaseModel):
    """Remnawave build metadata."""

    time: str = Field(..., description="Build timestamp")
    number: str = Field(..., description="Build number")


class MetadataGitBackendResponse(BaseModel):
    """Backend git metadata."""

    commit_sha: str = Field(..., description="Backend commit SHA")
    branch: str = Field(..., description="Backend branch")
    commit_url: str = Field(..., description="Backend commit URL")


class MetadataGitFrontendResponse(BaseModel):
    """Frontend git metadata."""

    commit_sha: str = Field(..., description="Frontend commit SHA")
    commit_url: str = Field(..., description="Frontend commit URL")


class MetadataGitResponse(BaseModel):
    """Git metadata for backend and frontend."""

    backend: MetadataGitBackendResponse
    frontend: MetadataGitFrontendResponse


class MetadataResponse(BaseModel):
    """Remnawave panel metadata response."""

    model_config = ConfigDict(from_attributes=True)

    version: str = Field(..., description="Remnawave panel version")
    build: MetadataBuildResponse
    git: MetadataGitResponse
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RecapPeriodResponse(BaseModel):
    """Traffic/users summary for a recap period."""

    users: int = Field(..., description="Users in the period")
    traffic_bytes: int = Field(..., description="Traffic in bytes for the period")


class RecapTotalsResponse(BaseModel):
    """Lifetime Remnawave recap totals."""

    users: int = Field(..., description="Total users")
    nodes: int = Field(..., description="Total nodes")
    traffic_bytes: int = Field(..., description="Lifetime traffic in bytes")
    nodes_ram: str | None = Field(None, description="Aggregate node RAM")
    nodes_cpu_cores: int | None = Field(None, description="Aggregate node CPU cores")
    distinct_countries: int | None = Field(None, description="Distinct node countries")


class RecapResponse(BaseModel):
    """Remnawave recap response."""

    model_config = ConfigDict(from_attributes=True)

    version: str | None = Field(None, description="Remnawave panel version")
    init_date: datetime | None = Field(None, description="Panel initialization date")
    total: RecapTotalsResponse
    this_month: RecapPeriodResponse | None = Field(None, description="Current month recap")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TopUserResponse(BaseModel):
    """Top user by traffic response."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str = Field(..., max_length=255, description="User ID")
    username: str = Field(..., max_length=100, description="Username")
    traffic_bytes: int = Field(..., description="Total traffic in bytes")
