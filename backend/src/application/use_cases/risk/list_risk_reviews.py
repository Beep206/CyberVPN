from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository


class ListRiskReviewsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._risk_repo = RiskSubjectGraphRepository(session)

    async def execute(self, *, risk_subject_id: UUID) -> list[RiskReviewModel]:
        subject = await self._risk_repo.get_subject_by_id(risk_subject_id)
        if subject is None:
            raise ValueError("Risk subject not found")
        return await self._risk_repo.list_reviews_for_subject(risk_subject_id)

