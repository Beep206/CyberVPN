"""Pydantic schemas for monitoring and health check endpoints."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ComponentStatus(BaseModel):
    """Status information for a single system component."""

    status: Literal["healthy", "unhealthy"] = Field(
        ..., description="Component health status"
    )
    message: str = Field(
        ..., max_length=500, description="Status message"
    )
    response_time_ms: float | None = Field(
        None, description="Response time in milliseconds"
    )


class HealthResponse(BaseModel):
    """Overall system health check response."""

    model_config = ConfigDict(from_attributes=True)

    status: Literal["healthy", "unhealthy", "degraded"] = Field(
        ..., description="Overall system status"
    )
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
    period: Literal["today", "week", "month"] = Field(
        ..., description="Time period for analytics"
    )


class TopUserResponse(BaseModel):
    """Top user by traffic response."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str = Field(..., max_length=255, description="User ID")
    username: str = Field(..., max_length=100, description="Username")
    traffic_bytes: int = Field(..., description="Total traffic in bytes")
