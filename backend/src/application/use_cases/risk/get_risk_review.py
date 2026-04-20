from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.governance_action_model import GovernanceActionModel
from src.infrastructure.database.models.risk_review_attachment_model import RiskReviewAttachmentModel
from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository


@dataclass(frozen=True)
class RiskReviewDetail:
    review: RiskReviewModel
    subject: RiskSubjectModel
    attachments: list[RiskReviewAttachmentModel]
    governance_actions: list[GovernanceActionModel]


class GetRiskReviewUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._risk_repo = RiskSubjectGraphRepository(session)

    async def execute(self, *, risk_review_id: UUID) -> RiskReviewDetail:
        review = await self._risk_repo.get_review_by_id(risk_review_id)
        if review is None:
            raise ValueError("Risk review not found")
        subject = await self._risk_repo.get_subject_by_id(review.risk_subject_id)
        if subject is None:
            raise ValueError("Risk subject not found")
        attachments = await self._risk_repo.list_review_attachments_for_review(review.id)
        governance_actions = await self._risk_repo.list_governance_actions(risk_review_id=review.id)
        return RiskReviewDetail(
            review=review,
            subject=subject,
            attachments=attachments,
            governance_actions=governance_actions,
        )
