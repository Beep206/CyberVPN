from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import case, func, select
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

    async def get_by_source_redemption_id(
        self,
        source_redemption_id: UUID,
    ) -> GrowthRewardAllocationModel | None:
        result = await self._session.execute(
            select(GrowthRewardAllocationModel).where(
                GrowthRewardAllocationModel.source_redemption_id == source_redemption_id
            )
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

    async def list_for_source_code(self, source_code_id: UUID) -> list[GrowthRewardAllocationModel]:
        result = await self._session.execute(
            select(GrowthRewardAllocationModel)
            .where(GrowthRewardAllocationModel.source_code_id == source_code_id)
            .order_by(
                GrowthRewardAllocationModel.allocated_at.desc(),
                GrowthRewardAllocationModel.created_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def list_recent_referral_rewards(
        self,
        *,
        beneficiary_user_id: UUID,
        limit: int = 10,
    ) -> list[GrowthRewardAllocationModel]:
        result = await self._session.execute(
            select(GrowthRewardAllocationModel)
            .where(
                GrowthRewardAllocationModel.beneficiary_user_id == beneficiary_user_id,
                GrowthRewardAllocationModel.reward_type == "referral_credit",
            )
            .order_by(
                GrowthRewardAllocationModel.allocated_at.desc(),
                GrowthRewardAllocationModel.created_at.desc(),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_releasable_referral_rewards(
        self,
        *,
        as_of: datetime | None = None,
        limit: int = 100,
    ) -> list[GrowthRewardAllocationModel]:
        resolved_as_of = as_of or datetime.now(UTC)
        result = await self._session.execute(
            select(GrowthRewardAllocationModel)
            .where(
                GrowthRewardAllocationModel.reward_type == "referral_credit",
                GrowthRewardAllocationModel.allocation_status == "pending",
                GrowthRewardAllocationModel.hold_until.is_not(None),
                GrowthRewardAllocationModel.hold_until <= resolved_as_of,
            )
            .order_by(
                GrowthRewardAllocationModel.hold_until.asc(),
                GrowthRewardAllocationModel.allocated_at.asc(),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_reversible_referral_rewards_for_order(
        self,
        *,
        order_id: UUID,
    ) -> list[GrowthRewardAllocationModel]:
        result = await self._session.execute(
            select(GrowthRewardAllocationModel)
            .where(
                GrowthRewardAllocationModel.order_id == order_id,
                GrowthRewardAllocationModel.reward_type == "referral_credit",
                GrowthRewardAllocationModel.allocation_status.in_(("pending", "available", "blocked_by_risk")),
            )
            .order_by(
                GrowthRewardAllocationModel.allocated_at.desc(),
                GrowthRewardAllocationModel.created_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def sum_quantity_for_beneficiary(
        self,
        *,
        beneficiary_user_id: UUID,
        reward_type: str | None = None,
        statuses: tuple[str, ...] | None = None,
        allocated_from: datetime | None = None,
    ) -> float:
        stmt = select(func.coalesce(func.sum(GrowthRewardAllocationModel.quantity), 0)).where(
            GrowthRewardAllocationModel.beneficiary_user_id == beneficiary_user_id
        )
        if reward_type is not None:
            stmt = stmt.where(GrowthRewardAllocationModel.reward_type == reward_type)
        if statuses is not None:
            stmt = stmt.where(GrowthRewardAllocationModel.allocation_status.in_(statuses))
        if allocated_from is not None:
            stmt = stmt.where(GrowthRewardAllocationModel.allocated_at >= allocated_from)
        result = await self._session.execute(stmt)
        return float(result.scalar_one() or 0)

    async def summarize_referral_credit_by_status(
        self,
        *,
        beneficiary_user_id: UUID,
    ) -> dict[str, float]:
        result = await self._session.execute(
            select(
                GrowthRewardAllocationModel.allocation_status,
                func.coalesce(func.sum(GrowthRewardAllocationModel.quantity), 0),
            )
            .where(
                GrowthRewardAllocationModel.beneficiary_user_id == beneficiary_user_id,
                GrowthRewardAllocationModel.reward_type == "referral_credit",
            )
            .group_by(GrowthRewardAllocationModel.allocation_status)
        )
        return {
            str(allocation_status): float(total or 0)
            for allocation_status, total in result.all()
        }

    async def get_referral_reward_stats_map(
        self,
        beneficiary_user_ids: list[UUID],
    ) -> dict[UUID, dict[str, float | int | datetime | None]]:
        if not beneficiary_user_ids:
            return {}

        active_reward_quantity = case(
            (GrowthRewardAllocationModel.allocation_status != "reversed", GrowthRewardAllocationModel.quantity),
            else_=0,
        )
        result = await self._session.execute(
            select(
                GrowthRewardAllocationModel.beneficiary_user_id.label("beneficiary_user_id"),
                func.count(GrowthRewardAllocationModel.id).label("reward_count"),
                func.coalesce(func.sum(active_reward_quantity), 0).label("total_earned"),
                func.max(GrowthRewardAllocationModel.allocated_at).label("last_reward_at"),
            )
            .where(
                GrowthRewardAllocationModel.beneficiary_user_id.in_(beneficiary_user_ids),
                GrowthRewardAllocationModel.reward_type == "referral_credit",
            )
            .group_by(GrowthRewardAllocationModel.beneficiary_user_id)
        )

        stats: dict[UUID, dict[str, float | int | datetime | None]] = {}
        for row in result:
            stats[row.beneficiary_user_id] = {
                "reward_count": int(row.reward_count or 0),
                "total_earned": float(row.total_earned or 0),
                "last_reward_at": row.last_reward_at,
            }
        return stats

    async def get_top_referrer_reward_stats(
        self,
        *,
        limit: int = 10,
    ) -> list[dict[str, float | int | UUID | datetime | None]]:
        active_reward_quantity = case(
            (GrowthRewardAllocationModel.allocation_status != "reversed", GrowthRewardAllocationModel.quantity),
            else_=0,
        )
        result = await self._session.execute(
            select(
                GrowthRewardAllocationModel.beneficiary_user_id.label("beneficiary_user_id"),
                func.count(GrowthRewardAllocationModel.id).label("reward_count"),
                func.coalesce(func.sum(active_reward_quantity), 0).label("total_earned"),
                func.max(GrowthRewardAllocationModel.allocated_at).label("last_reward_at"),
            )
            .where(GrowthRewardAllocationModel.reward_type == "referral_credit")
            .group_by(GrowthRewardAllocationModel.beneficiary_user_id)
            .order_by(
                func.coalesce(func.sum(active_reward_quantity), 0).desc(),
                func.count(GrowthRewardAllocationModel.id).desc(),
            )
            .limit(limit)
        )
        return [
            {
                "beneficiary_user_id": row.beneficiary_user_id,
                "reward_count": int(row.reward_count or 0),
                "total_earned": float(row.total_earned or 0),
                "last_reward_at": row.last_reward_at,
            }
            for row in result
        ]

    async def get_referral_reward_overview_metrics(self) -> dict[str, float | int]:
        active_reward_quantity = case(
            (GrowthRewardAllocationModel.allocation_status != "reversed", GrowthRewardAllocationModel.quantity),
            else_=0,
        )
        count_result = await self._session.execute(
            select(func.count())
            .select_from(GrowthRewardAllocationModel)
            .where(GrowthRewardAllocationModel.reward_type == "referral_credit")
        )
        total_result = await self._session.execute(
            select(func.coalesce(func.sum(active_reward_quantity), 0)).where(
                GrowthRewardAllocationModel.reward_type == "referral_credit"
            )
        )
        unique_referrers_result = await self._session.execute(
            select(func.count(func.distinct(GrowthRewardAllocationModel.beneficiary_user_id))).where(
                GrowthRewardAllocationModel.reward_type == "referral_credit"
            )
        )
        return {
            "total_rewards": int(count_result.scalar_one() or 0),
            "total_earned": float(total_result.scalar_one() or 0),
            "unique_referrers": int(unique_referrers_result.scalar_one() or 0),
        }

    async def summarize_by_status(self) -> list[dict[str, object]]:
        result = await self._session.execute(
            select(
                GrowthRewardAllocationModel.allocation_status,
                func.count(GrowthRewardAllocationModel.id),
            )
            .group_by(GrowthRewardAllocationModel.allocation_status)
            .order_by(GrowthRewardAllocationModel.allocation_status.asc())
        )
        return [
            {"allocation_status": allocation_status, "count": int(count)}
            for allocation_status, count in result.all()
        ]

    async def summarize_by_type(self) -> list[dict[str, object]]:
        result = await self._session.execute(
            select(
                GrowthRewardAllocationModel.reward_type,
                func.count(GrowthRewardAllocationModel.id),
            )
            .group_by(GrowthRewardAllocationModel.reward_type)
            .order_by(GrowthRewardAllocationModel.reward_type.asc())
        )
        return [
            {"reward_type": reward_type, "count": int(count)}
            for reward_type, count in result.all()
        ]

    async def get_available_referral_credit_total(self) -> float:
        result = await self._session.execute(
            select(func.coalesce(func.sum(GrowthRewardAllocationModel.quantity), 0))
            .where(
                GrowthRewardAllocationModel.reward_type == "referral_credit",
                GrowthRewardAllocationModel.allocation_status == "available",
                GrowthRewardAllocationModel.currency_code == "USD",
            )
        )
        return float(result.scalar_one() or 0)

    async def list_blocked_by_risk(
        self,
        *,
        limit: int = 50,
    ) -> list[GrowthRewardAllocationModel]:
        result = await self._session.execute(
            select(GrowthRewardAllocationModel)
            .where(GrowthRewardAllocationModel.allocation_status == "blocked_by_risk")
            .order_by(
                GrowthRewardAllocationModel.allocated_at.desc(),
                GrowthRewardAllocationModel.created_at.desc(),
            )
            .limit(limit)
        )
        return list(result.scalars().all())
