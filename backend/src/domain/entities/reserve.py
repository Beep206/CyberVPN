"""Canonical reserve control for partner settlement."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Reserve:
    id: UUID
    partner_account_id: UUID
    source_earning_event_id: UUID | None
    reserve_scope: str
    reserve_reason_type: str
    reserve_status: str
    amount: float
    currency_code: str
    reason_code: str | None
    reserve_payload: dict
    released_at: datetime | None
    released_by_admin_user_id: UUID | None
    created_by_admin_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
