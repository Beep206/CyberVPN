from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel


class SubscriptionPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(
        self,
        active_only: bool = True,
        *,
        include_untyped: bool = False,
    ) -> list[SubscriptionPlanModel]:
        query = select(SubscriptionPlanModel).order_by(SubscriptionPlanModel.sort_order)
        if active_only:
            query = query.where(SubscriptionPlanModel.is_active.is_(True))
        if not include_untyped:
            query = query.where(SubscriptionPlanModel.plan_code.is_not(None))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_catalog(
        self,
        *,
        visibility: str | None = None,
        sale_channel: str | None = None,
        active_only: bool = True,
    ) -> list[SubscriptionPlanModel]:
        query = (
            select(SubscriptionPlanModel)
            .where(SubscriptionPlanModel.plan_code.is_not(None))
            .order_by(SubscriptionPlanModel.sort_order, SubscriptionPlanModel.duration_days)
        )
        if active_only:
            query = query.where(SubscriptionPlanModel.is_active.is_(True))
        if visibility is not None:
            query = query.where(SubscriptionPlanModel.catalog_visibility == visibility)
        if sale_channel is not None:
            query = query.where(SubscriptionPlanModel.sale_channels.contains([sale_channel]))

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, id: UUID) -> SubscriptionPlanModel | None:
        return await self._session.get(SubscriptionPlanModel, id)

    async def get_by_name(self, name: str) -> SubscriptionPlanModel | None:
        result = await self._session.execute(select(SubscriptionPlanModel).where(SubscriptionPlanModel.name == name))
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

    async def get_by_plan_code(
        self,
        plan_code: str,
        *,
        duration_days: int | None = None,
        visibility: str | None = None,
        sale_channel: str | None = None,
    ) -> SubscriptionPlanModel | None:
        query = select(SubscriptionPlanModel).where(SubscriptionPlanModel.plan_code == plan_code)
        if duration_days is not None:
            query = query.where(SubscriptionPlanModel.duration_days == duration_days)
        if visibility is not None:
            query = query.where(SubscriptionPlanModel.catalog_visibility == visibility)
        if sale_channel is not None:
            query = query.where(SubscriptionPlanModel.sale_channels.contains([sale_channel]))

        query = query.order_by(SubscriptionPlanModel.sort_order, SubscriptionPlanModel.duration_days)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_plan_codes(
        self,
        plan_codes: Sequence[str],
        *,
        active_only: bool = True,
    ) -> list[SubscriptionPlanModel]:
        if not plan_codes:
            return []

        query = select(SubscriptionPlanModel).where(SubscriptionPlanModel.plan_code.in_(list(plan_codes)))
        if active_only:
            query = query.where(SubscriptionPlanModel.is_active.is_(True))
        query = query.order_by(SubscriptionPlanModel.sort_order, SubscriptionPlanModel.duration_days)
        result = await self._session.execute(query)
        return list(result.scalars().all())
