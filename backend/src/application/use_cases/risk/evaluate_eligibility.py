from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import RiskReviewDecision
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository

from ._helpers import is_blocking_identifier_type, reason_code_for_identifier


@dataclass(frozen=True)
class EligibilityEvaluationResult:
    check_type: str
    risk_subject_id: UUID
    allowed: bool
    reason_codes: list[str]
    linked_subject_ids: list[UUID]
    checked_at: datetime


class EvaluateEligibilityUseCase:
    _SUPPORTED_CHECK_TYPES = frozenset({"trial_activation", "referral_credit", "partner_payout"})

    def __init__(self, session: AsyncSession) -> None:
        self._risk_repo = RiskSubjectGraphRepository(session)

    async def execute(
        self,
        *,
        check_type: str,
        risk_subject_id: UUID,
        counterparty_subject_id: UUID | None = None,
        context: dict | None = None,
    ) -> EligibilityEvaluationResult:
        _ = context
        normalized_check_type = check_type.strip()
        if normalized_check_type not in self._SUPPORTED_CHECK_TYPES:
            raise ValueError("Unsupported eligibility check_type")

        subject = await self._risk_repo.get_subject_by_id(risk_subject_id)
        if subject is None:
            raise ValueError("Risk subject not found")

        if counterparty_subject_id is not None:
            counterparty = await self._risk_repo.get_subject_by_id(counterparty_subject_id)
            if counterparty is None:
                raise ValueError("Counterparty risk subject not found")

        reason_codes: set[str] = set()
        linked_subject_ids: set[UUID] = set()

        for review in await self._risk_repo.list_open_reviews_for_subject(risk_subject_id):
            if review.decision == RiskReviewDecision.BLOCK.value:
                reason_codes.add("risk_review_block")
            if review.decision == RiskReviewDecision.HOLD.value:
                reason_codes.add("risk_review_hold")

        subject_links = await self._risk_repo.list_links_for_subject(risk_subject_id)
        if normalized_check_type == "trial_activation":
            for link in subject_links:
                if link.status != "active" or not is_blocking_identifier_type(link.identifier_type):
                    continue
                reason_codes.add(reason_code_for_identifier(link.identifier_type))
                linked_subject_ids.add(
                    link.right_subject_id if link.left_subject_id == risk_subject_id else link.left_subject_id
                )

        if normalized_check_type == "referral_credit":
            if counterparty_subject_id is None:
                raise ValueError("referral_credit checks require counterparty_subject_id")
            if counterparty_subject_id == risk_subject_id:
                reason_codes.add("subject_matches_counterparty")
            for link in subject_links:
                if link.status != "active" or not is_blocking_identifier_type(link.identifier_type):
                    continue
                counterpart_id = (
                    link.right_subject_id if link.left_subject_id == risk_subject_id else link.left_subject_id
                )
                if counterpart_id == counterparty_subject_id:
                    reason_codes.add(reason_code_for_identifier(link.identifier_type))
                    linked_subject_ids.add(counterpart_id)

        return EligibilityEvaluationResult(
            check_type=normalized_check_type,
            risk_subject_id=risk_subject_id,
            allowed=not reason_codes,
            reason_codes=sorted(reason_codes),
            linked_subject_ids=sorted(linked_subject_ids, key=str),
            checked_at=datetime.now(UTC),
        )

