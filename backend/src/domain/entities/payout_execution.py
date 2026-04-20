"""Canonical payout execution attempt for a payout instruction."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PayoutExecution:
    id: UUID
    payout_instruction_id: UUID
    partner_account_id: UUID
    partner_statement_id: UUID
    partner_payout_account_id: UUID
    execution_key: str
    execution_mode: str
    execution_status: str
    request_idempotency_key: str
    external_reference: str | None
    execution_payload: dict
    result_payload: dict
    requested_by_admin_user_id: UUID | None
    submitted_by_admin_user_id: UUID | None
    submitted_at: datetime | None
    completed_by_admin_user_id: UUID | None
    completed_at: datetime | None
    reconciled_by_admin_user_id: UUID | None
    reconciled_at: datetime | None
    failure_reason_code: str | None
    created_at: datetime
    updated_at: datetime
