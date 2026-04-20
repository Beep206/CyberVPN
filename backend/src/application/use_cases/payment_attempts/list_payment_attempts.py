from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.repositories.payment_attempt_repo import PaymentAttemptRepository


class ListPaymentAttemptsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PaymentAttemptRepository(session)

    async def execute(self, *, order_id: UUID) -> list[PaymentAttemptModel]:
        return await self._repo.list_for_order(order_id)
