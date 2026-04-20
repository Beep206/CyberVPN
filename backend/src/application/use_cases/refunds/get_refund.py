from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.refund_repo import RefundRepository


class GetRefundUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._refunds = RefundRepository(session)

    async def execute(self, *, refund_id: UUID):
        return await self._refunds.get_by_id(refund_id)
