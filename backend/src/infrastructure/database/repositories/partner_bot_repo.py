"""Repository for PartnerBot runtime and provisioning records."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.partner_bot_model import (
    PartnerBotModel,
    PartnerBotProvisioningJobModel,
)


class PartnerBotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_bot(self, model: PartnerBotModel) -> PartnerBotModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update_bot(self, model: PartnerBotModel) -> PartnerBotModel:
        await self._session.merge(model)
        await self._session.flush()
        return model

    async def get_bot_by_id(self, partner_bot_id: UUID) -> PartnerBotModel | None:
        return await self._session.get(PartnerBotModel, partner_bot_id)

    async def get_bot_by_key(self, *, partner_account_id: UUID, bot_key: str) -> PartnerBotModel | None:
        result = await self._session.execute(
            select(PartnerBotModel).where(
                PartnerBotModel.partner_account_id == partner_account_id,
                PartnerBotModel.bot_key == bot_key,
            )
        )
        return result.scalar_one_or_none()

    async def list_bots(
        self,
        *,
        partner_account_id: UUID,
        bot_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PartnerBotModel]:
        query = select(PartnerBotModel).where(PartnerBotModel.partner_account_id == partner_account_id)
        if bot_status is not None:
            query = query.where(PartnerBotModel.status == bot_status)
        query = query.order_by(PartnerBotModel.updated_at.desc(), PartnerBotModel.created_at.desc())
        query = query.limit(limit).offset(offset)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def create_provisioning_job(
        self,
        model: PartnerBotProvisioningJobModel,
    ) -> PartnerBotProvisioningJobModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update_provisioning_job(
        self,
        model: PartnerBotProvisioningJobModel,
    ) -> PartnerBotProvisioningJobModel:
        await self._session.merge(model)
        await self._session.flush()
        return model

    async def claim_next_queued_provisioning_job(self) -> PartnerBotProvisioningJobModel | None:
        result = await self._session.execute(
            select(PartnerBotProvisioningJobModel)
            .where(PartnerBotProvisioningJobModel.job_status == "queued")
            .order_by(
                PartnerBotProvisioningJobModel.queued_at.asc(),
                PartnerBotProvisioningJobModel.created_at.asc(),
                PartnerBotProvisioningJobModel.id.asc(),
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_provisioning_jobs(
        self,
        *,
        partner_bot_ids: list[UUID] | None = None,
        partner_bot_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PartnerBotProvisioningJobModel]:
        query = select(PartnerBotProvisioningJobModel)
        if partner_bot_id is not None:
            query = query.where(PartnerBotProvisioningJobModel.partner_bot_id == partner_bot_id)
        if partner_bot_ids is not None:
            if not partner_bot_ids:
                return []
            query = query.where(PartnerBotProvisioningJobModel.partner_bot_id.in_(partner_bot_ids))
        query = query.order_by(
            PartnerBotProvisioningJobModel.created_at.desc(),
            PartnerBotProvisioningJobModel.id.desc(),
        )
        query = query.limit(limit).offset(offset)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_latest_provisioning_job(
        self,
        *,
        partner_bot_id: UUID,
    ) -> PartnerBotProvisioningJobModel | None:
        items = await self.list_provisioning_jobs(partner_bot_id=partner_bot_id, limit=1, offset=0)
        return items[0] if items else None

    async def get_provisioning_job_by_id(
        self,
        provisioning_job_id: UUID,
    ) -> PartnerBotProvisioningJobModel | None:
        return await self._session.get(PartnerBotProvisioningJobModel, provisioning_job_id)
