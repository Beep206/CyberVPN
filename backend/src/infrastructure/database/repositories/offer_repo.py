from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.offer_model import OfferModel


class OfferRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: OfferModel) -> OfferModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def list_active(
        self,
        *,
        at: datetime | None = None,
        sale_channel: str | None = None,
        subscription_plan_id: UUID | None = None,
        include_inactive: bool = False,
    ) -> list[OfferModel]:
        now = at or datetime.now(UTC)
        query: Select[tuple[OfferModel]] = select(OfferModel).order_by(
            OfferModel.offer_key,
            OfferModel.effective_from.desc(),
        )
        if not include_inactive:
            query = query.where(
                OfferModel.is_active.is_(True),
                OfferModel.version_status == "active",
                OfferModel.effective_from <= now,
                (OfferModel.effective_to.is_(None)) | (OfferModel.effective_to > now),
            )
        if sale_channel is not None:
            query = query.where(OfferModel.sale_channels.contains([sale_channel]))
        if subscription_plan_id is not None:
            query = query.where(OfferModel.subscription_plan_id == subscription_plan_id)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_current_by_key(
        self,
        offer_key: str,
        *,
        at: datetime | None = None,
    ) -> OfferModel | None:
        now = at or datetime.now(UTC)
        result = await self._session.execute(
            select(OfferModel)
            .where(
                OfferModel.offer_key == offer_key,
                OfferModel.is_active.is_(True),
                OfferModel.version_status == "active",
                OfferModel.effective_from <= now,
                (OfferModel.effective_to.is_(None)) | (OfferModel.effective_to > now),
            )
            .order_by(OfferModel.effective_from.desc())
        )
        return result.scalars().first()

    async def get_by_ids(self, offer_ids: list[UUID]) -> list[OfferModel]:
        if not offer_ids:
            return []
        result = await self._session.execute(select(OfferModel).where(OfferModel.id.in_(offer_ids)))
        return list(result.scalars().all())
