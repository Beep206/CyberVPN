from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.payment_model import PaymentModel


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> PaymentModel | None:
        return await self._session.get(PaymentModel, id)

    async def get_by_external_id(self, external_id: str) -> PaymentModel | None:
        result = await self._session.execute(select(PaymentModel).where(PaymentModel.external_id == external_id))
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

    async def get_paginated(self, offset: int = 0, limit: int = 100) -> list[PaymentModel]:
        result = await self._session.execute(
            select(PaymentModel).order_by(PaymentModel.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_user_uuid(self, user_uuid: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(PaymentModel).where(PaymentModel.user_uuid == user_uuid)
        )
        return int(result.scalar_one() or 0)

    async def get_total_amount_by_user_uuid(self, user_uuid: UUID) -> float:
        result = await self._session.execute(
            select(func.coalesce(func.sum(PaymentModel.amount), 0)).where(PaymentModel.user_uuid == user_uuid)
        )
        return float(result.scalar_one() or 0)

    async def create(self, model: PaymentModel) -> PaymentModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(self, model: PaymentModel) -> PaymentModel:
        await self._session.merge(model)
        await self._session.flush()
        return model

    async def get_latest_active_plan_payment(
        self,
        user_uuid: UUID,
        *,
        at: datetime | None = None,
    ) -> PaymentModel | None:
        now = at or datetime.now(UTC)
        result = await self._session.execute(
            select(PaymentModel)
            .where(
                PaymentModel.user_uuid == user_uuid,
                PaymentModel.status == "completed",
                PaymentModel.plan_id.is_not(None),
            )
            .order_by(PaymentModel.created_at.desc())
        )

        for payment in result.scalars().all():
            if payment.subscription_days <= 0:
                return payment

            expires_at = payment.created_at + timedelta(days=payment.subscription_days)
            if expires_at > now:
                return payment

        return None
