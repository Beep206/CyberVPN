"""Use case for canceling user's subscription."""

import logging
from datetime import datetime

from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.subscription_client import CachedSubscriptionClient
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway

logger = logging.getLogger(__name__)


class SubscriptionCancellationNotFoundError(ValueError):
    """The reconciled numeric user no longer exists upstream."""


class SubscriptionCancellationIdentityConflictError(ValueError):
    """The upstream response does not match the reconciled numeric identity."""


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

    async def execute(self, user_ref: RemnawaveUserRef) -> datetime:
        """Cancel the user's active subscription.

        Args:
            user_ref: Exact, reconciled Remnawave 3.x numeric identity.

        Raises:
            ValueError: If user not found in Remnawave

        Note:
            - Sets sub_revoked_at to current timestamp in Remnawave
            - Invalidates cached subscription data
            - Does not throw error if subscription is already canceled
        """
        numeric_user_id = user_ref.require_numeric_id()
        user = await self.user_gateway.get_by_ref(user_ref)
        if not user:
            raise SubscriptionCancellationNotFoundError("User not found in VPN backend")
        if user.remnawave_id != numeric_user_id:
            raise SubscriptionCancellationIdentityConflictError(
                "VPN backend returned a different numeric user identity"
            )

        # Repeated cancellation is a read-only success. Do not rotate credentials
        # or emit another upstream mutation for an already-revoked subscription.
        if user.sub_revoked_at is not None:
            await self.subscription_client.invalidate(user_ref)
            logger.info(
                "Subscription cancellation already applied",
                extra={"numeric_identity": True, "already_canceled": True},
            )
            return user.sub_revoked_at

        updated_user = await self.user_gateway.revoke_subscription(
            user_ref,
        )
        if updated_user.remnawave_id != numeric_user_id:
            raise SubscriptionCancellationIdentityConflictError(
                "VPN backend mutation returned a different numeric user identity"
            )
        if updated_user.sub_revoked_at is None:
            raise SubscriptionCancellationIdentityConflictError("VPN backend has not confirmed subscription revocation")

        await self.subscription_client.invalidate(user_ref)

        logger.info(
            "Subscription canceled",
            extra={"numeric_identity": True, "already_canceled": False},
        )
        return updated_user.sub_revoked_at
