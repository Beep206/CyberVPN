"""Magic link service for passwordless authentication.

Generates and validates single-use magic link tokens with rate limiting.
Also generates a 6-digit OTP code that can be used as an alternative to clicking the link.
"""

import json
import logging
import random
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
    - Time-limited (1-hour TTL)
    - Rate-limited (max 5 requests per hour per email)

    Each magic link also has a companion 6-digit OTP code that the user
    can enter instead of clicking the link.
    """

    PREFIX = "magic_link:"
    CONSUMED_PREFIX = "magic_link_consumed:"
    CONSUMED_REPLAY_PREFIX = "magic_link_consumed_replay:"
    EMAIL_TOKEN_PREFIX = "magic_link_email:"  # Reverse lookup: email -> token
    OTP_PREFIX = "magic_link_otp:"  # Reverse lookup: email -> 6-digit OTP code
    RATE_LIMIT_PREFIX = "magic_link_rate:"
    TTL_SECONDS = 3600  # 1 hour
    CONSUMED_TTL_SECONDS = 120  # Allow one replay to tolerate duplicate requests
    MAX_REQUESTS_PER_HOUR = 5
    RATE_LIMIT_WINDOW = 3600  # 1 hour

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def generate(
        self,
        email: str,
        ip_address: str | None = None,
    ) -> tuple[str, str]:
        """Generate a new magic link token and companion OTP code.

        Args:
            email: Email address to associate with the token.
            ip_address: Optional IP address of the requester.

        Returns:
            A tuple of (token, otp_code) where token is the magic link
            URL token and otp_code is the 6-digit numeric code.

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

        # Reuse existing token and OTP code if still valid (so old emails keep working)
        email_key = f"{self.EMAIL_TOKEN_PREFIX}{email}"
        otp_key = f"{self.OTP_PREFIX}{email}"
        existing_token = await self._redis.get(email_key)
        if existing_token:
            existing_token = existing_token.decode() if isinstance(existing_token, bytes) else existing_token
            # Verify the token data still exists in Redis
            token_key = f"{self.PREFIX}{existing_token}"
            if await self._redis.exists(token_key):
                # Also retrieve the existing OTP code
                existing_otp = await self._redis.get(otp_key)
                if existing_otp:
                    existing_otp = existing_otp.decode() if isinstance(existing_otp, bytes) else existing_otp
                    logger.debug(
                        "Reusing existing magic link token and OTP code",
                        extra={"email": email, "token_prefix": existing_token[:8]},
                    )
                    return existing_token, existing_otp

        # Generate new token: 48 bytes -> 64 URL-safe characters, 288 bits entropy
        token = secrets.token_urlsafe(48)
        # Generate 6-digit OTP code
        otp_code = str(random.randint(100000, 999999))  # noqa: S311
        key = f"{self.PREFIX}{token}"
        data = {
            "email": email,
            "ip_address": ip_address,
            "created_at": datetime.now(UTC).isoformat(),
        }

        # Store token data, reverse lookups (email -> token, email -> otp) with same TTL
        pipe = self._redis.pipeline()
        pipe.setex(key, self.TTL_SECONDS, json.dumps(data))
        pipe.setex(email_key, self.TTL_SECONDS, token)
        pipe.setex(otp_key, self.TTL_SECONDS, otp_code)
        await pipe.execute()

        logger.debug(
            "Magic link token and OTP code generated",
            extra={"email": email, "token_prefix": token[:8]},
        )

        return token, otp_code

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
        consumed_key = f"{self.CONSUMED_PREFIX}{token}"
        replay_key = f"{self.CONSUMED_REPLAY_PREFIX}{token}"

        # Atomic get+delete using pipeline
        pipe = self._redis.pipeline()
        pipe.get(key)
        pipe.delete(key)
        results = await pipe.execute()

        data = results[0]
        if not data:
            consumed_payload = await self._redis.get(consumed_key)
            payload = self._deserialize_payload(consumed_payload)
            if payload:
                replay_granted = await self._redis.set(
                    replay_key,
                    "1",
                    ex=self.CONSUMED_TTL_SECONDS,
                    nx=True,
                )
                if replay_granted:
                    logger.info(
                        "Magic link token replay accepted",
                        extra={
                            "email": payload.get("email"),
                            "token_prefix": token[:8] if len(token) >= 8 else token,
                        },
                    )
                    return payload

            logger.warning(
                "Invalid or expired magic link token used",
                extra={
                    "token_prefix": token[:8] if len(token) >= 8 else token,
                },
            )
            return None

        payload = self._deserialize_payload(data)
        if not payload:
            logger.warning(
                "Magic link token payload is malformed",
                extra={
                    "token_prefix": token[:8] if len(token) >= 8 else token,
                },
            )
            return None

        # Clean up reverse lookups (email -> token and email -> otp)
        email = payload.get("email")
        if email:
            email_key = f"{self.EMAIL_TOKEN_PREFIX}{email}"
            otp_key = f"{self.OTP_PREFIX}{email}"
            pipe = self._redis.pipeline()
            pipe.delete(email_key)
            pipe.delete(otp_key)
            pipe.setex(consumed_key, self.CONSUMED_TTL_SECONDS, json.dumps(payload))
            pipe.delete(replay_key)
            await pipe.execute()
        else:
            # Keep a short replay window even for malformed/missing email payloads.
            await self._redis.setex(consumed_key, self.CONSUMED_TTL_SECONDS, json.dumps(payload))
            await self._redis.delete(replay_key)

        logger.info(
            "Magic link token validated and consumed",
            extra={
                "email": email,
                "token_prefix": token[:8],
            },
        )

        return payload

    @staticmethod
    def _deserialize_payload(data: str | bytes | None) -> dict | None:
        """Deserialize token payload from Redis.

        Supports both the current JSON object format and legacy plain email
        string values to avoid hard failures during rolling updates.
        """
        if data is None:
            return None

        decoded = data.decode() if isinstance(data, bytes) else data

        try:
            payload = json.loads(decoded)
        except json.JSONDecodeError:
            if isinstance(decoded, str) and "@" in decoded:
                return {
                    "email": decoded,
                    "ip_address": None,
                    "created_at": None,
                }
            return None

        if isinstance(payload, dict):
            return payload

        if isinstance(payload, str) and "@" in payload:
            return {
                "email": payload,
                "ip_address": None,
                "created_at": None,
            }

        return None

    async def validate_otp(self, email: str, code: str) -> dict | None:
        """Validate a 6-digit OTP code for magic link authentication.

        Looks up the OTP code stored for the given email. If it matches,
        retrieves the associated token and delegates to validate_and_consume()
        to atomically consume the magic link.

        Args:
            email: The email address the OTP was sent to.
            code: The 6-digit OTP code entered by the user.

        Returns:
            The payload dict (email, ip_address, created_at) if the OTP
            is valid, or None if the code doesn't match or has expired.
        """
        otp_key = f"{self.OTP_PREFIX}{email}"
        stored_otp = await self._redis.get(otp_key)

        if not stored_otp:
            logger.warning(
                "Magic link OTP lookup failed: no OTP found",
                extra={"email": email},
            )
            return None

        stored_otp = stored_otp.decode() if isinstance(stored_otp, bytes) else stored_otp

        if stored_otp != code:
            logger.warning(
                "Magic link OTP code mismatch",
                extra={"email": email},
            )
            return None

        # OTP matches -- get the token from the email->token reverse lookup
        email_key = f"{self.EMAIL_TOKEN_PREFIX}{email}"
        token = await self._redis.get(email_key)

        if not token:
            logger.warning(
                "Magic link OTP valid but token not found",
                extra={"email": email},
            )
            return None

        token = token.decode() if isinstance(token, bytes) else token

        # Delegate to validate_and_consume which handles atomic consumption
        # and cleanup of all related keys (token data, email->token, email->otp)
        return await self.validate_and_consume(token)
