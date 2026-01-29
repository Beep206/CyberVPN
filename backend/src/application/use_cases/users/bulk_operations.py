"""Bulk user operations use case."""
from uuid import UUID

from src.domain.enums import UserStatus
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class BulkUserOperationsUseCase:
    """Use case for performing bulk operations on users."""

    def __init__(self, gateway: RemnawaveUserGateway):
        """Initialize the use case with a user gateway.

        Args:
            gateway: The user gateway for interacting with Remnawave API
        """
        self.gateway = gateway

    async def disable_users(self, uuids: list[UUID]) -> int:
        """Disable multiple users.

        Args:
            uuids: List of user UUIDs to disable

        Returns:
            The number of users successfully disabled
        """
        success_count = 0
        for uuid in uuids:
            try:
                await self.gateway.update(uuid, status=UserStatus.DISABLED)
                success_count += 1
            except Exception:
                # Log error but continue with other users
                continue
        return success_count

    async def enable_users(self, uuids: list[UUID]) -> int:
        """Enable multiple users.

        Args:
            uuids: List of user UUIDs to enable

        Returns:
            The number of users successfully enabled
        """
        success_count = 0
        for uuid in uuids:
            try:
                await self.gateway.update(uuid, status=UserStatus.ACTIVE)
                success_count += 1
            except Exception:
                # Log error but continue with other users
                continue
        return success_count
