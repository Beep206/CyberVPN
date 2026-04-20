from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.refund_model import RefundModel


class RefundRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: RefundModel) -> RefundModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_id(self, refund_id: UUID) -> RefundModel | None:
        return await self._session.get(RefundModel, refund_id)

    async def get_by_order_and_idempotency_key(
        self,
        *,
        order_id: UUID,
        idempotency_key: str,
    ) -> RefundModel | None:
        result = await self._session.execute(
            select(RefundModel).where(
                RefundModel.order_id == order_id,
                RefundModel.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_order(self, order_id: UUID) -> list[RefundModel]:
        result = await self._session.execute(
            select(RefundModel)
            .where(RefundModel.order_id == order_id)
            .order_by(RefundModel.created_at.asc(), RefundModel.submitted_at.asc())
        )
        return list(result.scalars().all())

    async def sum_for_order_by_statuses(self, *, order_id: UUID, statuses: tuple[str, ...]) -> Decimal:
        result = await self._session.execute(
            select(func.coalesce(func.sum(RefundModel.amount), 0)).where(
                RefundModel.order_id == order_id,
                RefundModel.refund_status.in_(statuses),
            )
        )
        value = result.scalar_one()
        return Decimal(str(value or 0))
