from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.payment_dispute_repo import PaymentDisputeRepository


class GetPaymentDisputeUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._payment_disputes = PaymentDisputeRepository(session)

    async def execute(self, *, payment_dispute_id: UUID):
        return await self._payment_disputes.get_by_id(payment_dispute_id)
