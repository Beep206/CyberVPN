"""CyberVPN Telegram Bot — Referral system service.

Business logic for referral links, stats, and reward withdrawal.
"""

from __future__ import annotations

from typing import Any

import structlog

from src.services.api_client import CyberVPNAPIClient
from src.services.cache_service import CacheService

logger = structlog.get_logger(__name__)


class ReferralService:
    """Referral program business logic layer.

    Provides methods for generating referral links, fetching stats,
    and withdrawing earned bonuses through the Backend API.
    """

    def __init__(
        self,
        api_client: CyberVPNAPIClient,
        cache: CacheService,
    ) -> None:
        self._api = api_client
        self._cache = cache

    async def get_referral_stats(self, telegram_id: int) -> dict[str, Any]:
        """Get referral statistics for a user.

        Checks cache first, falls back to API.

        Args:
            telegram_id: User's Telegram ID.

        Returns:
            Referral stats: count, bonus_days, link.
        """
        cache_key = f"referral_stats:{telegram_id}"
        cached = await self._cache.get_json(cache_key)
        if cached is not None:
            return cached

        stats = await self._api.get_referral_stats(telegram_id)
        await self._cache.set_json(cache_key, stats, ttl=120)
        return stats

    async def get_referral_link(self, telegram_id: int, bot_username: str) -> str:
        """Generate the referral deep link for a user.

        Args:
            telegram_id: User's Telegram ID.
            bot_username: Bot's username.

        Returns:
            Full referral link (https://t.me/bot?start=ref_123).
        """
        from src.utils.deep_links import encode_referral_payload

        payload = encode_referral_payload(telegram_id)
        return f"https://t.me/{bot_username}?start={payload}"

    async def withdraw_bonus(
        self,
        telegram_id: int,
        points: int,
    ) -> dict[str, Any]:
        """Withdraw referral bonus points/days.

        Args:
            telegram_id: User's Telegram ID.
            points: Number of points to withdraw.

        Returns:
            Updated referral balance.
        """
        result = await self._api.withdraw_referral_points(telegram_id, points)
        # Invalidate cached stats
        await self._cache.delete(f"referral_stats:{telegram_id}")
        logger.info(
            "referral_bonus_withdrawn",
            telegram_id=telegram_id,
            points=points,
        )
        return result

    async def invalidate_stats(self, telegram_id: int) -> None:
        """Invalidate cached referral stats after changes."""
        await self._cache.delete(f"referral_stats:{telegram_id}")
