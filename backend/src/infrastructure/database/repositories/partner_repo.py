"""Infrastructure repository for partner_codes and partner_earnings tables."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import case, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.partner_model import (
    PartnerAccountModel,
    PartnerCodeLinkModel,
    PartnerCodeModel,
    PartnerEarningModel,
)


def _normalize_lookup_code(code: str) -> str:
    return (code or "").strip().upper()


class PartnerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_code_by_id(self, id: UUID) -> PartnerCodeModel | None:
        return await self._session.get(PartnerCodeModel, id)

    async def get_account_by_id(self, id: UUID) -> PartnerAccountModel | None:
        return await self._session.get(PartnerAccountModel, id)

    async def get_code_by_code(self, code: str) -> PartnerCodeModel | None:
        normalized = _normalize_lookup_code(code)
        result = await self._session.execute(
            select(PartnerCodeModel).where(
                or_(
                    PartnerCodeModel.code_normalized == normalized,
                    func.upper(func.trim(PartnerCodeModel.code)) == normalized,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_active_code_by_code(self, code: str) -> PartnerCodeModel | None:
        normalized = _normalize_lookup_code(code)
        result = await self._session.execute(
            select(PartnerCodeModel).where(
                or_(
                    PartnerCodeModel.code_normalized == normalized,
                    func.upper(func.trim(PartnerCodeModel.code)) == normalized,
                ),
                PartnerCodeModel.is_active == True,  # noqa: E712
                PartnerCodeModel.lifecycle_status == "active",
                PartnerCodeModel.approval_status == "approved",
            )
        )
        return result.scalar_one_or_none()

    async def get_code_by_public_token_hash(self, token_hash: str) -> PartnerCodeModel | None:
        result = await self._session.execute(
            select(PartnerCodeModel).where(PartnerCodeModel.public_token_hash == token_hash).limit(1)
        )
        return result.scalars().first()

    async def get_code_by_public_slug(self, public_slug: str) -> PartnerCodeModel | None:
        result = await self._session.execute(
            select(PartnerCodeModel).where(PartnerCodeModel.public_slug == public_slug.strip()).limit(1)
        )
        return result.scalars().first()

    async def get_code_link_by_public_slug(self, public_slug: str) -> PartnerCodeLinkModel | None:
        result = await self._session.execute(
            select(PartnerCodeLinkModel).where(PartnerCodeLinkModel.public_slug == public_slug.strip()).limit(1)
        )
        return result.scalars().first()

    async def get_code_link_by_id(self, id: UUID) -> PartnerCodeLinkModel | None:
        return await self._session.get(PartnerCodeLinkModel, id)

    async def get_default_code_link(self, partner_code_id: UUID) -> PartnerCodeLinkModel | None:
        result = await self._session.execute(
            select(PartnerCodeLinkModel)
            .where(
                PartnerCodeLinkModel.partner_code_id == partner_code_id,
                PartnerCodeLinkModel.link_kind == "default",
            )
            .order_by(PartnerCodeLinkModel.created_at.asc(), PartnerCodeLinkModel.id.asc())
            .limit(1)
        )
        return result.scalars().first()

    async def get_active_code_by_public_token_hash(self, token_hash: str) -> PartnerCodeModel | None:
        result = await self._session.execute(
            select(PartnerCodeModel).where(
                PartnerCodeModel.public_token_hash == token_hash,
                PartnerCodeModel.is_active == True,  # noqa: E712
                PartnerCodeModel.lifecycle_status == "active",
                PartnerCodeModel.approval_status == "approved",
            )
        )
        return result.scalars().first()

    async def get_codes_by_partner(self, partner_user_id: UUID) -> list[PartnerCodeModel]:
        result = await self._session.execute(
            select(PartnerCodeModel).where(PartnerCodeModel.partner_user_id == partner_user_id)
        )
        return list(result.scalars().all())

    async def get_codes_by_account(self, partner_account_id: UUID) -> list[PartnerCodeModel]:
        result = await self._session.execute(
            select(PartnerCodeModel).where(PartnerCodeModel.partner_account_id == partner_account_id)
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

    async def create_code_link(self, model: PartnerCodeLinkModel) -> PartnerCodeLinkModel:
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

    async def get_earnings_by_account(
        self, partner_account_id: UUID, offset: int = 0, limit: int = 50
    ) -> list[PartnerEarningModel]:
        result = await self._session.execute(
            select(PartnerEarningModel)
            .where(PartnerEarningModel.partner_account_id == partner_account_id)
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

    async def count_clients_by_account(self, partner_account_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count(func.distinct(PartnerEarningModel.client_user_id))).where(
                PartnerEarningModel.partner_account_id == partner_account_id
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

    async def get_total_earnings_by_account(self, partner_account_id: UUID) -> Decimal:
        result = await self._session.execute(
            select(func.sum(PartnerEarningModel.total_earning)).where(
                PartnerEarningModel.partner_account_id == partner_account_id
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

    async def get_account_stats_map(self, partner_account_ids: list[UUID]) -> dict[UUID, dict[str, Any]]:
        if not partner_account_ids:
            return {}

        code_stats_result = await self._session.execute(
            select(
                PartnerCodeModel.partner_account_id.label("partner_account_id"),
                func.count(PartnerCodeModel.id).label("code_count"),
                func.sum(case((PartnerCodeModel.is_active == True, 1), else_=0)).label("active_code_count"),  # noqa: E712
                func.max(PartnerCodeModel.updated_at).label("last_code_at"),
            )
            .where(PartnerCodeModel.partner_account_id.in_(partner_account_ids))
            .group_by(PartnerCodeModel.partner_account_id)
        )

        earning_stats_result = await self._session.execute(
            select(
                PartnerEarningModel.partner_account_id.label("partner_account_id"),
                func.count(distinct(PartnerEarningModel.client_user_id)).label("total_clients"),
                func.coalesce(func.sum(PartnerEarningModel.total_earning), 0).label("total_earned"),
                func.max(PartnerEarningModel.created_at).label("last_earning_at"),
            )
            .where(PartnerEarningModel.partner_account_id.in_(partner_account_ids))
            .group_by(PartnerEarningModel.partner_account_id)
        )

        stats: dict[UUID, dict[str, Any]] = {
            account_id: {
                "code_count": 0,
                "active_code_count": 0,
                "total_clients": 0,
                "total_earned": Decimal(0),
                "last_activity_at": None,
            }
            for account_id in partner_account_ids
        }

        for row in code_stats_result:
            if row.partner_account_id is None:
                continue
            entry = stats.setdefault(
                row.partner_account_id,
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
            if row.partner_account_id is None:
                continue
            entry = stats.setdefault(
                row.partner_account_id,
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
