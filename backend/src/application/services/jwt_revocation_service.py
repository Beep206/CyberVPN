"""JWT token revocation service (HIGH-6).

Implements token revocation via Redis-based blocklist:
- Tokens include jti (JWT ID) claim for unique identification
- Revoked jti values stored in Redis with TTL matching token expiry
- Token validation checks revocation list
- Supports logout (single token), logout-all (all user tokens)
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis

from src.shared.async_compat import resolve_maybe_awaitable

logger = logging.getLogger(__name__)


class JWTRevocationService:
    """Service for managing JWT token revocation.

    Uses Redis to track revoked token JTIs with appropriate TTL.
    """

    REVOKED_PREFIX = "jwt_revoked:"
    USER_TOKENS_PREFIX = "jwt_user_tokens:"
    PRINCIPAL_TOKENS_PREFIX = "jwt_principal_tokens:"
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
        *,
        auth_realm_id: str | None = None,
        principal_class: str | None = None,
        principal_subject: str | None = None,
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
        metadata = self._encode_token_metadata(
            expires_at=expires_at,
            auth_realm_id=auth_realm_id,
            principal_class=principal_class,
            principal_subject=principal_subject,
        )

        # Store jti with expiry timestamp
        await resolve_maybe_awaitable(self._redis.hset(user_tokens_key, jti, metadata))
        await self._extend_key_expiry(user_tokens_key, ttl_seconds)

        principal_key = self._principal_tokens_key(
            auth_realm_id=auth_realm_id,
            principal_class=principal_class,
            principal_subject=principal_subject,
        )
        if principal_key is not None:
            await resolve_maybe_awaitable(self._redis.hset(principal_key, jti, metadata))
            await self._extend_key_expiry(principal_key, ttl_seconds)

        # Prune old tokens (keep most recent)
        await self._prune_user_tokens(user_id)

        logger.debug(
            "Token registered",
            extra={"jti": jti[:8] + "...", "user_id": user_id},
        )

    async def _extend_key_expiry(self, key: str, ttl_seconds: int) -> None:
        current_ttl = int(await resolve_maybe_awaitable(self._redis.ttl(key)))
        if current_ttl < ttl_seconds:
            await resolve_maybe_awaitable(self._redis.expire(key, ttl_seconds))

    @classmethod
    def _principal_tokens_key(
        cls,
        *,
        auth_realm_id: str | None,
        principal_class: str | None,
        principal_subject: str | None,
    ) -> str | None:
        if not auth_realm_id or not principal_class or not principal_subject:
            return None
        return f"{cls.PRINCIPAL_TOKENS_PREFIX}{auth_realm_id}:{principal_class}:{principal_subject}"

    @staticmethod
    def _encode_token_metadata(
        *,
        expires_at: datetime,
        auth_realm_id: str | None,
        principal_class: str | None,
        principal_subject: str | None,
    ) -> str:
        if not auth_realm_id or not principal_class or not principal_subject:
            return expires_at.isoformat()
        return json.dumps(
            {
                "expires_at": expires_at.isoformat(),
                "auth_realm_id": auth_realm_id,
                "principal_class": principal_class,
                "principal_subject": principal_subject,
            },
            separators=(",", ":"),
        )

    @staticmethod
    def _decode_token_metadata(raw_value: Any) -> tuple[datetime, str | None, str | None, str | None] | None:
        value = raw_value.decode() if isinstance(raw_value, bytes) else str(raw_value)
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            try:
                return (datetime.fromisoformat(value), None, None, None)
            except ValueError:
                return None
        if not isinstance(decoded, dict):
            return None
        expires_raw = decoded.get("expires_at")
        if not isinstance(expires_raw, str):
            return None
        try:
            expires_at = datetime.fromisoformat(expires_raw)
        except ValueError:
            return None
        auth_realm_id = decoded.get("auth_realm_id")
        principal_class = decoded.get("principal_class")
        principal_subject = decoded.get("principal_subject")
        return (
            expires_at,
            auth_realm_id if isinstance(auth_realm_id, str) else None,
            principal_class if isinstance(principal_class, str) else None,
            principal_subject if isinstance(principal_subject, str) else None,
        )

    async def _prune_user_tokens(self, user_id: str) -> None:
        """Remove expired tokens and enforce MAX_TOKENS_PER_USER limit.

        SEC-010: Implements FIFO eviction when user exceeds session limit.
        """
        user_tokens_key = f"{self.USER_TOKENS_PREFIX}{user_id}"
        tokens = await resolve_maybe_awaitable(self._redis.hgetall(user_tokens_key))

        if not tokens:
            return

        now = datetime.now(UTC)
        expired_jtis = []
        active_tokens: list[tuple[str, datetime]] = []

        for jti_bytes, metadata_bytes in tokens.items():
            jti = jti_bytes.decode() if isinstance(jti_bytes, bytes) else jti_bytes
            metadata = self._decode_token_metadata(metadata_bytes)
            if metadata is None:
                expired_jtis.append(jti)
                continue
            expires_at = metadata[0]
            if expires_at < now:
                expired_jtis.append(jti)
            else:
                active_tokens.append((jti, expires_at))

        # Remove expired tokens
        if expired_jtis:
            await resolve_maybe_awaitable(self._redis.hdel(user_tokens_key, *expired_jtis))

        # SEC-010: Enforce MAX_TOKENS_PER_USER with FIFO eviction
        if len(active_tokens) > self.MAX_TOKENS_PER_USER:
            # Sort by expiry (oldest first) and revoke excess
            active_tokens.sort(key=lambda x: x[1])
            tokens_to_revoke = len(active_tokens) - self.MAX_TOKENS_PER_USER

            for i in range(tokens_to_revoke):
                jti, expires_at = active_tokens[i]
                await self.revoke_token(jti, expires_at)
                await resolve_maybe_awaitable(self._redis.hdel(user_tokens_key, jti))

            logger.info(
                "Enforced session limit - revoked oldest tokens",
                extra={
                    "user_id": user_id,
                    "revoked_count": tokens_to_revoke,
                    "max_tokens": self.MAX_TOKENS_PER_USER,
                },
            )

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
        await resolve_maybe_awaitable(self._redis.set(key, "revoked", ex=ttl_seconds))

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
        tokens = await resolve_maybe_awaitable(self._redis.hgetall(user_tokens_key))

        if not tokens:
            return 0

        revoked_count = 0
        now = datetime.now(UTC)

        for jti_bytes, metadata_bytes in tokens.items():
            jti = jti_bytes.decode() if isinstance(jti_bytes, bytes) else jti_bytes
            metadata = self._decode_token_metadata(metadata_bytes)
            if metadata is None:
                continue
            expires_at = metadata[0]
            if expires_at > now:
                await self.revoke_token(jti, expires_at)
                revoked_count += 1

        # Clear user's token list
        await resolve_maybe_awaitable(self._redis.delete(user_tokens_key))

        logger.info(
            "All user tokens revoked",
            extra={"user_id": user_id, "revoked_count": revoked_count},
        )

        return revoked_count

    async def revoke_principal_tokens(
        self,
        *,
        user_id: str,
        auth_realm_id: str,
        principal_class: str,
        principal_subject: str,
        revoke_unscoped_legacy: bool = False,
    ) -> int:
        """Revoke indexed JWTs for one auth realm/principal boundary.

        The legacy user-wide key may contain scoped JSON metadata written by
        newer issuers or unscoped ISO timestamps from older issuers/tests. New
        callers should not revoke unscoped legacy entries unless they are in a
        compatibility path where user-wide revocation is explicitly intended.
        """
        revoked_count = 0
        scoped_key = self._principal_tokens_key(
            auth_realm_id=auth_realm_id,
            principal_class=principal_class,
            principal_subject=principal_subject,
        )
        if scoped_key is not None:
            revoked_count += await self._revoke_token_hash_entries(scoped_key, delete_key=True)

        legacy_key = f"{self.USER_TOKENS_PREFIX}{user_id}"
        legacy_tokens = await resolve_maybe_awaitable(self._redis.hgetall(legacy_key))
        if not legacy_tokens:
            return revoked_count

        matched_legacy_jtis: list[str] = []
        now = datetime.now(UTC)
        for jti_bytes, metadata_bytes in legacy_tokens.items():
            jti = jti_bytes.decode() if isinstance(jti_bytes, bytes) else jti_bytes
            metadata = self._decode_token_metadata(metadata_bytes)
            if metadata is None:
                matched_legacy_jtis.append(jti)
                continue
            expires_at, token_realm_id, token_principal_class, token_principal_subject = metadata
            scoped_match = (
                token_realm_id == auth_realm_id
                and token_principal_class == principal_class
                and token_principal_subject == principal_subject
            )
            legacy_match = (
                token_realm_id is None
                and token_principal_class is None
                and token_principal_subject is None
                and revoke_unscoped_legacy
            )
            if not scoped_match and not legacy_match:
                continue
            matched_legacy_jtis.append(jti)
            if expires_at > now and not await self.is_revoked(jti):
                await self.revoke_token(jti, expires_at)
                revoked_count += 1

        if matched_legacy_jtis:
            await resolve_maybe_awaitable(self._redis.hdel(legacy_key, *matched_legacy_jtis))

        return revoked_count

    async def _revoke_token_hash_entries(self, key: str, *, delete_key: bool = False) -> int:
        tokens = await resolve_maybe_awaitable(self._redis.hgetall(key))
        if not tokens:
            return 0

        revoked_count = 0
        now = datetime.now(UTC)
        expired_or_invalid_jtis: list[str] = []
        for jti_bytes, metadata_bytes in tokens.items():
            jti = jti_bytes.decode() if isinstance(jti_bytes, bytes) else jti_bytes
            metadata = self._decode_token_metadata(metadata_bytes)
            if metadata is None:
                expired_or_invalid_jtis.append(jti)
                continue
            expires_at = metadata[0]
            if expires_at > now:
                await self.revoke_token(jti, expires_at)
                revoked_count += 1
            else:
                expired_or_invalid_jtis.append(jti)

        if delete_key:
            await resolve_maybe_awaitable(self._redis.delete(key))
        elif expired_or_invalid_jtis:
            await resolve_maybe_awaitable(self._redis.hdel(key, *expired_or_invalid_jtis))

        return revoked_count

    async def is_revoked(self, jti: str) -> bool:
        """Check if a token is revoked.

        Args:
            jti: The JWT ID to check

        Returns:
            True if revoked, False otherwise
        """
        key = f"{self.REVOKED_PREFIX}{jti}"
        return int(await resolve_maybe_awaitable(self._redis.exists(key))) > 0

    async def get_user_active_sessions(self, user_id: str) -> int:
        """Get count of active (non-expired) sessions for a user.

        Args:
            user_id: The user ID

        Returns:
            Number of active sessions
        """
        user_tokens_key = f"{self.USER_TOKENS_PREFIX}{user_id}"
        tokens = await resolve_maybe_awaitable(self._redis.hgetall(user_tokens_key))

        if not tokens:
            return 0

        now = datetime.now(UTC)
        active_count = 0

        for jti_bytes, metadata_bytes in tokens.items():
            jti = jti_bytes.decode() if isinstance(jti_bytes, bytes) else jti_bytes
            metadata = self._decode_token_metadata(metadata_bytes)
            if metadata is None:
                continue
            expires_at = metadata[0]
            if expires_at > now:
                # Check if not revoked
                if not await self.is_revoked(jti):
                    active_count += 1

        return active_count
