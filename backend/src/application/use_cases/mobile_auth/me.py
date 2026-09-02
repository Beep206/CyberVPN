"""Mobile user profile use case.

Handles fetching current user profile for mobile app users.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.mobile_auth import (
    SubscriptionInfoDTO,
    SubscriptionStatus,
    UserResponseDTO,
)
from src.application.services.remnawave_identity_access import resolve_exact_mapped_mobile_user_ref
from src.application.use_cases.mobile_auth.user_response import build_mobile_user_response
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
    session: AsyncSession | None = None

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

        # Fetch an exact identity-bound subscription; dependency failures are
        # surfaced rather than converted into an empty entitlement.
        user_ref = await resolve_exact_mapped_mobile_user_ref(self.session, user)
        if self.subscription_client and user_ref is not None:
            subscription = await self.subscription_client.get_subscription(user_ref)
        else:
            subscription = SubscriptionInfoDTO(status=SubscriptionStatus.NONE)

        return build_mobile_user_response(user, subscription=subscription)
