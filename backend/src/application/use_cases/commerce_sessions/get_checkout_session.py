from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.checkout_session_model import CheckoutSessionModel
from src.infrastructure.database.repositories.commerce_session_repo import CommerceSessionRepository


class GetCheckoutSessionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = CommerceSessionRepository(session)

    async def execute(self, *, checkout_session_id: UUID) -> CheckoutSessionModel | None:
        return await self._repo.get_checkout_session_by_id(checkout_session_id)
