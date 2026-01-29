"""CyberVPN Telegram Bot — Broadcast service.

Handles broadcast message creation and sending through the
Backend API's broadcast system.
"""

from __future__ import annotations

from typing import Any

import structlog

from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)


class BroadcastService:
    """Broadcast message management service.

    Manages broadcast creation, preview, and sending through
    the CyberVPN Backend API. Actual message delivery is handled
    by the task-worker service.
    """

    def __init__(self, api_client: CyberVPNAPIClient) -> None:
        self._api = api_client

    async def create_broadcast(
        self,
        message: str,
        audience: str,
    ) -> dict[str, Any]:
        """Create and queue a broadcast message.

        Args:
            message: Broadcast text (HTML).
            audience: Target audience (all, active, expired, trial).

        Returns:
            Broadcast job data with id, status, and recipient count.
        """
        logger.info(
            "creating_broadcast",
            audience=audience,
            message_length=len(message),
        )
        result = await self._api.create_broadcast(
            message=message,
            audience=audience,
        )
        logger.info(
            "broadcast_created",
            broadcast_id=result.get("id"),
            recipients=result.get("recipient_count"),
        )
        return result

    async def get_audience_count(self, audience: str) -> int:
        """Get estimated recipient count for an audience type.

        Args:
            audience: Audience type (all, active, expired, trial).

        Returns:
            Estimated number of recipients.
        """
        try:
            stats = await self._api.get_statistics()
            match audience:
                case "all":
                    return stats.get("total_users", 0)
                case "active":
                    return stats.get("active_subscriptions", 0)
                case "expired":
                    return stats.get("expired_subscriptions", 0)
                case "trial":
                    return stats.get("trial_users", 0)
                case _:
                    return 0
        except Exception:
            logger.exception("audience_count_error", audience=audience)
            return 0
