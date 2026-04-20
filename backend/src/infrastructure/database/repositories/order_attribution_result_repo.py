from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.order_attribution_result_model import OrderAttributionResultModel


class OrderAttributionResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: OrderAttributionResultModel) -> OrderAttributionResultModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_by_id(self, result_id: UUID) -> OrderAttributionResultModel | None:
        return await self._session.get(OrderAttributionResultModel, result_id)

    async def get_by_order_id(self, order_id: UUID) -> OrderAttributionResultModel | None:
        result = await self._session.execute(
            select(OrderAttributionResultModel).where(OrderAttributionResultModel.order_id == order_id)
        )
        return result.scalars().first()
