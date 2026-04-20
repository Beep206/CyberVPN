from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.order_attribution_result_repo import (
    OrderAttributionResultRepository,
)


class GetOrderAttributionResultUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._results = OrderAttributionResultRepository(session)

    async def execute(self, *, order_id: UUID):
        return await self._results.get_by_order_id(order_id)
