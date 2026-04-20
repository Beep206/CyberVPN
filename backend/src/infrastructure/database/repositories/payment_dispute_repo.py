from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.payment_dispute_model import PaymentDisputeModel


class PaymentDisputeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: PaymentDisputeModel) -> PaymentDisputeModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_id(self, payment_dispute_id: UUID) -> PaymentDisputeModel | None:
        return await self._session.get(PaymentDisputeModel, payment_dispute_id)

    async def get_by_provider_reference(
        self,
        *,
        provider: str,
        external_reference: str,
    ) -> PaymentDisputeModel | None:
        result = await self._session.execute(
            select(PaymentDisputeModel).where(
                PaymentDisputeModel.provider == provider,
                PaymentDisputeModel.external_reference == external_reference,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_order(self, order_id: UUID) -> list[PaymentDisputeModel]:
        result = await self._session.execute(
            select(PaymentDisputeModel)
            .where(PaymentDisputeModel.order_id == order_id)
            .order_by(PaymentDisputeModel.created_at.asc(), PaymentDisputeModel.opened_at.asc())
        )
        return list(result.scalars().all())
