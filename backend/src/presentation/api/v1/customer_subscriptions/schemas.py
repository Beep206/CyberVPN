from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerSubscriptionSummaryResponse(BaseModel):
    subscription_key: str
    kind: Literal["entitlement_grant", "trial", "legacy_payment"]
    status: str
    display_name: str | None = None
    plan_uuid: str | None = None
    plan_code: str | None = None
    source_type: str | None = None
    source_order_id: UUID | None = None
    entitlement_grant_id: UUID | None = None
    service_identity_id: UUID | None = None
    provider_name: str | None = None
    expires_at: str | None = None
    created_at: datetime | None = None
    effective_entitlements: dict[str, Any] = Field(default_factory=dict)
    invite_bundle: dict[str, int] = Field(default_factory=dict)
    is_trial: bool
    addons: list[dict[str, Any]] = Field(default_factory=list)
    can_manage: bool
    can_deliver_config: bool
    management_scope: Literal["subscription_entitlement", "account_vpn_identity"]


class CustomerSubscriptionListResponse(BaseModel):
    customer_account_id: UUID
    auth_realm_id: UUID
    selected_subscription_key: str | None = None
    default_subscription_key: str | None = None
    items: list[CustomerSubscriptionSummaryResponse] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
