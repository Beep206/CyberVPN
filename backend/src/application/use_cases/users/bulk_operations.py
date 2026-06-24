"""Bulk user operations use case."""

import logging
from uuid import UUID

from src.domain.entities.user import User
from src.domain.enums import UserStatus
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway

logger = logging.getLogger(__name__)


class BulkUserOperationsUseCase:
    """Use case for performing bulk operations on users."""

    def __init__(self, gateway: RemnawaveUserGateway):
        """Initialize the use case with a user gateway.

        Args:
            gateway: The user gateway for interacting with Remnawave API
        """
        self.gateway = gateway

    async def disable_users(self, uuids: list[UUID]) -> list[User]:
        """Disable multiple users.

        Args:
            uuids: List of user UUIDs to disable

        Returns:
            The users successfully disabled
        """
        updated_users: list[User] = []
        for uuid in uuids:
            try:
                updated_users.append(await self.gateway.update(uuid, status=UserStatus.DISABLED))
            except Exception as e:
                logger.warning("Failed to disable user %s: %s", uuid, e)
                continue
        return updated_users

    async def enable_users(self, uuids: list[UUID]) -> list[User]:
        """Enable multiple users.

        Args:
            uuids: List of user UUIDs to enable

        Returns:
            The users successfully enabled
        """
        updated_users: list[User] = []
        for uuid in uuids:
            try:
                updated_users.append(await self.gateway.update(uuid, status=UserStatus.ACTIVE))
            except Exception as e:
                logger.warning("Failed to enable user %s: %s", uuid, e)
                continue
        return updated_users
