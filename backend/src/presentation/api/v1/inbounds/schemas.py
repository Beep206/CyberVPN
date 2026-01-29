"""Inbound configuration API schemas for Remnawave proxy."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class InboundResponse(BaseModel):
    """Expected response from Remnawave inbounds API."""

    model_config = ConfigDict(from_attributes=True)

    uuid: str = Field(..., description="Inbound UUID")
    tag: str = Field(..., max_length=100, description="Inbound tag")
    protocol: str = Field(..., max_length=50, description="Protocol (vless, vmess, trojan, etc.)")
    port: int = Field(..., description="Listening port")
    network: Optional[str] = Field(None, max_length=50, description="Transport network type")
    security: Optional[str] = Field(None, max_length=50, description="Security type (tls, reality, etc.)")
    settings: Optional[dict[str, Any]] = Field(None, description="Inbound settings")
