from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.attribution_touchpoint_repo import AttributionTouchpointRepository


class GetAttributionTouchpointUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._touchpoints = AttributionTouchpointRepository(session)

    async def execute(self, *, touchpoint_id: UUID):
        return await self._touchpoints.get_by_id(touchpoint_id)
