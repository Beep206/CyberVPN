from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.attribution_touchpoint_repo import AttributionTouchpointRepository


class ListAttributionTouchpointsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._touchpoints = AttributionTouchpointRepository(session)

    async def execute(
        self,
        *,
        user_id: UUID | None = None,
        quote_session_id: UUID | None = None,
        order_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        return await self._touchpoints.list(
            user_id=user_id,
            quote_session_id=quote_session_id,
            order_id=order_id,
            limit=limit,
            offset=offset,
        )
