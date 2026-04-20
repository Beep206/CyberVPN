from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class CommissionabilityEvaluation:
    id: UUID
    order_id: UUID
    commissionability_status: str
    reason_codes: list[str] = field(default_factory=list)
    partner_context_present: bool = False
    program_allows_commissionability: bool = False
    positive_commission_base: bool = False
    paid_status: bool = False
    fully_refunded: bool = False
    open_payment_dispute_present: bool = False
    risk_allowed: bool = True
    evaluation_snapshot: dict[str, Any] = field(default_factory=dict)
    explainability_snapshot: dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
