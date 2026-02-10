"""Pydantic schemas for the usage statistics endpoint."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UsageResponse(BaseModel):
    """Response schema for user VPN usage statistics."""

    model_config = ConfigDict(from_attributes=True)

    bandwidth_used_bytes: int = Field(description="Total bandwidth consumed in bytes")
    bandwidth_limit_bytes: int = Field(description="Bandwidth limit in bytes (0 = unlimited)")
    connections_active: int = Field(description="Number of currently active connections")
    connections_limit: int = Field(description="Maximum allowed concurrent connections")
    period_start: datetime = Field(description="Start of the current billing period")
    period_end: datetime = Field(description="End of the current billing period")
    last_connection_at: datetime | None = Field(None, description="Timestamp of last VPN connection")
