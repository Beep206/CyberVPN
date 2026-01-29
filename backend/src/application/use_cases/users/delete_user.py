"""Delete user use case."""
from uuid import UUID

from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class DeleteUserUseCase:
    """Use case for deleting a user."""

    def __init__(self, gateway: RemnawaveUserGateway):
        """Initialize the use case with a user gateway.

        Args:
            gateway: The user gateway for interacting with Remnawave API
        """
        self.gateway = gateway

    async def execute(self, uuid: UUID) -> None:
        """Execute the delete user use case.

        Args:
            uuid: The UUID of the user to delete

        Raises:
            Exception: If user deletion fails or user not found
        """
        await self.gateway.delete(uuid)
