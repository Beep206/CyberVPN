"""Invite token service for registration access control (CRIT-1)."""

import hashlib
import json
import logging
from collections.abc import Awaitable
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

import redis.asyncio as redis

from src.config.settings import settings
from src.shared.logging import fingerprint_pii

logger = logging.getLogger(__name__)


class InviteTokenService:
    """Service for managing single-use invite tokens for registration.

    Tokens are stored in Redis with a configurable TTL (default 24h).
    Each token can only be used once and is deleted after consumption.
    """

    PREFIX = "invite_token:"
    REGISTRATION_RESERVATION_PREFIX = "invite_token_registration_reservation:"
    REGISTRATION_RESERVATION_TTL_SECONDS = 600
    _DELETE_RESERVATION_SCRIPT = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    end
    return 0
    """

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    @staticmethod
    def _token_fingerprint(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _token_key_digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def _registration_reservation_key(cls, token: str) -> str:
        return f"{cls.REGISTRATION_RESERVATION_PREFIX}{cls._token_key_digest(token)}"

    @classmethod
    def _legacy_registration_reservation_key(cls, token: str) -> str:
        return f"{cls.REGISTRATION_RESERVATION_PREFIX}{token}"

    @staticmethod
    def _decode_redis_text(value: object) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    async def _delete_registration_reservation_key(
        self,
        reservation_key: str,
        reservation_id: str,
    ) -> bool:
        deleted = await cast(
            Awaitable[Any],
            self._redis.eval(
                self._DELETE_RESERVATION_SCRIPT,
                1,
                reservation_key,
                reservation_id,
            ),
        )
        return bool(deleted)

    async def _find_owned_registration_reservation_key(
        self,
        token: str,
        reservation_id: str,
    ) -> str | None:
        for reservation_key in (
            self._registration_reservation_key(token),
            self._legacy_registration_reservation_key(token),
        ):
            existing_reservation = await self._redis.get(reservation_key)
            if existing_reservation and self._decode_redis_text(existing_reservation) == reservation_id:
                return reservation_key
        return None

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

        await self._redis.set(
            key,
            json.dumps(data),
            ex=int(self.ttl.total_seconds()),
        )

        logger.info(
            "Invite token generated",
            extra={
                "created_by": created_by,
                "role": role,
                "email_hint_present": email_hint is not None,
                "email_hint_fingerprint": fingerprint_pii(email_hint, namespace="invite_email_hint"),
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

    async def reserve_for_registration(
        self,
        token: str,
        reservation_id: str,
        *,
        ttl_seconds: int = REGISTRATION_RESERVATION_TTL_SECONDS,
    ) -> dict | None:
        """Reserve an invite token for a registration attempt without consuming it."""
        token_data = await self.validate(token)
        if not token_data:
            logger.warning(
                "Invalid or expired invite token reservation attempted",
                extra={"token_fingerprint": self._token_fingerprint(token)},
            )
            return None

        reservation_key = self._registration_reservation_key(token)
        reserved = await self._redis.set(
            reservation_key,
            reservation_id,
            ex=ttl_seconds,
            nx=True,
        )
        if reserved:
            logger.info(
                "Invite token reserved for registration",
                extra={"token_fingerprint": self._token_fingerprint(token)},
            )
            return token_data

        if await self._find_owned_registration_reservation_key(token, reservation_id):
            return token_data

        logger.warning(
            "Invite token registration reservation conflict",
            extra={"token_fingerprint": self._token_fingerprint(token)},
        )
        return None

    async def consume_reserved_for_registration(self, token: str, reservation_id: str) -> dict | None:
        """Consume an invite token only when the caller still owns its reservation."""
        reservation_key = await self._find_owned_registration_reservation_key(token, reservation_id)
        if not reservation_key:
            logger.warning(
                "Invite token consume blocked by missing registration reservation",
                extra={"token_fingerprint": self._token_fingerprint(token)},
            )
            return None

        token_data = await self.validate_and_consume(token)
        await self._delete_registration_reservation_key(reservation_key, reservation_id)
        return token_data

    async def release_registration_reservation(self, token: str, reservation_id: str) -> bool:
        """Release a registration reservation without consuming the invite token."""
        reservation_key = await self._find_owned_registration_reservation_key(token, reservation_id)
        released = False
        if reservation_key:
            released = await self._delete_registration_reservation_key(reservation_key, reservation_id)
        if released:
            logger.info(
                "Invite token registration reservation released",
                extra={"token_fingerprint": self._token_fingerprint(token)},
            )
        return released

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
                extra={"token_fingerprint": self._token_fingerprint(token)},
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
                extra={"token_fingerprint": self._token_fingerprint(token)},
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
