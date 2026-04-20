from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.commissionability_evaluation_model import CommissionabilityEvaluationModel


class CommissionabilityEvaluationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: CommissionabilityEvaluationModel) -> CommissionabilityEvaluationModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_id(self, evaluation_id: UUID) -> CommissionabilityEvaluationModel | None:
        return await self._session.get(CommissionabilityEvaluationModel, evaluation_id)

    async def get_by_order_id(self, order_id: UUID) -> CommissionabilityEvaluationModel | None:
        result = await self._session.execute(
            select(CommissionabilityEvaluationModel).where(CommissionabilityEvaluationModel.order_id == order_id)
        )
        return result.scalar_one_or_none()
