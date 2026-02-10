"""Update user use case."""

from typing import Any
from uuid import UUID

from src.domain.entities.user import User
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class UpdateUserUseCase:
    """Use case for updating user information."""

    def __init__(self, gateway: RemnawaveUserGateway):
        """Initialize the use case with a user gateway.

        Args:
            gateway: The user gateway for interacting with Remnawave API
        """
        self.gateway = gateway

    async def execute(self, uuid: UUID, **kwargs: Any) -> User:
        """Execute the update user use case.

        Args:
            uuid: The UUID of the user to update
            **kwargs: Keyword arguments for fields to update (e.g., username, email, data_limit)

        Returns:
            The updated User entity

        Raises:
            Exception: If user update fails or user not found
        """
        return await self.gateway.update(uuid, **kwargs)
