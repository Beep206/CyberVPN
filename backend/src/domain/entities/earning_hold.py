"""Canonical payout-hold object for partner settlement accruals."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class EarningHold:
    id: UUID
    earning_event_id: UUID
    partner_account_id: UUID | None
    hold_reason_type: str
    hold_status: str
    reason_code: str | None
    hold_until: datetime | None
    released_at: datetime | None
    released_by_admin_user_id: UUID | None
    created_by_admin_user_id: UUID | None
    hold_payload: dict
    created_at: datetime
    updated_at: datetime
