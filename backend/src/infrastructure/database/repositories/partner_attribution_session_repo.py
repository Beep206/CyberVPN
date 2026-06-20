from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.partner_attribution_session_model import (
    PartnerAttributionSessionModel,
)


class PartnerAttributionSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: PartnerAttributionSessionModel) -> PartnerAttributionSessionModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_by_id(self, session_id: UUID) -> PartnerAttributionSessionModel | None:
        return await self._session.get(PartnerAttributionSessionModel, session_id)

    async def get_by_session_token_hash(
        self, session_token_hash: str, *, for_update: bool = False
    ) -> PartnerAttributionSessionModel | None:
        stmt = (
            select(PartnerAttributionSessionModel)
            .where(PartnerAttributionSessionModel.session_token_hash == session_token_hash)
            .limit(1)
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_by_transfer_token_hash(
        self,
        transfer_token_hash: str,
        *,
        for_update: bool = False,
    ) -> PartnerAttributionSessionModel | None:
        stmt = (
            select(PartnerAttributionSessionModel)
            .where(PartnerAttributionSessionModel.transfer_token_hash == transfer_token_hash)
            .limit(1)
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalars().first()
