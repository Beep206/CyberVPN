from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.partner_integration_credential_model import (
    PartnerIntegrationCredentialModel,
)


class PartnerIntegrationCredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_workspace(
        self,
        *,
        partner_account_id: UUID,
    ) -> list[PartnerIntegrationCredentialModel]:
        result = await self._session.execute(
            select(PartnerIntegrationCredentialModel)
            .where(PartnerIntegrationCredentialModel.partner_account_id == partner_account_id)
            .order_by(
                PartnerIntegrationCredentialModel.credential_kind.asc(),
                PartnerIntegrationCredentialModel.created_at.asc(),
            )
        )
        return list(result.scalars().all())

    async def get_for_workspace_and_kind(
        self,
        *,
        partner_account_id: UUID,
        credential_kind: str,
    ) -> PartnerIntegrationCredentialModel | None:
        result = await self._session.execute(
            select(PartnerIntegrationCredentialModel).where(
                PartnerIntegrationCredentialModel.partner_account_id == partner_account_id,
                PartnerIntegrationCredentialModel.credential_kind == credential_kind,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_hash_and_kind(
        self,
        *,
        credential_hash: str,
        credential_kind: str,
    ) -> PartnerIntegrationCredentialModel | None:
        result = await self._session.execute(
            select(PartnerIntegrationCredentialModel).where(
                PartnerIntegrationCredentialModel.credential_hash == credential_hash,
                PartnerIntegrationCredentialModel.credential_kind == credential_kind,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        model: PartnerIntegrationCredentialModel,
    ) -> PartnerIntegrationCredentialModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(
        self,
        model: PartnerIntegrationCredentialModel,
    ) -> PartnerIntegrationCredentialModel:
        await self._session.merge(model)
        await self._session.flush()
        return model
