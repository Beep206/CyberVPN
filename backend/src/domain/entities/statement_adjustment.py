"""Typed statement adjustment linked to one statement lineage."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class StatementAdjustment:
    id: UUID
    partner_statement_id: UUID
    partner_account_id: UUID
    source_reference_type: str | None
    source_reference_id: UUID | None
    carried_from_adjustment_id: UUID | None
    adjustment_type: str
    adjustment_direction: str
    amount: float
    currency_code: str
    reason_code: str | None
    adjustment_payload: dict
    created_by_admin_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
