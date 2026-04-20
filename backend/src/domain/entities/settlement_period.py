"""Canonical settlement period for partner finance windows."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class SettlementPeriod:
    id: UUID
    partner_account_id: UUID
    period_key: str
    period_status: str
    currency_code: str
    window_start: datetime
    window_end: datetime
    closed_at: datetime | None
    closed_by_admin_user_id: UUID | None
    reopened_at: datetime | None
    reopened_by_admin_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
