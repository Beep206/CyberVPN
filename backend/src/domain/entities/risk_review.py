from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.enums import RiskReviewDecision, RiskReviewStatus


@dataclass(frozen=True)
class RiskReview:
    uuid: UUID
    risk_subject_id: UUID
    review_type: str
    status: RiskReviewStatus | str
    decision: RiskReviewDecision | str
    reason: str
    evidence: dict[str, Any]
    created_by_admin_user_id: UUID | None
    resolved_by_admin_user_id: UUID | None
    resolved_at: datetime | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.review_type.strip():
            raise ValueError("Risk review review_type must not be empty")
