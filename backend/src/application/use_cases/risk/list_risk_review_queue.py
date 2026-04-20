from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository


@dataclass(frozen=True)
class RiskReviewQueueItem:
    review: RiskReviewModel
    subject: RiskSubjectModel
    attachment_count: int
    governance_action_count: int


class ListRiskReviewQueueUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._risk_repo = RiskSubjectGraphRepository(session)

    async def execute(
        self,
        *,
        status: str | None = None,
        review_type: str | None = None,
    ) -> list[RiskReviewQueueItem]:
        queue: list[RiskReviewQueueItem] = []
        for review in await self._risk_repo.list_reviews(status=status, review_type=review_type):
            subject = await self._risk_repo.get_subject_by_id(review.risk_subject_id)
            if subject is None:
                continue
            attachments = await self._risk_repo.list_review_attachments_for_review(review.id)
            governance_actions = await self._risk_repo.list_governance_actions(risk_review_id=review.id)
            queue.append(
                RiskReviewQueueItem(
                    review=review,
                    subject=subject,
                    attachment_count=len(attachments),
                    governance_action_count=len(governance_actions),
                )
            )
        return queue
