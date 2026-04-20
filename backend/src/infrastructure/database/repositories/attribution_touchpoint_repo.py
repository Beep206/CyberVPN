from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.attribution_touchpoint_model import AttributionTouchpointModel


class AttributionTouchpointRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: AttributionTouchpointModel) -> AttributionTouchpointModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_by_id(self, touchpoint_id: UUID) -> AttributionTouchpointModel | None:
        return await self._session.get(AttributionTouchpointModel, touchpoint_id)

    async def list(
        self,
        *,
        user_id: UUID | None = None,
        quote_session_id: UUID | None = None,
        order_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AttributionTouchpointModel]:
        stmt = select(AttributionTouchpointModel).order_by(
            AttributionTouchpointModel.occurred_at.asc(),
            AttributionTouchpointModel.created_at.asc(),
        )
        if user_id is not None:
            stmt = stmt.where(AttributionTouchpointModel.user_id == user_id)
        if quote_session_id is not None:
            stmt = stmt.where(AttributionTouchpointModel.quote_session_id == quote_session_id)
        if order_id is not None:
            stmt = stmt.where(AttributionTouchpointModel.order_id == order_id)
        result = await self._session.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def list_for_resolution_context(
        self,
        *,
        quote_session_id: UUID | None,
        checkout_session_id: UUID,
        order_id: UUID,
    ) -> list[AttributionTouchpointModel]:
        clauses = [
            AttributionTouchpointModel.checkout_session_id == checkout_session_id,
            AttributionTouchpointModel.order_id == order_id,
        ]
        if quote_session_id is not None:
            clauses.append(AttributionTouchpointModel.quote_session_id == quote_session_id)

        stmt = (
            select(AttributionTouchpointModel)
            .where(or_(*clauses))
            .order_by(
                AttributionTouchpointModel.occurred_at.asc(),
                AttributionTouchpointModel.created_at.asc(),
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
