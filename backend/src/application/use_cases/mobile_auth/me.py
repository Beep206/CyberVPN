"""Mobile user profile use case.

Handles fetching current user profile for mobile app users.
"""

from dataclasses import dataclass
from uuid import UUID

from src.application.dto.mobile_auth import (
    SubscriptionInfoDTO,
    SubscriptionStatus,
    UserResponseDTO,
)
from src.domain.exceptions import UserNotFoundError
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository


@dataclass
class MobileGetProfileUseCase:
    """Use case for fetching mobile user profile.

    Returns current user profile with subscription information.
    """

    user_repo: MobileUserRepository

    async def execute(self, user_id: UUID) -> UserResponseDTO:
        """Get user profile.

        Args:
            user_id: UUID of the authenticated user.

        Returns:
            UserResponseDTO with user profile and subscription info.

        Raises:
            UserNotFoundError: If user not found or inactive.
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(identifier=str(user_id))

        if not user.is_active:
            raise UserNotFoundError(identifier=str(user_id))

        # Build subscription info
        # TODO: Fetch actual subscription from Remnawave
        subscription = SubscriptionInfoDTO(
            status=SubscriptionStatus.NONE,
        )

        return UserResponseDTO(
            id=user.id,
            email=user.email,
            username=user.username,
            status=user.status,
            telegram_id=user.telegram_id,
            telegram_username=user.telegram_username,
            created_at=user.created_at,
            subscription=subscription,
        )
