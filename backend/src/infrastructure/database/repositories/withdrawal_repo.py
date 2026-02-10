"""Infrastructure repository for withdrawal_requests table."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.withdrawal_request_model import (
    WithdrawalRequestModel,
)


class WithdrawalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> WithdrawalRequestModel | None:
        return await self._session.get(WithdrawalRequestModel, id)

    async def create(self, model: WithdrawalRequestModel) -> WithdrawalRequestModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(self, model: WithdrawalRequestModel) -> WithdrawalRequestModel:
        await self._session.merge(model)
        await self._session.flush()
        return model

    async def get_by_user(self, user_id: UUID, offset: int = 0, limit: int = 50) -> list[WithdrawalRequestModel]:
        result = await self._session.execute(
            select(WithdrawalRequestModel)
            .where(WithdrawalRequestModel.user_id == user_id)
            .order_by(WithdrawalRequestModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_pending(self, offset: int = 0, limit: int = 50) -> list[WithdrawalRequestModel]:
        result = await self._session.execute(
            select(WithdrawalRequestModel)
            .where(WithdrawalRequestModel.status == "pending")
            .order_by(WithdrawalRequestModel.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
