"""Invite token service for registration access control (CRIT-1)."""

import json
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import redis.asyncio as redis

from src.config.settings import settings

logger = logging.getLogger(__name__)


class InviteTokenService:
    """Service for managing single-use invite tokens for registration.

    Tokens are stored in Redis with a configurable TTL (default 24h).
    Each token can only be used once and is deleted after consumption.
    """

    PREFIX = "invite_token:"

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    @property
    def ttl(self) -> timedelta:
        return timedelta(hours=settings.invite_token_expiry_hours)

    async def generate(
        self,
        created_by: str,
        role: str = "VIEWER",
        email_hint: str | None = None,
    ) -> str:
        """Generate a new invite token.

        Args:
            created_by: User ID of the admin creating the invite
            role: Role to assign to the registered user (default: VIEWER)
            email_hint: Optional email to restrict the invite to

        Returns:
            The generated invite token (UUID)
        """
        token = str(uuid4())
        key = f"{self.PREFIX}{token}"
        data = {
            "created_by": created_by,
            "role": role,
            "email_hint": email_hint,
            "created_at": datetime.now(UTC).isoformat(),
        }

        await self._redis.setex(
            key,
            int(self.ttl.total_seconds()),
            json.dumps(data),
        )

        logger.info(
            "Invite token generated",
            extra={
                "created_by": created_by,
                "role": role,
                "email_hint": email_hint,
                "expires_in_hours": settings.invite_token_expiry_hours,
            },
        )

        return token

    async def validate(self, token: str) -> dict | None:
        """Validate an invite token without consuming it.

        Args:
            token: The invite token to validate

        Returns:
            Token data if valid, None if invalid/expired
        """
        key = f"{self.PREFIX}{token}"
        data = await self._redis.get(key)

        if not data:
            return None

        return json.loads(data)

    async def validate_and_consume(self, token: str) -> dict | None:
        """Validate and consume an invite token (single-use).

        Args:
            token: The invite token to validate and consume

        Returns:
            Token data if valid, None if invalid/expired/already used
        """
        key = f"{self.PREFIX}{token}"

        # Use GET + DELETE in a transaction for atomicity
        pipe = self._redis.pipeline()
        pipe.get(key)
        pipe.delete(key)
        results = await pipe.execute()

        data = results[0]
        if not data:
            logger.warning(
                "Invalid or expired invite token used",
                extra={"token_prefix": token[:8] if len(token) >= 8 else token},
            )
            return None

        token_data = json.loads(data)
        logger.info(
            "Invite token consumed",
            extra={
                "created_by": token_data.get("created_by"),
                "role": token_data.get("role"),
            },
        )

        return token_data

    async def revoke(self, token: str) -> bool:
        """Revoke an invite token.

        Args:
            token: The invite token to revoke

        Returns:
            True if token was found and deleted, False otherwise
        """
        key = f"{self.PREFIX}{token}"
        deleted = await self._redis.delete(key)

        if deleted:
            logger.info(
                "Invite token revoked",
                extra={"token_prefix": token[:8] if len(token) >= 8 else token},
            )

        return bool(deleted)

    async def list_active(self) -> list[dict]:
        """List all active (non-expired) invite tokens.

        Returns:
            List of token data with remaining TTL
        """
        pattern = f"{self.PREFIX}*"
        tokens = []

        async for key in self._redis.scan_iter(match=pattern):
            token = key.replace(self.PREFIX, "")
            ttl = await self._redis.ttl(key)
            data = await self._redis.get(key)

            if data:
                token_data = json.loads(data)
                token_data["token"] = token
                token_data["ttl_seconds"] = ttl
                tokens.append(token_data)

        return tokens
