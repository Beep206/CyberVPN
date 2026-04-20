from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.renewal_order_model import RenewalOrderModel


class RenewalOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: RenewalOrderModel) -> RenewalOrderModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_by_id(self, renewal_order_id: UUID) -> RenewalOrderModel | None:
        return await self._session.get(RenewalOrderModel, renewal_order_id)

    async def get_by_order_id(self, order_id: UUID) -> RenewalOrderModel | None:
        result = await self._session.execute(
            select(RenewalOrderModel).where(RenewalOrderModel.order_id == order_id)
        )
        return result.scalars().first()

    async def list_for_initial_order(self, initial_order_id: UUID) -> list[RenewalOrderModel]:
        result = await self._session.execute(
            select(RenewalOrderModel)
            .where(RenewalOrderModel.initial_order_id == initial_order_id)
            .order_by(
                RenewalOrderModel.renewal_sequence_number.asc(),
                RenewalOrderModel.created_at.asc(),
            )
        )
        return list(result.scalars().all())
