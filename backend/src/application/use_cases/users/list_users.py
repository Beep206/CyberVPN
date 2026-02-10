"""List users use case."""

from src.domain.entities.user import User
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class ListUsersUseCase:
    """Use case for listing users with pagination."""

    def __init__(self, gateway: RemnawaveUserGateway):
        """Initialize the use case with a user gateway.

        Args:
            gateway: The user gateway for interacting with Remnawave API
        """
        self.gateway = gateway

    async def execute(self, offset: int = 0, limit: int = 100) -> list[User]:
        """Execute the list users use case.

        Args:
            offset: The number of users to skip (default: 0)
            limit: The maximum number of users to return (default: 100)

        Returns:
            A list of User entities
        """
        all_users = await self.gateway.get_all()
        return all_users[offset : offset + limit]
