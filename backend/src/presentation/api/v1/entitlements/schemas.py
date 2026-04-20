from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import EntitlementGrantSourceType, EntitlementGrantStatus


class CreateEntitlementGrantRequest(BaseModel):
    service_identity_id: UUID
    source_order_id: UUID | None = None
    source_growth_reward_allocation_id: UUID | None = None
    source_renewal_order_id: UUID | None = None
    manual_source_key: str | None = Field(None, min_length=1, max_length=160)
    grant_snapshot: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class EntitlementGrantTransitionRequest(BaseModel):
    reason_code: str | None = Field(None, min_length=1, max_length=80)


class CurrentEntitlementStateResponse(BaseModel):
    status: str
    plan_uuid: str | None = None
    plan_code: str | None = None
    display_name: str | None = None
    period_days: int | None = None
    expires_at: str | None = None
    effective_entitlements: dict[str, Any]
    invite_bundle: dict[str, int]
    is_trial: bool
    addons: list[dict[str, Any]] = Field(default_factory=list)


class EntitlementGrantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    grant_key: str
    service_identity_id: UUID
    customer_account_id: UUID
    auth_realm_id: UUID
    origin_storefront_id: UUID | None = None
    source_type: EntitlementGrantSourceType
    source_order_id: UUID | None = None
    source_growth_reward_allocation_id: UUID | None = None
    source_renewal_order_id: UUID | None = None
    manual_source_key: str | None = None
    grant_status: EntitlementGrantStatus
    grant_snapshot: dict[str, Any] = Field(default_factory=dict)
    source_snapshot: dict[str, Any] = Field(default_factory=dict)
    effective_from: datetime | None = None
    expires_at: datetime | None = None
    created_by_admin_user_id: UUID | None = None
    activated_at: datetime | None = None
    activated_by_admin_user_id: UUID | None = None
    suspended_at: datetime | None = None
    suspended_by_admin_user_id: UUID | None = None
    suspension_reason_code: str | None = None
    revoked_at: datetime | None = None
    revoked_by_admin_user_id: UUID | None = None
    revoke_reason_code: str | None = None
    expired_at: datetime | None = None
    expired_by_admin_user_id: UUID | None = None
    expiry_reason_code: str | None = None
    created_at: datetime
    updated_at: datetime
