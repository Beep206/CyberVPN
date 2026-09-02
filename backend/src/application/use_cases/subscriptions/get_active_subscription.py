"""Use case for retrieving user's active subscription."""

import logging

from src.application.dto.mobile_auth import SubscriptionInfoDTO
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
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

    async def execute(self, user_ref: RemnawaveUserRef) -> SubscriptionInfoDTO:
        """Get the active subscription for a user.

        Args:
            user_ref: Exact reconciled Remnawave 3.x numeric identity.

        Returns:
            SubscriptionInfoDTO with current subscription status and details

        Note:
            Uses exact identity-bound cached data with a five-minute TTL.
            Provider or identity failures propagate as a stable dependency error.
        """
        user_ref.require_numeric_id()
        subscription = await self.subscription_client.get_subscription(user_ref)

        logger.info(
            "Active subscription retrieved",
            extra={
                "status": subscription.status,
                "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            },
        )

        return subscription
