"""OAuth state service for CSRF protection (CRIT-2/HIGH-5).

Manages single-use state tokens for OAuth flows to prevent CSRF attacks.
"""

import json
import logging
import secrets
from datetime import UTC, datetime

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class OAuthStateService:
    """Service for managing OAuth state tokens (CSRF protection).

    State tokens are:
    - Cryptographically random
    - Single-use (deleted on validation)
    - Time-limited (10-minute TTL)
    - Tied to user session or IP
    """

    PREFIX = "oauth_state:"
    TTL_SECONDS = 600  # 10 minutes

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def generate(
        self,
        provider: str,
        user_id: str | None = None,
        ip_address: str | None = None,
    ) -> str:
        """Generate a new OAuth state token.

        Args:
            provider: OAuth provider name (e.g., 'telegram', 'github')
            user_id: Optional user ID to bind the state to (for linking flows)
            ip_address: Optional IP address to bind the state to

        Returns:
            The generated state token
        """
        state = secrets.token_urlsafe(32)
        key = f"{self.PREFIX}{state}"
        data = {
            "provider": provider,
            "user_id": user_id,
            "ip_address": ip_address,
            "created_at": datetime.now(UTC).isoformat(),
        }

        await self._redis.setex(key, self.TTL_SECONDS, json.dumps(data))

        logger.debug(
            "OAuth state generated",
            extra={"provider": provider, "state_prefix": state[:8]},
        )

        return state

    async def validate_and_consume(
        self,
        state: str,
        provider: str,
        user_id: str | None = None,
        ip_address: str | None = None,
    ) -> bool:
        """Validate and consume an OAuth state token.

        Args:
            state: The state token to validate
            provider: Expected provider name
            user_id: Expected user ID (if applicable)
            ip_address: Expected IP address (if applicable)

        Returns:
            True if valid, False otherwise
        """
        key = f"{self.PREFIX}{state}"

        # Get and delete atomically using pipeline
        pipe = self._redis.pipeline()
        pipe.get(key)
        pipe.delete(key)
        results = await pipe.execute()

        data = results[0]
        if not data:
            logger.warning(
                "Invalid or expired OAuth state used",
                extra={"state_prefix": state[:8] if len(state) >= 8 else state},
            )
            return False

        state_data = json.loads(data)

        # Validate provider matches
        if state_data.get("provider") != provider:
            logger.warning(
                "OAuth state provider mismatch",
                extra={
                    "expected": provider,
                    "actual": state_data.get("provider"),
                },
            )
            return False

        # Validate user_id if provided at generation
        if state_data.get("user_id") and user_id and state_data["user_id"] != user_id:
            logger.warning(
                "OAuth state user_id mismatch",
                extra={
                    "expected": state_data.get("user_id"),
                    "actual": user_id,
                },
            )
            return False

        # Note: IP validation is optional - NAT and mobile networks can change IPs
        # Only log warning if different, don't fail
        if state_data.get("ip_address") and ip_address and state_data["ip_address"] != ip_address:
            logger.warning(
                "OAuth state IP address changed during flow",
                extra={
                    "original_ip": state_data.get("ip_address"),
                    "callback_ip": ip_address,
                },
            )

        logger.info(
            "OAuth state validated and consumed",
            extra={"provider": provider, "state_prefix": state[:8]},
        )

        return True
