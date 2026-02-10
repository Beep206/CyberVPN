"""Infrastructure repository for referral_commissions table."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.referral_commission_model import (
    ReferralCommissionModel,
)


class ReferralCommissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> ReferralCommissionModel | None:
        return await self._session.get(ReferralCommissionModel, id)

    async def create(self, model: ReferralCommissionModel) -> ReferralCommissionModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_referrer(
        self, referrer_user_id: UUID, offset: int = 0, limit: int = 50
    ) -> list[ReferralCommissionModel]:
        result = await self._session.execute(
            select(ReferralCommissionModel)
            .where(ReferralCommissionModel.referrer_user_id == referrer_user_id)
            .order_by(ReferralCommissionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_referrer(self, referrer_user_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(ReferralCommissionModel)
            .where(ReferralCommissionModel.referrer_user_id == referrer_user_id)
        )
        return result.scalar_one()

    async def get_total_by_referrer(self, referrer_user_id: UUID) -> Decimal:
        result = await self._session.execute(
            select(func.coalesce(func.sum(ReferralCommissionModel.commission_amount), 0)).where(
                ReferralCommissionModel.referrer_user_id == referrer_user_id
            )
        )
        return Decimal(str(result.scalar_one()))

    async def count_by_referrer_for_referred(self, referrer_user_id: UUID, referred_user_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(ReferralCommissionModel)
            .where(
                ReferralCommissionModel.referrer_user_id == referrer_user_id,
                ReferralCommissionModel.referred_user_id == referred_user_id,
            )
        )
        return result.scalar_one()
