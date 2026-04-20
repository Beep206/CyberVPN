from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)


class GetGrowthRewardAllocationUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._allocations = GrowthRewardAllocationRepository(session)

    async def execute(self, *, allocation_id: UUID):
        return await self._allocations.get_by_id(allocation_id)
