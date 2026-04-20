"""Canonical service principal detached from storefront session assumptions."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ServiceIdentity:
    id: UUID
    service_key: str
    customer_account_id: UUID
    auth_realm_id: UUID
    source_order_id: UUID | None
    origin_storefront_id: UUID | None
    provider_name: str
    provider_subject_ref: str | None
    identity_status: str
    service_context: dict
    created_at: datetime
    updated_at: datetime
