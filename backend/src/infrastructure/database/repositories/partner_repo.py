"""Infrastructure repository for partner_codes and partner_earnings tables."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
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
