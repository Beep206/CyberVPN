"""Infrastructure repository for partner_codes and partner_earnings tables."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.partner_model import (
    PartnerCodeModel,
    PartnerEarningModel,
)


class PartnerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_code_by_id(self, id: UUID) -> PartnerCodeModel | None:
        return await self._session.get(PartnerCodeModel, id)

    async def get_code_by_code(self, code: str) -> PartnerCodeModel | None:
        result = await self._session.execute(select(PartnerCodeModel).where(PartnerCodeModel.code == code))
        return result.scalar_one_or_none()

    async def get_active_code_by_code(self, code: str) -> PartnerCodeModel | None:
        result = await self._session.execute(
            select(PartnerCodeModel).where(
                PartnerCodeModel.code == code,
                PartnerCodeModel.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_codes_by_partner(self, partner_user_id: UUID) -> list[PartnerCodeModel]:
        result = await self._session.execute(
            select(PartnerCodeModel).where(PartnerCodeModel.partner_user_id == partner_user_id)
        )
        return list(result.scalars().all())

    async def get_codes_by_partners(self, partner_user_ids: list[UUID]) -> list[PartnerCodeModel]:
        if not partner_user_ids:
            return []

        result = await self._session.execute(
            select(PartnerCodeModel).where(PartnerCodeModel.partner_user_id.in_(partner_user_ids))
        )
        return list(result.scalars().all())

    async def create_code(self, model: PartnerCodeModel) -> PartnerCodeModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update_code(self, model: PartnerCodeModel) -> PartnerCodeModel:
        await self._session.merge(model)
        await self._session.flush()
        return model

    async def record_earning(self, model: PartnerEarningModel) -> PartnerEarningModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_earnings_by_partner(
        self, partner_user_id: UUID, offset: int = 0, limit: int = 50
    ) -> list[PartnerEarningModel]:
        result = await self._session.execute(
            select(PartnerEarningModel)
            .where(PartnerEarningModel.partner_user_id == partner_user_id)
            .order_by(PartnerEarningModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_clients(self, partner_user_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count(func.distinct(PartnerEarningModel.client_user_id))).where(
                PartnerEarningModel.partner_user_id == partner_user_id
            )
        )
        return result.scalar_one() or 0

    async def get_total_earnings(self, partner_user_id: UUID) -> Decimal:
        result = await self._session.execute(
            select(func.sum(PartnerEarningModel.total_earning)).where(
                PartnerEarningModel.partner_user_id == partner_user_id
            )
        )
        return result.scalar_one() or Decimal(0)

    async def get_partner_stats_map(self, partner_user_ids: list[UUID]) -> dict[UUID, dict[str, Any]]:
        if not partner_user_ids:
            return {}

        code_stats_result = await self._session.execute(
            select(
                PartnerCodeModel.partner_user_id.label("partner_user_id"),
                func.count(PartnerCodeModel.id).label("code_count"),
                func.sum(case((PartnerCodeModel.is_active == True, 1), else_=0)).label("active_code_count"),  # noqa: E712
                func.max(PartnerCodeModel.updated_at).label("last_code_at"),
            )
            .where(PartnerCodeModel.partner_user_id.in_(partner_user_ids))
            .group_by(PartnerCodeModel.partner_user_id)
        )

        earning_stats_result = await self._session.execute(
            select(
                PartnerEarningModel.partner_user_id.label("partner_user_id"),
                func.count(distinct(PartnerEarningModel.client_user_id)).label("total_clients"),
                func.coalesce(func.sum(PartnerEarningModel.total_earning), 0).label("total_earned"),
                func.max(PartnerEarningModel.created_at).label("last_earning_at"),
            )
            .where(PartnerEarningModel.partner_user_id.in_(partner_user_ids))
            .group_by(PartnerEarningModel.partner_user_id)
        )

        stats: dict[UUID, dict[str, Any]] = {
            user_id: {
                "code_count": 0,
                "active_code_count": 0,
                "total_clients": 0,
                "total_earned": Decimal(0),
                "last_activity_at": None,
            }
            for user_id in partner_user_ids
        }

        for row in code_stats_result:
            entry = stats.setdefault(
                row.partner_user_id,
                {
                    "code_count": 0,
                    "active_code_count": 0,
                    "total_clients": 0,
                    "total_earned": Decimal(0),
                    "last_activity_at": None,
                },
            )
            entry["code_count"] = int(row.code_count or 0)
            entry["active_code_count"] = int(row.active_code_count or 0)
            entry["last_activity_at"] = row.last_code_at

        for row in earning_stats_result:
            entry = stats.setdefault(
                row.partner_user_id,
                {
                    "code_count": 0,
                    "active_code_count": 0,
                    "total_clients": 0,
                    "total_earned": Decimal(0),
                    "last_activity_at": None,
                },
            )
            entry["total_clients"] = int(row.total_clients or 0)
            entry["total_earned"] = Decimal(str(row.total_earned or 0))
            if row.last_earning_at and (
                entry["last_activity_at"] is None or row.last_earning_at > entry["last_activity_at"]
            ):
                entry["last_activity_at"] = row.last_earning_at

        return stats
