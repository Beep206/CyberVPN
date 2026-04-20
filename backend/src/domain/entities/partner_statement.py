"""Canonical partner statement snapshot object."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PartnerStatement:
    id: UUID
    partner_account_id: UUID
    settlement_period_id: UUID
    statement_key: str
    statement_version: int
    statement_status: str
    reopened_from_statement_id: UUID | None
    superseded_by_statement_id: UUID | None
    currency_code: str
    accrual_amount: float
    on_hold_amount: float
    reserve_amount: float
    adjustment_net_amount: float
    available_amount: float
    source_event_count: int
    held_event_count: int
    active_reserve_count: int
    adjustment_count: int
    statement_snapshot: dict
    closed_at: datetime | None
    closed_by_admin_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
