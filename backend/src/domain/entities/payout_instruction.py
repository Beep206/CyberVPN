"""Canonical payout instruction generated from a closed partner statement."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PayoutInstruction:
    id: UUID
    partner_account_id: UUID
    partner_statement_id: UUID
    partner_payout_account_id: UUID
    instruction_key: str
    instruction_status: str
    payout_amount: float
    currency_code: str
    instruction_snapshot: dict
    created_by_admin_user_id: UUID | None
    approved_by_admin_user_id: UUID | None
    approved_at: datetime | None
    rejected_by_admin_user_id: UUID | None
    rejected_at: datetime | None
    rejection_reason_code: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
