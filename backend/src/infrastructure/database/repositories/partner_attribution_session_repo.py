from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
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
            .where(
                or_(
                    PartnerAttributionSessionModel.transfer_token_hash == transfer_token_hash,
                    PartnerAttributionSessionModel.consumed_transfer_token_hash == transfer_token_hash,
                )
            )
            .limit(1)
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_by_capture_idempotency_key(
        self,
        capture_idempotency_key_hash: str,
        *,
        for_update: bool = False,
    ) -> PartnerAttributionSessionModel | None:
        stmt = (
            select(PartnerAttributionSessionModel)
            .where(PartnerAttributionSessionModel.capture_idempotency_key_hash == capture_idempotency_key_hash)
            .limit(1)
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_active_for_browser(
        self,
        *,
        partner_code_id: UUID,
        auth_realm_id: UUID,
        storefront_id: UUID | None,
        browser_key_hash: str,
        now: datetime,
        for_update: bool = False,
    ) -> PartnerAttributionSessionModel | None:
        stmt = (
            select(PartnerAttributionSessionModel)
            .where(
                PartnerAttributionSessionModel.partner_code_id == partner_code_id,
                PartnerAttributionSessionModel.auth_realm_id == auth_realm_id,
                PartnerAttributionSessionModel.browser_key_hash == browser_key_hash,
                PartnerAttributionSessionModel.status == "pending",
                PartnerAttributionSessionModel.transfer_consumed_at.is_(None),
                PartnerAttributionSessionModel.expires_at > now,
            )
            .order_by(
                PartnerAttributionSessionModel.last_seen_at.desc(),
                PartnerAttributionSessionModel.created_at.desc(),
            )
            .limit(1)
        )
        if storefront_id is None:
            stmt = stmt.where(PartnerAttributionSessionModel.storefront_id.is_(None))
        else:
            stmt = stmt.where(PartnerAttributionSessionModel.storefront_id == storefront_id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalars().first()
