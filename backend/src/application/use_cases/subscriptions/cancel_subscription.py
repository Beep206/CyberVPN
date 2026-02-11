"""Use case for canceling user's subscription."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from src.infrastructure.remnawave.subscription_client import CachedSubscriptionClient
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway

logger = logging.getLogger(__name__)


class CancelSubscriptionUseCase:
    """Use case for canceling a user's active subscription."""

    def __init__(
        self,
        user_gateway: RemnawaveUserGateway,
        subscription_client: CachedSubscriptionClient,
    ):
        """Initialize with Remnawave gateway and subscription client.

        Args:
            user_gateway: Gateway for updating user data in Remnawave
            subscription_client: Client for invalidating cached subscription data
        """
        self.user_gateway = user_gateway
        self.subscription_client = subscription_client

    async def execute(self, user_id: UUID) -> None:
        """Cancel the user's active subscription.

        Args:
            user_id: UUID of the admin user (also used as Remnawave UUID)

        Raises:
            ValueError: If user not found in Remnawave

        Note:
            - Sets sub_revoked_at to current timestamp in Remnawave
            - Invalidates cached subscription data
            - Does not throw error if subscription is already canceled
        """
        # Check if user exists in Remnawave
        user = await self.user_gateway.get_by_uuid(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found in VPN backend")

        # Set subscription revocation timestamp
        now = datetime.now(UTC)
        await self.user_gateway.update(
            uuid=user_id,
            subRevokedAt=now.isoformat(),  # Remnawave expects camelCase
        )

        # Invalidate cached subscription data
        await self.subscription_client.invalidate(str(user_id))

        logger.info(
            "Subscription canceled",
            extra={"user_id": str(user_id), "revoked_at": now.isoformat()},
        )
