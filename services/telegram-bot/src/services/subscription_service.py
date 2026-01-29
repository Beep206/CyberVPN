"""Subscription business logic service for CyberVPN Telegram Bot.

Provides high-level subscription operations with caching and error handling.
Acts as a business logic layer between handlers and the API client.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from pydantic import ValidationError

from src.models.subscription import SubscriptionPlan
from src.services.api_client import APIError, NotFoundError

if TYPE_CHECKING:
    from src.services.api_client import CyberVPNAPIClient
    from src.services.cache_service import CacheService

logger = structlog.get_logger(__name__)


class SubscriptionService:
    """Business logic layer for subscription operations.

    Manages subscription plans, user subscriptions, and trial activations
    with caching and graceful error handling.
    """

    def __init__(
        self,
        api_client: CyberVPNAPIClient,
        cache: CacheService,
    ) -> None:
        """Initialize subscription service.

        Args:
            api_client: Backend API client instance.
            cache: Redis cache service instance.
        """
        self._api = api_client
        self._cache = cache

    async def get_plans(
        self,
        telegram_id: int | None = None,
        force_refresh: bool = False,
    ) -> list[SubscriptionPlan]:
        """Get available subscription plans for a user.

        Args:
            telegram_id: User's Telegram ID for personalized plans (optional).
            force_refresh: Skip cache and fetch fresh data.

        Returns:
            List of available subscription plans.

        Raises:
            APIError: On backend communication errors.
        """
        # Try cache first
        if not force_refresh:
            cached_plans = await self._cache.get_plans()
            if cached_plans is not None:
                try:
                    return [SubscriptionPlan.model_validate(p) for p in cached_plans]
                except ValidationError:
                    logger.warning("subscription_plans_cache_invalid")
                    await self._cache.invalidate_plans()

        # Fetch from API
        try:
            plans_data = await self._api.get_available_plans(telegram_id=telegram_id)
            logger.info("subscription_plans_fetched", count=len(plans_data))

            # Parse and validate
            plans = [SubscriptionPlan.model_validate(p) for p in plans_data]

            # Cache for future requests
            await self._cache.set_plans(plans_data, ttl=600)

            return plans

        except APIError as exc:
            logger.error(
                "subscription_plans_fetch_error",
                telegram_id=telegram_id,
                error=str(exc),
            )
            raise

    async def get_user_subscription(
        self,
        telegram_id: int,
        force_refresh: bool = False,
    ) -> dict[str, Any] | None:
        """Get user's current subscription details.

        Args:
            telegram_id: User's Telegram ID.
            force_refresh: Skip cache and fetch fresh data.

        Returns:
            Subscription data dict or None if no subscription.

        Raises:
            APIError: On backend communication errors.
        """
        # Try cache first
        if not force_refresh:
            cached_user = await self._cache.get_user(telegram_id)
            if cached_user is not None and "subscription" in cached_user:
                return cached_user.get("subscription")

        # Fetch from API
        try:
            user_data = await self._api.get_user(telegram_id)
            logger.info("user_subscription_fetched", telegram_id=telegram_id)

            # Cache user data
            await self._cache.set_user(telegram_id, user_data, ttl=300)

            return user_data.get("subscription")

        except NotFoundError:
            logger.info("user_not_found", telegram_id=telegram_id)
            return None
        except APIError as exc:
            logger.error(
                "user_subscription_fetch_error",
                telegram_id=telegram_id,
                error=str(exc),
            )
            raise

    async def create_subscription(
        self,
        telegram_id: int,
        plan_id: str,
        duration_days: int,
        *,
        is_trial: bool = False,
    ) -> dict[str, Any]:
        """Create a new subscription for a user.

        Args:
            telegram_id: User's Telegram ID.
            plan_id: Subscription plan identifier.
            duration_days: Subscription duration in days.
            is_trial: Whether this is a trial subscription (default: False).

        Returns:
            Created subscription data dict.

        Raises:
            APIError: On backend errors (e.g., trial already used).
        """
        try:
            subscription = await self._api.create_subscription(
                telegram_id=telegram_id,
                plan_id=plan_id,
                duration_days=duration_days,
                is_trial=is_trial,
            )
            logger.info(
                "subscription_created",
                telegram_id=telegram_id,
                plan_id=plan_id,
                is_trial=is_trial,
            )

            # Invalidate user cache to force refresh
            await self._cache.invalidate_user(telegram_id)

            return subscription

        except APIError as exc:
            logger.error(
                "subscription_create_error",
                telegram_id=telegram_id,
                plan_id=plan_id,
                error=str(exc),
            )
            raise

    async def activate_trial(
        self,
        telegram_id: int,
        trial_plan_id: str,
        trial_days: int,
    ) -> dict[str, Any]:
        """Activate trial subscription for a user.

        Args:
            telegram_id: User's Telegram ID.
            trial_plan_id: Trial plan identifier.
            trial_days: Trial duration in days.

        Returns:
            Created trial subscription data.

        Raises:
            APIError: On backend errors (e.g., trial already used, user ineligible).
        """
        return await self.create_subscription(
            telegram_id=telegram_id,
            plan_id=trial_plan_id,
            duration_days=trial_days,
            is_trial=True,
        )

    async def get_user_config(self, telegram_id: int) -> dict[str, Any]:
        """Get user's VPN connection configuration.

        Args:
            telegram_id: User's Telegram ID.

        Returns:
            Config data with connection link.

        Raises:
            APIError: On backend errors (e.g., no active subscription).
        """
        try:
            config = await self._api.get_user_config(telegram_id)
            logger.info("user_config_fetched", telegram_id=telegram_id)
            return config

        except APIError as exc:
            logger.error(
                "user_config_fetch_error",
                telegram_id=telegram_id,
                error=str(exc),
            )
            raise
