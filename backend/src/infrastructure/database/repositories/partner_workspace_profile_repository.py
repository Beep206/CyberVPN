"""Repository for partner workspace organization profile and settings."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.partner_workspace_profile_model import (
    PartnerWorkspaceProfileModel,
)


class PartnerWorkspaceProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_account_id(self, partner_account_id: UUID) -> PartnerWorkspaceProfileModel | None:
        result = await self._session.execute(
            select(PartnerWorkspaceProfileModel).where(
                PartnerWorkspaceProfileModel.partner_account_id == partner_account_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, partner_account_id: UUID) -> PartnerWorkspaceProfileModel:
        existing = await self.get_by_account_id(partner_account_id)
        if existing is not None:
            return existing

        model = PartnerWorkspaceProfileModel(partner_account_id=partner_account_id)
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(self, model: PartnerWorkspaceProfileModel) -> PartnerWorkspaceProfileModel:
        await self._session.merge(model)
        await self._session.flush()
        return model

