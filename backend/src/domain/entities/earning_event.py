"""Canonical partner settlement accrual event."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class EarningEvent:
    id: UUID
    partner_account_id: UUID | None
    partner_user_id: UUID
    client_user_id: UUID
    order_id: UUID
    payment_id: UUID | None
    partner_code_id: UUID | None
    legacy_partner_earning_id: UUID | None
    order_attribution_result_id: UUID | None
    owner_type: str
    event_status: str
    commission_base_amount: float
    markup_amount: float
    commission_pct: float
    commission_amount: float
    total_amount: float
    currency_code: str
    available_at: datetime | None
    source_snapshot: dict
    created_at: datetime
    updated_at: datetime
