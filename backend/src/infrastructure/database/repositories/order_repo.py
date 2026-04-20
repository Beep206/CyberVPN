from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database.models.order_model import OrderItemModel, OrderModel


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: OrderModel) -> OrderModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_id(self, order_id: UUID) -> OrderModel | None:
        result = await self._session.execute(
            select(OrderModel)
            .execution_options(populate_existing=True)
            .options(selectinload(OrderModel.items))
            .where(OrderModel.id == order_id)
        )
        return result.scalars().first()

    async def get_by_checkout_session_id(self, checkout_session_id: UUID) -> OrderModel | None:
        result = await self._session.execute(
            select(OrderModel)
            .execution_options(populate_existing=True)
            .options(selectinload(OrderModel.items))
            .where(OrderModel.checkout_session_id == checkout_session_id)
        )
        return result.scalars().first()

    async def list_for_user(self, *, user_id: UUID, limit: int = 50, offset: int = 0) -> list[OrderModel]:
        result = await self._session.execute(
            select(OrderModel)
            .execution_options(populate_existing=True)
            .options(selectinload(OrderModel.items))
            .where(OrderModel.user_id == user_id)
            .order_by(OrderModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def create_items(self, items: list[OrderItemModel]) -> list[OrderItemModel]:
        self._session.add_all(items)
        await self._session.flush()
        return items
