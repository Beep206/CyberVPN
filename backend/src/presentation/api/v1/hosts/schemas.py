"""Host API schemas for Remnawave proxy."""

import re
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


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
    address: str = Field(..., min_length=1, max_length=255, description="Host address or IP")
    port: int = Field(..., ge=1, le=65535, description="Host port")
    sni: str | None = Field(default=None, max_length=255, description="Server Name Indication")
    host_header: str | None = Field(default=None, max_length=255, description="HTTP Host header")
    is_disabled: bool = Field(False, description="Whether host is disabled")
    path: str | None = Field(default=None, max_length=255, description="WebSocket path")
    alpn: list[str] | None = Field(default=None, description="ALPN protocols")

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError("Address must be a valid hostname or IP address")
        return v


class UpdateHostRequest(BaseModel):
    """Request schema for updating a VPN host."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    sni: str | None = Field(default=None, max_length=255)
    host_header: str | None = Field(default=None, max_length=255)
    is_disabled: bool | None = None
    path: str | None = Field(default=None, max_length=255)
    alpn: list[str] | None = None

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError("Address must be a valid hostname or IP address")
        return v


class HostResponse(BaseModel):
    """Expected response from Remnawave hosts API."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_by_name=True,
        validate_by_alias=True,
    )

    uuid: str = Field(..., description="Host UUID")
    name: str = Field(
        ...,
        max_length=100,
        validation_alias=AliasChoices("name", "remark"),
        description="Host display name",
    )
    address: str = Field(..., max_length=255, description="Host address")
    port: int = Field(..., description="Host port")
    sni: str | None = Field(default=None, max_length=255, description="SNI")
    host_header: str | None = Field(
        default=None,
        max_length=255,
        validation_alias=AliasChoices("host_header", "hostHeader", "host"),
        description="Host header",
    )
    is_disabled: bool = Field(
        ...,
        validation_alias=AliasChoices("is_disabled", "isDisabled"),
        description="Whether host is disabled",
    )
    path: str | None = Field(default=None, max_length=255, description="WebSocket path")
    alpn: list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("alpn"),
        description="ALPN protocols",
    )

    @field_validator("alpn", mode="before")
    @classmethod
    def normalize_alpn(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value
