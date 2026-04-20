"""Customer commercial binding domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class CustomerCommercialBinding:
    id: UUID
    user_id: UUID
    auth_realm_id: UUID
    storefront_id: UUID | None
    binding_type: str
    binding_status: str
    owner_type: str
    partner_account_id: UUID | None
    partner_code_id: UUID | None
    reason_code: str | None
    evidence_payload: dict[str, Any]
    created_by_admin_user_id: UUID | None
    effective_from: datetime
    effective_to: datetime | None
    created_at: datetime
    updated_at: datetime
