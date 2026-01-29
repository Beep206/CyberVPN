"""Host API schemas for Remnawave proxy."""

import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateHostRequest(BaseModel):
    """Request schema for creating a VPN host."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Germany Server 1",
                "address": "de1.example.com",
                "port": 443,
                "sni": "cloudflare.com",
                "is_disabled": False,
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=100, description="Host display name")
    address: str = Field(
        ..., min_length=1, max_length=255, description="Host address or IP"
    )
    port: int = Field(..., ge=1, le=65535, description="Host port")
    sni: Optional[str] = Field(
        None, max_length=255, description="Server Name Indication"
    )
    host_header: Optional[str] = Field(
        None, max_length=255, description="HTTP Host header"
    )
    is_disabled: bool = Field(False, description="Whether host is disabled")
    path: Optional[str] = Field(None, max_length=255, description="WebSocket path")
    alpn: Optional[list[str]] = Field(None, description="ALPN protocols")

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError("Address must be a valid hostname or IP address")
        return v


class UpdateHostRequest(BaseModel):
    """Request schema for updating a VPN host."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    address: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    sni: Optional[str] = Field(None, max_length=255)
    host_header: Optional[str] = Field(None, max_length=255)
    is_disabled: Optional[bool] = None
    path: Optional[str] = Field(None, max_length=255)
    alpn: Optional[list[str]] = None

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError("Address must be a valid hostname or IP address")
        return v


class HostResponse(BaseModel):
    """Expected response from Remnawave hosts API."""

    model_config = ConfigDict(from_attributes=True)

    uuid: str = Field(..., description="Host UUID")
    name: str = Field(..., max_length=100, description="Host display name")
    address: str = Field(..., max_length=255, description="Host address")
    port: int = Field(..., description="Host port")
    sni: Optional[str] = Field(None, max_length=255, description="SNI")
    host_header: Optional[str] = Field(None, max_length=255, description="Host header")
    is_disabled: bool = Field(..., description="Whether host is disabled")
    path: Optional[str] = Field(None, max_length=255, description="WebSocket path")
    alpn: Optional[list[str]] = Field(None, description="ALPN protocols")
