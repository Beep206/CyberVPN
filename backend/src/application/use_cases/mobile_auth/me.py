"""Mobile user profile use case.

Handles fetching current user profile for mobile app users.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from src.application.dto.mobile_auth import (
    SubscriptionInfoDTO,
    SubscriptionStatus,
    UserResponseDTO,
)
from src.domain.exceptions import UserNotFoundError
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository

if TYPE_CHECKING:
    from src.infrastructure.remnawave.subscription_client import CachedSubscriptionClient


@dataclass
class MobileGetProfileUseCase:
    """Use case for fetching mobile user profile.

    Returns current user profile with subscription information.
    """

    user_repo: MobileUserRepository
    subscription_client: CachedSubscriptionClient | None = None

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

        # Fetch subscription from Remnawave (cached, with fallback to NONE).
        if self.subscription_client and user.remnawave_uuid:
            subscription = await self.subscription_client.get_subscription(user.remnawave_uuid)
        else:
            subscription = SubscriptionInfoDTO(status=SubscriptionStatus.NONE)

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
