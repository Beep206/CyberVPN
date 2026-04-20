from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.growth_reward_allocation_model import GrowthRewardAllocationModel


class GrowthRewardAllocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: GrowthRewardAllocationModel) -> GrowthRewardAllocationModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_by_id(self, allocation_id: UUID) -> GrowthRewardAllocationModel | None:
        return await self._session.get(GrowthRewardAllocationModel, allocation_id)

    async def get_by_source_key(self, source_key: str) -> GrowthRewardAllocationModel | None:
        result = await self._session.execute(
            select(GrowthRewardAllocationModel).where(GrowthRewardAllocationModel.source_key == source_key)
        )
        return result.scalars().first()

    async def list(
        self,
        *,
        beneficiary_user_id: UUID | None = None,
        order_id: UUID | None = None,
        reward_type: str | None = None,
        allocation_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GrowthRewardAllocationModel]:
        stmt = select(GrowthRewardAllocationModel).order_by(
            GrowthRewardAllocationModel.allocated_at.desc(),
            GrowthRewardAllocationModel.created_at.desc(),
        )
        if beneficiary_user_id is not None:
            stmt = stmt.where(GrowthRewardAllocationModel.beneficiary_user_id == beneficiary_user_id)
        if order_id is not None:
            stmt = stmt.where(GrowthRewardAllocationModel.order_id == order_id)
        if reward_type is not None:
            stmt = stmt.where(GrowthRewardAllocationModel.reward_type == reward_type)
        if allocation_status is not None:
            stmt = stmt.where(GrowthRewardAllocationModel.allocation_status == allocation_status)
        result = await self._session.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def list_for_order(self, order_id: UUID) -> list[GrowthRewardAllocationModel]:
        result = await self._session.execute(
            select(GrowthRewardAllocationModel)
            .where(GrowthRewardAllocationModel.order_id == order_id)
            .order_by(
                GrowthRewardAllocationModel.allocated_at.desc(),
                GrowthRewardAllocationModel.created_at.desc(),
            )
        )
        return list(result.scalars().all())
