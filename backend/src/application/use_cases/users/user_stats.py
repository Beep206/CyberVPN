"""User statistics use case."""
from uuid import UUID

from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class UserStatsUseCase:
    """Use case for retrieving user statistics."""

    def __init__(self, gateway: RemnawaveUserGateway):
        """Initialize the use case with a user gateway.

        Args:
            gateway: The user gateway for interacting with Remnawave API
        """
        self.gateway = gateway

    async def execute(self, uuid: UUID) -> dict:
        """Execute the user stats use case.

        Args:
            uuid: The UUID of the user to get statistics for

        Returns:
            A dictionary containing user traffic statistics

        Raises:
            Exception: If user not found or stats retrieval fails
        """
        user = await self.gateway.get_by_uuid(uuid)
        if not user:
            raise ValueError(f"User with UUID {uuid} not found")

        return {
            "uuid": str(user.uuid),
            "username": user.username,
            "data_usage": user.data_usage,
            "data_limit": user.data_limit,
            "usage_percentage": (
                (user.data_usage / user.data_limit * 100)
                if user.data_limit and user.data_limit > 0
                else 0.0
            ),
            "remaining_data": (
                max(0, user.data_limit - user.data_usage) if user.data_limit else None
            ),
            "status": user.status.value if hasattr(user.status, "value") else user.status,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "expires_at": user.expires_at.isoformat() if user.expires_at else None,
        }
