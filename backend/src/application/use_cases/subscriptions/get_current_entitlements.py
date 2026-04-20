"""Use case for retrieving the current effective subscription entitlements."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.service_access import GetCurrentEntitlementStateUseCase


class GetCurrentEntitlementsUseCase:
    """Resolve the current entitlement snapshot for a mobile user."""

    def __init__(self, session: AsyncSession) -> None:
        self._entitlements = GetCurrentEntitlementStateUseCase(session)

    async def execute(self, user_id: UUID, *, auth_realm_id: UUID | None = None) -> dict:
        return await self._entitlements.execute(
            customer_account_id=user_id,
            auth_realm_id=auth_realm_id,
        )
