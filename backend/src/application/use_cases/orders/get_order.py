from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.repositories.order_repo import OrderRepository


class GetOrderUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OrderRepository(session)

    async def execute(self, *, order_id: UUID) -> OrderModel | None:
        return await self._repo.get_by_id(order_id)
