from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.governance_action_model import GovernanceActionModel
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository


class ListGovernanceActionsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._risk_repo = RiskSubjectGraphRepository(session)

    async def execute(
        self,
        *,
        risk_subject_id: UUID | None = None,
        risk_review_id: UUID | None = None,
    ) -> list[GovernanceActionModel]:
        if risk_subject_id is not None:
            subject = await self._risk_repo.get_subject_by_id(risk_subject_id)
            if subject is None:
                raise ValueError("Risk subject not found")
        if risk_review_id is not None:
            review = await self._risk_repo.get_review_by_id(risk_review_id)
            if review is None:
                raise ValueError("Risk review not found")

        return await self._risk_repo.list_governance_actions(
            risk_subject_id=risk_subject_id,
            risk_review_id=risk_review_id,
        )
