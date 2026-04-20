from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database.models.pricebook_model import PricebookEntryModel, PricebookModel
from src.infrastructure.database.models.storefront_model import StorefrontModel


class PricebookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: PricebookModel) -> PricebookModel:
        self._session.add(model)
        await self._session.flush()
        result = await self._session.execute(
            select(PricebookModel)
            .options(selectinload(PricebookModel.entries).selectinload(PricebookEntryModel.offer))
            .where(PricebookModel.id == model.id)
        )
        return result.scalars().one()

    async def list_active(
        self,
        *,
        storefront_id: UUID | None = None,
        storefront_key: str | None = None,
        at: datetime | None = None,
        currency_code: str | None = None,
        region_code: str | None = None,
        include_inactive: bool = False,
    ) -> list[PricebookModel]:
        now = at or datetime.now(UTC)
        query: Select[tuple[PricebookModel]] = (
            select(PricebookModel)
            .options(selectinload(PricebookModel.entries).selectinload(PricebookEntryModel.offer))
            .order_by(PricebookModel.pricebook_key, PricebookModel.effective_from.desc())
        )
        if storefront_key is not None:
            query = query.join(StorefrontModel, StorefrontModel.id == PricebookModel.storefront_id).where(
                StorefrontModel.storefront_key == storefront_key
            )
        if not include_inactive:
            query = query.where(
                PricebookModel.is_active.is_(True),
                PricebookModel.version_status == "active",
                PricebookModel.effective_from <= now,
                (PricebookModel.effective_to.is_(None)) | (PricebookModel.effective_to > now),
            )
        if storefront_id is not None:
            query = query.where(PricebookModel.storefront_id == storefront_id)
        if currency_code is not None:
            query = query.where(PricebookModel.currency_code == currency_code.upper())
        if region_code is not None:
            query = query.where(PricebookModel.region_code == region_code.upper())
        result = await self._session.execute(query)
        return list(result.scalars().unique().all())

    async def get_current_by_key(self, pricebook_key: str, *, at: datetime | None = None) -> PricebookModel | None:
        now = at or datetime.now(UTC)
        result = await self._session.execute(
            select(PricebookModel)
            .options(selectinload(PricebookModel.entries).selectinload(PricebookEntryModel.offer))
            .where(
                PricebookModel.pricebook_key == pricebook_key,
                PricebookModel.is_active.is_(True),
                PricebookModel.version_status == "active",
                PricebookModel.effective_from <= now,
                (PricebookModel.effective_to.is_(None)) | (PricebookModel.effective_to > now),
            )
            .order_by(PricebookModel.effective_from.desc())
        )
        return result.scalars().first()
