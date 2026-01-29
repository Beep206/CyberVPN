"""Xray configuration API schemas for Remnawave proxy."""

from typing import Any, Optional

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

    log: Optional[dict[str, Any]] = Field(
        None, description="Xray log configuration"
    )
    inbounds: Optional[list[dict[str, Any]]] = Field(
        None, description="Inbound configurations"
    )
    outbounds: Optional[list[dict[str, Any]]] = Field(
        None, description="Outbound configurations"
    )
    routing: Optional[dict[str, Any]] = Field(None, description="Routing rules")
    dns: Optional[dict[str, Any]] = Field(None, description="DNS configuration")
    policy: Optional[dict[str, Any]] = Field(None, description="Policy configuration")


class XrayConfigResponse(BaseModel):
    """Expected response from Remnawave xray config API."""

    model_config = ConfigDict(from_attributes=True)

    log: Optional[dict[str, Any]] = Field(None, description="Xray log configuration")
    inbounds: Optional[list[dict[str, Any]]] = Field(None, description="Inbound configurations")
    outbounds: Optional[list[dict[str, Any]]] = Field(None, description="Outbound configurations")
    routing: Optional[dict[str, Any]] = Field(None, description="Routing rules")
    dns: Optional[dict[str, Any]] = Field(None, description="DNS configuration")
    policy: Optional[dict[str, Any]] = Field(None, description="Policy configuration")
