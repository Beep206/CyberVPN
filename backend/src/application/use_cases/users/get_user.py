"""Get user use case."""

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

    async def execute(self, user_id: int) -> User | None:
        """Execute the get user by numeric Remnawave id use case.

        Args:
            user_id: The positive numeric Remnawave user id to retrieve

        Returns:
            The User entity if found, None otherwise
        """
        if isinstance(user_id, bool) or user_id <= 0:
            raise ValueError("Remnawave numeric user id must be positive")
        return await self.gateway.get_by_id(user_id)

    async def execute_by_username(self, username: str) -> User | None:
        """Execute the get user by username use case.

        Args:
            username: The username of the user to retrieve

        Returns:
            The User entity if found, None otherwise
        """
        return await self.gateway.get_by_username(username)
