"""Update user use case."""

from typing import Any

from src.domain.entities.user import User
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class UpdateUserUseCase:
    """Use case for updating user information."""

    def __init__(self, gateway: RemnawaveUserGateway):
        """Initialize the use case with a user gateway.

        Args:
            gateway: The user gateway for interacting with Remnawave API
        """
        self.gateway = gateway

    async def execute(self, user_ref: RemnawaveUserRef, **kwargs: Any) -> User:
        """Execute the update user use case.

        Args:
            user_ref: Reconciled numeric Remnawave user reference
            **kwargs: Keyword arguments for fields to update (e.g., username, email, data_limit)

        Returns:
            The updated User entity

        Raises:
            Exception: If user update fails or user not found
        """
        user_ref.require_numeric_id()
        return await self.gateway.update(user_ref, **kwargs)
