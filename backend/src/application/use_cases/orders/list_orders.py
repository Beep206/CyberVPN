from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.repositories.order_repo import OrderRepository


class ListOrdersUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OrderRepository(session)

    async def execute(self, *, user_id: UUID, limit: int = 50, offset: int = 0) -> list[OrderModel]:
        return await self._repo.list_for_user(user_id=user_id, limit=limit, offset=offset)
