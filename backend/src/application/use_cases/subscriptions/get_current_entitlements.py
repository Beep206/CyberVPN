"""Use case for retrieving the current effective subscription entitlements."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.entitlements_service import EntitlementsService


class GetCurrentEntitlementsUseCase:
    """Resolve the current entitlement snapshot for a mobile user."""

    def __init__(self, session: AsyncSession) -> None:
        self._entitlements = EntitlementsService(session)

    async def execute(self, user_id: UUID) -> dict:
        return await self._entitlements.get_current_snapshot(user_id)
