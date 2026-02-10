"""Get user use case."""

from uuid import UUID

from src.domain.entities.user import User
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class GetUserUseCase:
    """Use case for retrieving user information."""

    def __init__(self, gateway: RemnawaveUserGateway):
        """Initialize the use case with a user gateway.

        Args:
            gateway: The user gateway for interacting with Remnawave API
        """
        self.gateway = gateway

    async def execute(self, uuid: UUID) -> User | None:
        """Execute the get user by UUID use case.

        Args:
            uuid: The UUID of the user to retrieve

        Returns:
            The User entity if found, None otherwise
        """
        return await self.gateway.get_by_uuid(uuid)

    async def execute_by_username(self, username: str) -> User | None:
        """Execute the get user by username use case.

        Args:
            username: The username of the user to retrieve

        Returns:
            The User entity if found, None otherwise
        """
        return await self.gateway.get_by_username(username)
