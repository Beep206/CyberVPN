"""Canonical non-cash growth reward allocation entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class GrowthRewardAllocation:
    id: UUID
    reward_type: str
    allocation_status: str
    beneficiary_user_id: UUID
    auth_realm_id: UUID
    storefront_id: UUID | None
    order_id: UUID | None
    invite_code_id: UUID | None
    referral_commission_id: UUID | None
    source_key: str | None
    quantity: float
    unit: str
    currency_code: str | None
    reward_payload: dict[str, Any]
    created_by_admin_user_id: UUID | None
    allocated_at: datetime
    reversed_at: datetime | None
    created_at: datetime
    updated_at: datetime
