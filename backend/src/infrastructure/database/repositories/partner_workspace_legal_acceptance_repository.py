"""Repository for partner workspace legal acceptance records."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.partner_workspace_legal_acceptance_model import (
    PartnerWorkspaceLegalAcceptanceModel,
)


class PartnerWorkspaceLegalAcceptanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_workspace(
        self,
        partner_account_id: UUID,
    ) -> list[PartnerWorkspaceLegalAcceptanceModel]:
        result = await self._session.execute(
            select(PartnerWorkspaceLegalAcceptanceModel)
            .where(PartnerWorkspaceLegalAcceptanceModel.partner_account_id == partner_account_id)
            .order_by(PartnerWorkspaceLegalAcceptanceModel.accepted_at.desc())
        )
        return list(result.scalars().all())

    async def get_for_document(
        self,
        *,
        partner_account_id: UUID,
        document_kind: str,
        document_version: str,
    ) -> PartnerWorkspaceLegalAcceptanceModel | None:
        result = await self._session.execute(
            select(PartnerWorkspaceLegalAcceptanceModel).where(
                PartnerWorkspaceLegalAcceptanceModel.partner_account_id == partner_account_id,
                PartnerWorkspaceLegalAcceptanceModel.document_kind == document_kind,
                PartnerWorkspaceLegalAcceptanceModel.document_version == document_version,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        model: PartnerWorkspaceLegalAcceptanceModel,
    ) -> PartnerWorkspaceLegalAcceptanceModel:
        self._session.add(model)
        await self._session.flush()
        return model
