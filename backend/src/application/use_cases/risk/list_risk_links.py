from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.risk_link_model import RiskLinkModel
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository


class ListRiskLinksUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._risk_repo = RiskSubjectGraphRepository(session)

    async def execute(self, *, risk_subject_id: UUID) -> list[RiskLinkModel]:
        subject = await self._risk_repo.get_subject_by_id(risk_subject_id)
        if subject is None:
            raise ValueError("Risk subject not found")
        return await self._risk_repo.list_links_for_subject(risk_subject_id)

