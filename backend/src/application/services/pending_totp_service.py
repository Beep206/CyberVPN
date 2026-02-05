"""Pending TOTP service for delayed secret storage (CRIT-3).

Stores TOTP secrets temporarily until verification, implementing the secure flow:
1. Generate secret -> store in Redis (not DB)
2. User scans QR code
3. User submits TOTP code
4. If valid -> persist to DB
5. If invalid/expired -> secret discarded

This prevents storing potentially unused/unverified secrets in the database.
"""

import json
import logging
from datetime import UTC, datetime

import redis.asyncio as redis

from src.infrastructure.totp.totp_service import TOTPService

logger = logging.getLogger(__name__)


class PendingTOTPService:
    """Service for managing pending (unverified) TOTP secrets.

    Secrets are stored in Redis with a short TTL and only persisted to the
    database after successful verification.
    """

    PREFIX = "pending_totp:"
    TTL_MINUTES = 10  # Pending secrets expire after 10 minutes

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client
        self._totp = TOTPService()

    async def generate_pending_secret(
        self,
        user_id: str,
        account_name: str,
    ) -> dict:
        """Generate a new TOTP secret and store as pending.

        Args:
            user_id: The user ID
            account_name: Account name for the TOTP URI (email or username)

        Returns:
            Dict with secret and qr_uri
        """
        secret = self._totp.generate_secret()
        uri = self._totp.generate_qr_uri(secret, account_name)

        key = f"{self.PREFIX}{user_id}"
        data = {
            "secret": secret,
            "account_name": account_name,
            "created_at": datetime.now(UTC).isoformat(),
        }

        ttl_seconds = self.TTL_MINUTES * 60
        await self._redis.setex(key, ttl_seconds, json.dumps(data))

        logger.info(
            "Pending TOTP secret generated",
            extra={"user_id": user_id, "ttl_minutes": self.TTL_MINUTES},
        )

        return {"secret": secret, "qr_uri": uri}

    async def get_pending_secret(self, user_id: str) -> str | None:
        """Get the pending TOTP secret for a user.

        Args:
            user_id: The user ID

        Returns:
            The pending secret if exists, None otherwise
        """
        key = f"{self.PREFIX}{user_id}"
        data = await self._redis.get(key)

        if not data:
            return None

        return json.loads(data).get("secret")

    async def verify_and_consume(self, user_id: str, code: str) -> str | None:
        """Verify TOTP code against pending secret and consume if valid.

        Args:
            user_id: The user ID
            code: The TOTP code to verify

        Returns:
            The secret if verification successful, None otherwise
        """
        key = f"{self.PREFIX}{user_id}"
        data = await self._redis.get(key)

        if not data:
            logger.warning(
                "No pending TOTP secret found",
                extra={"user_id": user_id},
            )
            return None

        secret = json.loads(data).get("secret")

        if not self._totp.verify_code(secret, code):
            logger.warning(
                "Invalid TOTP code for pending secret",
                extra={"user_id": user_id},
            )
            return None

        # Verification successful - delete pending secret
        await self._redis.delete(key)

        logger.info(
            "Pending TOTP secret verified and consumed",
            extra={"user_id": user_id},
        )

        return secret

    async def discard(self, user_id: str) -> None:
        """Discard a pending TOTP secret.

        Args:
            user_id: The user ID
        """
        key = f"{self.PREFIX}{user_id}"
        await self._redis.delete(key)
