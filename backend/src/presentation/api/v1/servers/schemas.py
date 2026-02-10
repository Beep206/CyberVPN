"""Server API schemas."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.enums import ServerStatus


class ServerResponse(BaseModel):
    """Response schema for a Remnawave VPN server."""

    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    name: str
    address: str
    port: int
    status: ServerStatus
    is_connected: bool
    is_disabled: bool
    created_at: datetime
    updated_at: datetime
    traffic_used_bytes: int
    inbound_count: int
    users_online: int


class CreateServerRequest(BaseModel):
    """Request schema for creating a new server."""

    name: str = Field(..., min_length=1, max_length=100)
    address: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError("Address must be a valid hostname or IP address")
        return v


class UpdateServerRequest(BaseModel):
    """Request schema for updating a server."""

    name: str | None = Field(None, min_length=1, max_length=100)
    address: str | None = Field(None, min_length=1, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError("Address must be a valid hostname or IP address")
        return v


class ServerStatsResponse(BaseModel):
    """Response schema for server statistics by status."""

    model_config = ConfigDict(from_attributes=True)

    online: int
    offline: int
    warning: int
    maintenance: int
    total: int
