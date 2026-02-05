"""JWT token revocation service (HIGH-6).

Implements token revocation via Redis-based blocklist:
- Tokens include jti (JWT ID) claim for unique identification
- Revoked jti values stored in Redis with TTL matching token expiry
- Token validation checks revocation list
- Supports logout (single token), logout-all (all user tokens)
"""

import logging
import uuid
from datetime import UTC, datetime

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class JWTRevocationService:
    """Service for managing JWT token revocation.

    Uses Redis to track revoked token JTIs with appropriate TTL.
    """

    REVOKED_PREFIX = "jwt_revoked:"
    USER_TOKENS_PREFIX = "jwt_user_tokens:"
    MAX_TOKENS_PER_USER = 10  # Limit concurrent sessions

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    @staticmethod
    def generate_jti() -> str:
        """Generate a unique JWT ID (jti) claim.

        Returns:
            UUID4 string
        """
        return str(uuid.uuid4())

    async def register_token(
        self,
        jti: str,
        user_id: str,
        expires_at: datetime,
    ) -> None:
        """Register a newly created token.

        Tracks token for the user to support logout-all functionality.

        Args:
            jti: The JWT ID
            user_id: The user who owns this token
            expires_at: When the token expires
        """
        ttl_seconds = int((expires_at - datetime.now(UTC)).total_seconds())
        if ttl_seconds <= 0:
            return  # Token already expired

        user_tokens_key = f"{self.USER_TOKENS_PREFIX}{user_id}"

        # Store jti with expiry timestamp
        await self._redis.hset(user_tokens_key, jti, expires_at.isoformat())

        # Set key expiry to longest token TTL (extend if needed)
        current_ttl = await self._redis.ttl(user_tokens_key)
        if current_ttl < ttl_seconds:
            await self._redis.expire(user_tokens_key, ttl_seconds)

        # Prune old tokens (keep most recent)
        await self._prune_user_tokens(user_id)

        logger.debug(
            "Token registered",
            extra={"jti": jti[:8] + "...", "user_id": user_id},
        )

    async def _prune_user_tokens(self, user_id: str) -> None:
        """Remove expired tokens from user's token list."""
        user_tokens_key = f"{self.USER_TOKENS_PREFIX}{user_id}"
        tokens = await self._redis.hgetall(user_tokens_key)

        if not tokens:
            return

        now = datetime.now(UTC)
        expired_jtis = []

        for jti_bytes, expires_bytes in tokens.items():
            jti = jti_bytes.decode() if isinstance(jti_bytes, bytes) else jti_bytes
            expires_str = expires_bytes.decode() if isinstance(expires_bytes, bytes) else expires_bytes

            try:
                expires_at = datetime.fromisoformat(expires_str)
                if expires_at < now:
                    expired_jtis.append(jti)
            except ValueError:
                expired_jtis.append(jti)

        if expired_jtis:
            await self._redis.hdel(user_tokens_key, *expired_jtis)

    async def revoke_token(self, jti: str, expires_at: datetime) -> None:
        """Revoke a specific token by its JTI.

        Args:
            jti: The JWT ID to revoke
            expires_at: When the token would have expired (for TTL)
        """
        ttl_seconds = int((expires_at - datetime.now(UTC)).total_seconds())
        if ttl_seconds <= 0:
            return  # Token already expired, no need to revoke

        key = f"{self.REVOKED_PREFIX}{jti}"
        await self._redis.setex(key, ttl_seconds, "revoked")

        logger.info(
            "Token revoked",
            extra={"jti": jti[:8] + "...", "ttl_seconds": ttl_seconds},
        )

    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all tokens for a user (logout all devices).

        Args:
            user_id: The user whose tokens to revoke

        Returns:
            Number of tokens revoked
        """
        user_tokens_key = f"{self.USER_TOKENS_PREFIX}{user_id}"
        tokens = await self._redis.hgetall(user_tokens_key)

        if not tokens:
            return 0

        revoked_count = 0
        now = datetime.now(UTC)

        for jti_bytes, expires_bytes in tokens.items():
            jti = jti_bytes.decode() if isinstance(jti_bytes, bytes) else jti_bytes
            expires_str = expires_bytes.decode() if isinstance(expires_bytes, bytes) else expires_bytes

            try:
                expires_at = datetime.fromisoformat(expires_str)
                if expires_at > now:
                    await self.revoke_token(jti, expires_at)
                    revoked_count += 1
            except ValueError:
                continue

        # Clear user's token list
        await self._redis.delete(user_tokens_key)

        logger.info(
            "All user tokens revoked",
            extra={"user_id": user_id, "revoked_count": revoked_count},
        )

        return revoked_count

    async def is_revoked(self, jti: str) -> bool:
        """Check if a token is revoked.

        Args:
            jti: The JWT ID to check

        Returns:
            True if revoked, False otherwise
        """
        key = f"{self.REVOKED_PREFIX}{jti}"
        return await self._redis.exists(key) > 0

    async def get_user_active_sessions(self, user_id: str) -> int:
        """Get count of active (non-expired) sessions for a user.

        Args:
            user_id: The user ID

        Returns:
            Number of active sessions
        """
        user_tokens_key = f"{self.USER_TOKENS_PREFIX}{user_id}"
        tokens = await self._redis.hgetall(user_tokens_key)

        if not tokens:
            return 0

        now = datetime.now(UTC)
        active_count = 0

        for jti_bytes, expires_bytes in tokens.items():
            jti = jti_bytes.decode() if isinstance(jti_bytes, bytes) else jti_bytes
            expires_str = expires_bytes.decode() if isinstance(expires_bytes, bytes) else expires_bytes

            try:
                expires_at = datetime.fromisoformat(expires_str)
                if expires_at > now:
                    # Check if not revoked
                    if not await self.is_revoked(jti):
                        active_count += 1
            except ValueError:
                continue

        return active_count
