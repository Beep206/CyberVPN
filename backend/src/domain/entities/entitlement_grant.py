"""Canonical service-access entitlement state."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class EntitlementGrant:
    id: UUID
    grant_key: str
    service_identity_id: UUID
    customer_account_id: UUID
    auth_realm_id: UUID
    origin_storefront_id: UUID | None
    source_type: str
    source_order_id: UUID | None
    source_growth_reward_allocation_id: UUID | None
    source_renewal_order_id: UUID | None
    manual_source_key: str | None
    grant_status: str
    grant_snapshot: dict
    source_snapshot: dict
    effective_from: datetime | None
    expires_at: datetime | None
    created_by_admin_user_id: UUID | None
    activated_at: datetime | None
    activated_by_admin_user_id: UUID | None
    suspended_at: datetime | None
    suspended_by_admin_user_id: UUID | None
    suspension_reason_code: str | None
    revoked_at: datetime | None
    revoked_by_admin_user_id: UUID | None
    revoke_reason_code: str | None
    expired_at: datetime | None
    expired_by_admin_user_id: UUID | None
    expiry_reason_code: str | None
    created_at: datetime
    updated_at: datetime
