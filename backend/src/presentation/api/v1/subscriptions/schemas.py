"""Subscription template API schemas for Remnawave proxy."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateSubscriptionTemplateRequest(BaseModel):
    """Request schema for creating a subscription template."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Standard VPN Config",
                "template_type": "v2ray",
                "host_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "inbound_tag": "vless-in",
                "flow": "xtls-rprx-vision",
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    template_type: str = Field(..., min_length=1, max_length=50, description="VPN client template type")
    host_uuid: str | None = Field(None, max_length=255, description="Host UUID")
    inbound_tag: str | None = Field(None, max_length=100, description="Inbound tag")
    flow: str | None = Field(None, max_length=50, description="Flow control method")
    config_data: dict[str, Any] | None = Field(None, description="Additional config data")


class UpdateSubscriptionTemplateRequest(BaseModel):
    """Request schema for updating a subscription template."""

    name: str | None = Field(None, min_length=1, max_length=100)
    template_type: str | None = Field(None, min_length=1, max_length=50)
    host_uuid: str | None = Field(None, max_length=255)
    inbound_tag: str | None = Field(None, max_length=100)
    flow: str | None = Field(None, max_length=50)
    config_data: dict[str, Any] | None = None


class SubscriptionResponse(BaseModel):
    """Expected response from Remnawave subscriptions API."""

    model_config = ConfigDict(from_attributes=True)

    uuid: str = Field(..., description="Subscription UUID")
    name: str = Field(..., max_length=100, description="Template name")
    template_type: str = Field(..., max_length=50, description="Template type")
    host_uuid: str | None = Field(None, description="Host UUID")
    inbound_tag: str | None = Field(None, max_length=100, description="Inbound tag")
    flow: str | None = Field(None, max_length=50, description="Flow control method")
    config_data: dict[str, Any] | None = Field(None, description="Config data")


class SubscriptionConfigResponse(BaseModel):
    """Expected response for subscription config generation."""

    model_config = ConfigDict(from_attributes=True)

    config: str = Field(..., description="Generated VPN configuration string")
    subscription_url: str | None = Field(None, max_length=5000, description="Subscription URL")
