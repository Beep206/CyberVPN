from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)


class ListReferralRewardsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._allocations = GrowthRewardAllocationRepository(session)

    async def execute(
        self,
        *,
        beneficiary_user_id: UUID,
        limit: int = 20,
    ):
        return await self._allocations.list_recent_referral_rewards(
            beneficiary_user_id=beneficiary_user_id,
            limit=limit,
        )
