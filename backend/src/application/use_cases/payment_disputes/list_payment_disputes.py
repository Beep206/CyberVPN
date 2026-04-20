from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.payment_dispute_repo import PaymentDisputeRepository


class ListPaymentDisputesUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._payment_disputes = PaymentDisputeRepository(session)

    async def execute(self, *, order_id: UUID):
        return await self._payment_disputes.list_for_order(order_id)
