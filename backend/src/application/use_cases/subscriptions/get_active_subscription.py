"""Use case for retrieving user's active subscription."""

import logging
from uuid import UUID

from src.application.dto.mobile_auth import SubscriptionInfoDTO
from src.infrastructure.remnawave.subscription_client import CachedSubscriptionClient

logger = logging.getLogger(__name__)


class GetActiveSubscriptionUseCase:
    """Use case for retrieving a user's active subscription information."""

    def __init__(self, subscription_client: CachedSubscriptionClient):
        """Initialize with cached subscription client.

        Args:
            subscription_client: Client for fetching subscription data from Remnawave
        """
        self.subscription_client = subscription_client

    async def execute(self, user_id: UUID) -> SubscriptionInfoDTO:
        """Get the active subscription for a user.

        Args:
            user_id: UUID of the admin user (also used as Remnawave UUID)

        Returns:
            SubscriptionInfoDTO with current subscription status and details

        Note:
            Uses cached data with 5-minute TTL. Falls back to NONE status on errors.
        """
        subscription = await self.subscription_client.get_subscription(str(user_id))

        logger.info(
            "Active subscription retrieved",
            extra={
                "user_id": str(user_id),
                "status": subscription.status,
                "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            },
        )

        return subscription
