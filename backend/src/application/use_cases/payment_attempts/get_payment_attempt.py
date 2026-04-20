from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.repositories.payment_attempt_repo import PaymentAttemptRepository


class GetPaymentAttemptUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PaymentAttemptRepository(session)

    async def execute(self, *, payment_attempt_id: UUID) -> PaymentAttemptModel | None:
        return await self._repo.get_by_id(payment_attempt_id)
