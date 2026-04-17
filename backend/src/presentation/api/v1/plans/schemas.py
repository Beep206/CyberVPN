"""Canonical pricing catalog schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TrafficPolicySchema(BaseModel):
    mode: str = Field(default="fair_use")
    display_label: str = Field(default="Unlimited")
    enforcement_profile: str | None = None


class DedicatedIpSchema(BaseModel):
    included: int = Field(default=0, ge=0)
    eligible: bool = Field(default=False)


class InviteBundleSchema(BaseModel):
    count: int = Field(default=0, ge=0)
    friend_days: int = Field(default=0, ge=0)
    expiry_days: int = Field(default=0, ge=0)


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    name: str
    plan_code: str
    display_name: str
    catalog_visibility: str
    duration_days: int
    traffic_limit_bytes: int | None = None
    devices_included: int
    price_usd: float
    price_rub: float | None = None
    traffic_policy: TrafficPolicySchema
    connection_modes: list[str]
    server_pool: list[str]
    support_sla: str
    dedicated_ip: DedicatedIpSchema
    sale_channels: list[str]
    invite_bundle: InviteBundleSchema
    trial_eligible: bool
    features: dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    sort_order: int


class CreatePlanRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "plus_365",
                "plan_code": "plus",
                "display_name": "Plus",
                "catalog_visibility": "public",
                "duration_days": 365,
                "devices_included": 5,
                "price_usd": 79.0,
                "traffic_policy": {"mode": "fair_use", "display_label": "Unlimited"},
                "connection_modes": ["standard", "stealth"],
                "server_pool": ["shared_plus"],
                "support_sla": "standard",
                "dedicated_ip": {"included": 0, "eligible": True},
                "sale_channels": ["web", "miniapp", "telegram_bot", "admin"],
                "invite_bundle": {"count": 2, "friend_days": 14, "expiry_days": 60},
                "trial_eligible": False,
                "is_active": True,
                "sort_order": 20,
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=100)
    plan_code: str = Field(..., min_length=1, max_length=20)
    display_name: str = Field(..., min_length=1, max_length=100)
    catalog_visibility: str = Field(default="public", min_length=1, max_length=20)
    duration_days: int = Field(..., gt=0, le=3650)
    traffic_limit_bytes: int | None = Field(None, ge=0)
    devices_included: int = Field(..., ge=1)
    price_usd: float = Field(..., ge=0)
    price_rub: float | None = Field(None, ge=0)
    traffic_policy: TrafficPolicySchema = Field(default_factory=TrafficPolicySchema)
    connection_modes: list[str] = Field(default_factory=list)
    server_pool: list[str] = Field(default_factory=list)
    support_sla: str = Field(default="standard", min_length=1, max_length=20)
    dedicated_ip: DedicatedIpSchema = Field(default_factory=DedicatedIpSchema)
    sale_channels: list[str] = Field(default_factory=lambda: ["web", "miniapp", "telegram_bot", "admin"])
    invite_bundle: InviteBundleSchema = Field(default_factory=InviteBundleSchema)
    trial_eligible: bool = False
    features: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0)


class UpdatePlanRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    plan_code: str | None = Field(None, min_length=1, max_length=20)
    display_name: str | None = Field(None, min_length=1, max_length=100)
    catalog_visibility: str | None = Field(None, min_length=1, max_length=20)
    duration_days: int | None = Field(None, gt=0, le=3650)
    traffic_limit_bytes: int | None = Field(None, ge=0)
    devices_included: int | None = Field(None, ge=1)
    price_usd: float | None = Field(None, ge=0)
    price_rub: float | None = Field(None, ge=0)
    traffic_policy: TrafficPolicySchema | None = None
    connection_modes: list[str] | None = None
    server_pool: list[str] | None = None
    support_sla: str | None = Field(None, min_length=1, max_length=20)
    dedicated_ip: DedicatedIpSchema | None = None
    sale_channels: list[str] | None = None
    invite_bundle: InviteBundleSchema | None = None
    trial_eligible: bool | None = None
    features: dict[str, Any] | None = None
    is_active: bool | None = None
    sort_order: int | None = Field(None, ge=0)
