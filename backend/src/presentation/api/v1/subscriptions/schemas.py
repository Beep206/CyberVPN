"""Subscription template API schemas for Remnawave proxy."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.infrastructure.remnawave.control_plane_contracts import (
    RemnawaveSubscriptionTemplateV34Response,
    SubscriptionTemplateType,
)


class _SubscriptionTemplateRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_alias=True,
        validate_by_name=True,
        extra="forbid",
    )

    def to_upstream_payload(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json", exclude_unset=True)


class CreateSubscriptionTemplateRequest(_SubscriptionTemplateRequest):
    """Exact target ``CreateSubscriptionTemplateBodyDto`` shape."""

    name: str = Field(min_length=2, max_length=255, pattern=r"^[A-Za-z0-9_\s-]+$")
    template_type: SubscriptionTemplateType = Field(alias="templateType")


class UpdateSubscriptionTemplateRequest(_SubscriptionTemplateRequest):
    """Exact target ``UpdateTemplateBodyDto`` fields except path-owned UUID."""

    name: str | None = Field(default=None, min_length=2, max_length=255, pattern=r"^[A-Za-z0-9_\s-]+$")
    template_json: dict[str, Any] | None = Field(default=None, alias="templateJson")
    encoded_template_yaml: str | None = Field(default=None, alias="encodedTemplateYaml")

    @model_validator(mode="after")
    def reject_explicit_null(self) -> UpdateSubscriptionTemplateRequest:
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class SubscriptionTemplateResponse(RemnawaveSubscriptionTemplateV34Response):
    """CyberVPN response mirrors the unwrapped target template DTO."""


class SubscriptionTemplateListResponse(BaseModel):
    """Current Remnawave template list envelope."""

    total: int = Field(..., ge=0, description="Total number of templates")
    templates: list[SubscriptionTemplateResponse] = Field(
        default_factory=list,
        description="Subscription templates returned by Remnawave",
    )


class SubscriptionConfigResponse(BaseModel):
    """Expected response for subscription config generation."""

    model_config = ConfigDict(from_attributes=True)

    config: str = Field(..., description="Generated VPN configuration string")
    is_found: bool = Field(True, alias="isFound", description="Whether the upstream subscription exists")
    links: list[str] = Field(default_factory=list, description="All generated connection links")
    ss_conf_links: dict[str, str] = Field(default_factory=dict, alias="ssConfLinks", description="SS config links")
    subscription_url: str | None = Field(default=None, max_length=5000, description="Subscription URL")
    xhttp_enabled: bool = Field(False, alias="xhttpEnabled", description="Whether XHTTP links are present")
    xhttp_links: list[str] = Field(default_factory=list, alias="xhttpLinks", description="XHTTP connection links")


class ActiveSubscriptionResponse(BaseModel):
    """Response schema for active subscription."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., description="Subscription status (active, expired, trial, cancelled, none)")
    plan_name: str | None = Field(default=None, description="Name of the subscription plan")
    expires_at: datetime | None = Field(default=None, description="Subscription expiration timestamp")
    traffic_limit_bytes: int | None = Field(default=None, description="Traffic limit in bytes")
    used_traffic_bytes: int | None = Field(default=None, description="Used traffic in bytes")
    auto_renew: bool = Field(False, description="Whether subscription auto-renews")


class CurrentEntitlementsResponse(BaseModel):
    """Canonical effective entitlement snapshot."""

    status: str
    plan_uuid: str | None = None
    plan_code: str | None = None
    display_name: str | None = None
    period_days: int | None = None
    expires_at: str | None = None
    effective_entitlements: dict[str, Any]
    invite_bundle: dict[str, Any]
    is_trial: bool
    addons: list[dict[str, Any]] = Field(default_factory=list)


class UpgradeSubscriptionRequest(BaseModel):
    target_plan_id: UUID = Field(..., description="Target subscription plan UUID")
    promo_code: str | None = Field(default=None, max_length=50)
    use_wallet: float = Field(0, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=12)
    channel: str = Field(default="web", min_length=1, max_length=30)


class SubscriptionAddonItemRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    qty: int = Field(default=1, ge=1, le=100)
    location_code: str | None = Field(default=None, min_length=2, max_length=64)


class PurchaseSubscriptionAddonsRequest(BaseModel):
    addons: list[SubscriptionAddonItemRequest] = Field(..., min_length=1)
    promo_code: str | None = Field(default=None, max_length=50)
    use_wallet: float = Field(0, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=12)
    channel: str = Field(default="web", min_length=1, max_length=30)


class CancelSubscriptionResponse(BaseModel):
    """Response schema for subscription cancellation."""

    message: str = "Subscription canceled successfully"
    canceled_at: datetime = Field(..., description="Cancellation timestamp")
