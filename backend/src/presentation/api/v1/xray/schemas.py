"""Xray configuration API schemas for Remnawave proxy."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UpdateXrayConfigRequest(BaseModel):
    """Request schema for updating Xray configuration."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "log": {"loglevel": "warning"},
                "inbounds": [],
                "outbounds": [],
                "routing": {"rules": []},
            }
        }
    )

    log: dict[str, Any] | None = Field(None, description="Xray log configuration")
    inbounds: list[dict[str, Any]] | None = Field(None, description="Inbound configurations")
    outbounds: list[dict[str, Any]] | None = Field(None, description="Outbound configurations")
    routing: dict[str, Any] | None = Field(None, description="Routing rules")
    dns: dict[str, Any] | None = Field(None, description="DNS configuration")
    policy: dict[str, Any] | None = Field(None, description="Policy configuration")


class XrayConfigResponse(BaseModel):
    """Expected response from Remnawave xray config API."""

    model_config = ConfigDict(from_attributes=True)

    log: dict[str, Any] | None = Field(None, description="Xray log configuration")
    inbounds: list[dict[str, Any]] | None = Field(None, description="Inbound configurations")
    outbounds: list[dict[str, Any]] | None = Field(None, description="Outbound configurations")
    routing: dict[str, Any] | None = Field(None, description="Routing rules")
    dns: dict[str, Any] | None = Field(None, description="DNS configuration")
    policy: dict[str, Any] | None = Field(None, description="Policy configuration")
