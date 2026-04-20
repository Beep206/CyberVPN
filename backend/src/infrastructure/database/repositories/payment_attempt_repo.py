from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import PaymentAttemptStatus
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel

ACTIVE_PAYMENT_ATTEMPT_STATUSES = (
    PaymentAttemptStatus.PENDING.value,
    PaymentAttemptStatus.PROCESSING.value,
)
SUCCEEDED_PAYMENT_ATTEMPT_STATUSES = (PaymentAttemptStatus.SUCCEEDED.value,)


class PaymentAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: PaymentAttemptModel) -> PaymentAttemptModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_id(self, payment_attempt_id: UUID) -> PaymentAttemptModel | None:
        return await self._session.get(PaymentAttemptModel, payment_attempt_id)

    async def get_by_payment_id(self, payment_id: UUID) -> PaymentAttemptModel | None:
        result = await self._session.execute(
            select(PaymentAttemptModel).where(PaymentAttemptModel.payment_id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_order_and_idempotency_key(
        self,
        *,
        order_id: UUID,
        idempotency_key: str,
    ) -> PaymentAttemptModel | None:
        result = await self._session.execute(
            select(PaymentAttemptModel).where(
                PaymentAttemptModel.order_id == order_id,
                PaymentAttemptModel.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_for_order(self, order_id: UUID) -> PaymentAttemptModel | None:
        result = await self._session.execute(
            select(PaymentAttemptModel)
            .where(PaymentAttemptModel.order_id == order_id)
            .order_by(PaymentAttemptModel.attempt_number.desc(), PaymentAttemptModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_active_for_order(self, order_id: UUID) -> PaymentAttemptModel | None:
        result = await self._session.execute(
            select(PaymentAttemptModel)
            .where(
                PaymentAttemptModel.order_id == order_id,
                PaymentAttemptModel.status.in_(ACTIVE_PAYMENT_ATTEMPT_STATUSES),
            )
            .order_by(PaymentAttemptModel.attempt_number.desc(), PaymentAttemptModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_for_order(self, order_id: UUID) -> list[PaymentAttemptModel]:
        result = await self._session.execute(
            select(PaymentAttemptModel)
            .where(PaymentAttemptModel.order_id == order_id)
            .order_by(PaymentAttemptModel.attempt_number.asc(), PaymentAttemptModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_latest_succeeded_for_order(self, order_id: UUID) -> PaymentAttemptModel | None:
        result = await self._session.execute(
            select(PaymentAttemptModel)
            .where(
                PaymentAttemptModel.order_id == order_id,
                PaymentAttemptModel.status.in_(SUCCEEDED_PAYMENT_ATTEMPT_STATUSES),
            )
            .order_by(PaymentAttemptModel.attempt_number.desc(), PaymentAttemptModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
