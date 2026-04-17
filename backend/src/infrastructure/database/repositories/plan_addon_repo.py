from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.plan_addon_model import PlanAddonModel, SubscriptionAddonModel


class PlanAddonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_catalog(
        self,
        *,
        active_only: bool = True,
        sale_channel: str | None = None,
    ) -> list[PlanAddonModel]:
        query = select(PlanAddonModel).order_by(PlanAddonModel.display_name)
        if active_only:
            query = query.where(PlanAddonModel.is_active.is_(True))
        if sale_channel is not None:
            query = query.where(PlanAddonModel.sale_channels.contains([sale_channel]))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, addon_id: UUID) -> PlanAddonModel | None:
        return await self._session.get(PlanAddonModel, addon_id)

    async def get_by_code(self, code: str) -> PlanAddonModel | None:
        result = await self._session.execute(select(PlanAddonModel).where(PlanAddonModel.code == code))
        return result.scalar_one_or_none()

    async def get_by_codes(self, codes: list[str]) -> list[PlanAddonModel]:
        if not codes:
            return []
        result = await self._session.execute(select(PlanAddonModel).where(PlanAddonModel.code.in_(codes)))
        return list(result.scalars().all())

    async def get_by_ids(self, addon_ids: list[UUID]) -> list[PlanAddonModel]:
        if not addon_ids:
            return []
        result = await self._session.execute(select(PlanAddonModel).where(PlanAddonModel.id.in_(addon_ids)))
        return list(result.scalars().all())

    async def create(self, model: PlanAddonModel) -> PlanAddonModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(self, model: PlanAddonModel) -> PlanAddonModel:
        await self._session.merge(model)
        await self._session.flush()
        return model


class SubscriptionAddonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_for_user(
        self,
        user_id: UUID,
        *,
        at: datetime | None = None,
    ) -> list[SubscriptionAddonModel]:
        now = at or datetime.now(UTC)
        result = await self._session.execute(
            select(SubscriptionAddonModel).where(
                SubscriptionAddonModel.user_id == user_id,
                SubscriptionAddonModel.status == "active",
                SubscriptionAddonModel.starts_at <= now,
                (SubscriptionAddonModel.expires_at.is_(None)) | (SubscriptionAddonModel.expires_at > now),
            )
        )
        return list(result.scalars().all())

    async def create_batch(self, models: list[SubscriptionAddonModel]) -> list[SubscriptionAddonModel]:
        self._session.add_all(models)
        await self._session.flush()
        return models
