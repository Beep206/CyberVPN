"""Delete user use case."""

from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class DeleteUserUseCase:
    """Use case for deleting a user."""

    def __init__(self, gateway: RemnawaveUserGateway):
        """Initialize the use case with a user gateway.

        Args:
            gateway: The user gateway for interacting with Remnawave API
        """
        self.gateway = gateway

    async def execute(self, user_ref: RemnawaveUserRef) -> None:
        """Execute the delete user use case.

        Args:
            user_ref: Reconciled numeric Remnawave user reference

        Raises:
            Exception: If user deletion fails or user not found
        """
        user_ref.require_numeric_id()
        await self.gateway.delete(user_ref)
