"""Magic link service for passwordless authentication.

Generates and validates single-use magic link tokens with rate limiting.
"""

import json
import logging
import secrets
from datetime import UTC, datetime

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RateLimitExceededError(Exception):
    """Raised when a user exceeds the magic link request rate limit."""

    def __init__(self, email: str, retry_after_seconds: int | None = None) -> None:
        self.email = email
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded for magic link requests: {email}")


class MagicLinkService:
    """Service for managing passwordless magic link tokens.

    Magic link tokens are:
    - Cryptographically random (288 bits / 64 URL-safe characters)
    - Single-use (deleted on validation)
    - Time-limited (15-minute TTL)
    - Rate-limited (max 5 requests per hour per email)
    """

    PREFIX = "magic_link:"
    RATE_LIMIT_PREFIX = "magic_link_rate:"
    TTL_SECONDS = 900  # 15 minutes
    MAX_REQUESTS_PER_HOUR = 5
    RATE_LIMIT_WINDOW = 3600  # 1 hour

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def generate(
        self,
        email: str,
        ip_address: str | None = None,
    ) -> str:
        """Generate a new magic link token.

        Args:
            email: Email address to associate with the token.
            ip_address: Optional IP address of the requester.

        Returns:
            The generated magic link token.

        Raises:
            RateLimitExceededError: If the email has exceeded the hourly
                request limit.
        """
        rate_key = f"{self.RATE_LIMIT_PREFIX}{email}"

        # Check and increment rate limit counter
        pipe = self._redis.pipeline()
        pipe.incr(rate_key)
        pipe.ttl(rate_key)
        results = await pipe.execute()

        count = results[0]
        current_ttl = results[1]

        # Set TTL on first request (when count transitions from 0 to 1)
        if count == 1:
            await self._redis.expire(rate_key, self.RATE_LIMIT_WINDOW)

        if count > self.MAX_REQUESTS_PER_HOUR:
            retry_after = current_ttl if current_ttl > 0 else self.RATE_LIMIT_WINDOW
            logger.warning(
                "Magic link rate limit exceeded",
                extra={"email": email, "count": count, "retry_after": retry_after},
            )
            raise RateLimitExceededError(email, retry_after_seconds=retry_after)

        # Generate token: 48 bytes -> 64 URL-safe characters, 288 bits entropy
        token = secrets.token_urlsafe(48)
        key = f"{self.PREFIX}{token}"
        data = {
            "email": email,
            "ip_address": ip_address,
            "created_at": datetime.now(UTC).isoformat(),
        }

        await self._redis.setex(key, self.TTL_SECONDS, json.dumps(data))

        logger.debug(
            "Magic link token generated",
            extra={"email": email, "token_prefix": token[:8]},
        )

        return token

    async def validate_and_consume(self, token: str) -> dict | None:
        """Validate and consume a magic link token.

        The token is atomically retrieved and deleted so it cannot be
        reused.

        Args:
            token: The magic link token to validate.

        Returns:
            The payload dict (email, ip_address, created_at) if the token
            is valid, or None if the token is invalid or expired.
        """
        key = f"{self.PREFIX}{token}"

        # Atomic get+delete using pipeline
        pipe = self._redis.pipeline()
        pipe.get(key)
        pipe.delete(key)
        results = await pipe.execute()

        data = results[0]
        if not data:
            logger.warning(
                "Invalid or expired magic link token used",
                extra={
                    "token_prefix": token[:8] if len(token) >= 8 else token,
                },
            )
            return None

        payload = json.loads(data)

        logger.info(
            "Magic link token validated and consumed",
            extra={
                "email": payload.get("email"),
                "token_prefix": token[:8],
            },
        )

        return payload
