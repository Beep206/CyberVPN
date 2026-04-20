from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.quote_session_model import QuoteSessionModel
from src.infrastructure.database.repositories.commerce_session_repo import CommerceSessionRepository


class GetQuoteSessionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = CommerceSessionRepository(session)

    async def execute(self, *, quote_session_id: UUID) -> QuoteSessionModel | None:
        return await self._repo.get_quote_session_by_id(quote_session_id)
