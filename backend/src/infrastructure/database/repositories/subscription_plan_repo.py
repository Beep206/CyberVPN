from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel


class SubscriptionPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self, active_only: bool = True) -> list[SubscriptionPlanModel]:
        query = select(SubscriptionPlanModel).order_by(SubscriptionPlanModel.sort_order)
        if active_only:
            query = query.where(SubscriptionPlanModel.is_active.is_(True))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, id: UUID) -> SubscriptionPlanModel | None:
        return await self._session.get(SubscriptionPlanModel, id)

    async def get_by_name(self, name: str) -> SubscriptionPlanModel | None:
        result = await self._session.execute(
            select(SubscriptionPlanModel).where(SubscriptionPlanModel.name == name)
        )
        return result.scalar_one_or_none()

    async def create(self, model: SubscriptionPlanModel) -> SubscriptionPlanModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(self, model: SubscriptionPlanModel) -> SubscriptionPlanModel:
        await self._session.merge(model)
        await self._session.flush()
        return model

    async def delete(self, id: UUID) -> None:
        model = await self.get_by_id(id)
        if model:
            await self._session.delete(model)
            await self._session.flush()
