from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.refund_repo import RefundRepository


class ListRefundsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._refunds = RefundRepository(session)

    async def execute(self, *, order_id: UUID):
        return await self._refunds.list_for_order(order_id)
