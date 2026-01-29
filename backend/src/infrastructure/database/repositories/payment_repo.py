from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.payment_model import PaymentModel


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> PaymentModel | None:
        return await self._session.get(PaymentModel, id)

    async def get_by_external_id(self, external_id: str) -> PaymentModel | None:
        result = await self._session.execute(
            select(PaymentModel).where(PaymentModel.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_uuid(self, user_uuid: UUID, offset: int = 0, limit: int = 100) -> list[PaymentModel]:
        result = await self._session.execute(
            select(PaymentModel)
            .where(PaymentModel.user_uuid == user_uuid)
            .order_by(PaymentModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, model: PaymentModel) -> PaymentModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(self, model: PaymentModel) -> PaymentModel:
        await self._session.merge(model)
        await self._session.flush()
        return model
