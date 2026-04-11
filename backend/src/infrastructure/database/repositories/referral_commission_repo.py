"""Infrastructure repository for referral_commissions table."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import desc, distinct, func, select
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

    async def get_recent(self, offset: int = 0, limit: int = 50) -> list[ReferralCommissionModel]:
        result = await self._session.execute(
            select(ReferralCommissionModel)
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

    async def count_distinct_referred_users(self, referrer_user_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count(distinct(ReferralCommissionModel.referred_user_id))).where(
                ReferralCommissionModel.referrer_user_id == referrer_user_id
            )
        )
        return int(result.scalar_one() or 0)

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

    async def get_admin_overview_metrics(self) -> dict[str, int | Decimal]:
        total_commissions_result = await self._session.execute(
            select(func.count()).select_from(ReferralCommissionModel)
        )
        total_earned_result = await self._session.execute(
            select(func.coalesce(func.sum(ReferralCommissionModel.commission_amount), 0))
        )
        unique_referrers_result = await self._session.execute(
            select(func.count(distinct(ReferralCommissionModel.referrer_user_id)))
        )
        unique_referred_users_result = await self._session.execute(
            select(func.count(distinct(ReferralCommissionModel.referred_user_id)))
        )

        return {
            "total_commissions": int(total_commissions_result.scalar_one() or 0),
            "total_earned": Decimal(str(total_earned_result.scalar_one() or 0)),
            "unique_referrers": int(unique_referrers_result.scalar_one() or 0),
            "unique_referred_users": int(unique_referred_users_result.scalar_one() or 0),
        }

    async def get_referrer_stats_map(self, referrer_user_ids: list[UUID]) -> dict[UUID, dict[str, Any]]:
        if not referrer_user_ids:
            return {}

        result = await self._session.execute(
            select(
                ReferralCommissionModel.referrer_user_id.label("referrer_user_id"),
                func.count(ReferralCommissionModel.id).label("commission_count"),
                func.count(distinct(ReferralCommissionModel.referred_user_id)).label("referred_users"),
                func.coalesce(func.sum(ReferralCommissionModel.commission_amount), 0).label("total_earned"),
                func.max(ReferralCommissionModel.created_at).label("last_commission_at"),
            )
            .where(ReferralCommissionModel.referrer_user_id.in_(referrer_user_ids))
            .group_by(ReferralCommissionModel.referrer_user_id)
        )

        stats: dict[UUID, dict[str, Any]] = {}
        for row in result:
            stats[row.referrer_user_id] = {
                "commission_count": int(row.commission_count or 0),
                "referred_users": int(row.referred_users or 0),
                "total_earned": Decimal(str(row.total_earned or 0)),
                "last_commission_at": row.last_commission_at,
            }
        return stats

    async def get_top_referrer_stats(self, limit: int = 10) -> list[dict[str, Any]]:
        result = await self._session.execute(
            select(
                ReferralCommissionModel.referrer_user_id.label("referrer_user_id"),
                func.count(ReferralCommissionModel.id).label("commission_count"),
                func.count(distinct(ReferralCommissionModel.referred_user_id)).label("referred_users"),
                func.coalesce(func.sum(ReferralCommissionModel.commission_amount), 0).label("total_earned"),
                func.max(ReferralCommissionModel.created_at).label("last_commission_at"),
            )
            .group_by(ReferralCommissionModel.referrer_user_id)
            .order_by(desc("total_earned"), desc("commission_count"))
            .limit(limit)
        )

        return [
            {
                "referrer_user_id": row.referrer_user_id,
                "commission_count": int(row.commission_count or 0),
                "referred_users": int(row.referred_users or 0),
                "total_earned": Decimal(str(row.total_earned or 0)),
                "last_commission_at": row.last_commission_at,
            }
            for row in result
        ]
