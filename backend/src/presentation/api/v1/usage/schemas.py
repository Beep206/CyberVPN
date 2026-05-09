"""Pydantic schemas for the usage statistics endpoint."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UsageSource = Literal["remnawave", "unavailable"]
UsageUnavailableReason = Literal[
    "upstream_user_not_found",
    "upstream_unavailable",
]


class UsageResponse(BaseModel):
    """Response schema for user VPN usage statistics."""

    model_config = ConfigDict(from_attributes=True)

    usage_available: bool = Field(
        description="True when aggregate usage was fetched from the authoritative VPN backend"
    )
    usage_source: UsageSource = Field(description="Authoritative source for this usage snapshot")
    usage_unavailable_reason: UsageUnavailableReason | None = Field(
        None,
        description="Reason usage is unavailable when usage_available is false",
    )
    bandwidth_used_bytes: int = Field(description="Total bandwidth consumed in bytes")
    bandwidth_limit_bytes: int = Field(description="Bandwidth limit in bytes (0 = unlimited)")
    connections_active: int = Field(description="Number of currently active connections")
    connections_limit: int = Field(description="Maximum allowed concurrent connections")
    period_start: datetime = Field(description="Start of the current billing period")
    period_end: datetime = Field(description="End of the current billing period")
    last_connection_at: datetime | None = Field(None, description="Timestamp of last VPN connection")
    generated_at: datetime = Field(description="Timestamp when this usage snapshot was generated")
