"""Pydantic schemas for the public status endpoint."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class ServiceStatuses(BaseModel):
    """Health status of backend service dependencies."""

    model_config = ConfigDict(from_attributes=True)

    database: str = Field(
        "ok",
        description="Database connectivity status",
    )
    redis: str = Field(
        "ok",
        description="Redis cache connectivity status",
    )


class StatusResponse(BaseModel):
    """Public API status response.

    Returned by ``GET /api/v1/status`` without authentication.
    Mobile clients use this endpoint to verify backend reachability
    before attempting authenticated requests.
    """

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(
        "ok",
        description="Overall backend status",
    )
    version: str = Field(
        ...,
        description="Backend release version",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Server timestamp in ISO 8601 format",
    )
    services: ServiceStatuses = Field(
        default_factory=ServiceStatuses,
        description="Individual service dependency statuses",
    )
