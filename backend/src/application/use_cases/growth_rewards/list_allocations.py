from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)


class ListGrowthRewardAllocationsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._allocations = GrowthRewardAllocationRepository(session)

    async def execute(
        self,
        *,
        beneficiary_user_id: UUID | None = None,
        order_id: UUID | None = None,
        reward_type: str | None = None,
        allocation_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        return await self._allocations.list(
            beneficiary_user_id=beneficiary_user_id,
            order_id=order_id,
            reward_type=reward_type,
            allocation_status=allocation_status,
            limit=limit,
            offset=offset,
        )
