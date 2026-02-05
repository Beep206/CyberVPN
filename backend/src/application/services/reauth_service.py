"""Re-authentication service for sensitive operations (CRIT-3).

Provides password re-authentication for security-sensitive operations like:
- 2FA setup/disable
- Password change
- Account deletion
"""

import json
import logging
from datetime import UTC, datetime, timedelta

import redis.asyncio as redis

from src.application.services.auth_service import AuthService

logger = logging.getLogger(__name__)


class ReauthService:
    """Service for managing password re-authentication for sensitive operations.

    Re-authentication is required for operations that could compromise account security.
    After successful password verification, a short-lived token is stored allowing
    the user to perform sensitive operations within the grace period.
    """

    PREFIX = "reauth:"
    DEFAULT_GRACE_PERIOD_MINUTES = 5

    def __init__(
        self,
        redis_client: redis.Redis,
        auth_service: AuthService,
        grace_period_minutes: int = DEFAULT_GRACE_PERIOD_MINUTES,
    ) -> None:
        self._redis = redis_client
        self._auth = auth_service
        self._grace_period = timedelta(minutes=grace_period_minutes)

    async def verify_password(
        self,
        user_id: str,
        password: str,
        password_hash: str,
    ) -> bool:
        """Verify password and create re-auth token if valid.

        Args:
            user_id: The user ID
            password: The plaintext password to verify
            password_hash: The stored password hash

        Returns:
            True if password is valid, False otherwise
        """
        if not self._auth.verify_password(password, password_hash):
            logger.warning(
                "Re-authentication failed - invalid password",
                extra={"user_id": user_id},
            )
            return False

        # Store re-auth token
        key = f"{self.PREFIX}{user_id}"
        data = {
            "verified_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + self._grace_period).isoformat(),
        }
        await self._redis.setex(
            key,
            int(self._grace_period.total_seconds()),
            json.dumps(data),
        )

        logger.info(
            "Re-authentication successful",
            extra={"user_id": user_id, "grace_period_minutes": self._grace_period.total_seconds() / 60},
        )

        return True

    async def is_recently_authenticated(self, user_id: str) -> bool:
        """Check if user has recently re-authenticated.

        Args:
            user_id: The user ID

        Returns:
            True if user has a valid re-auth token, False otherwise
        """
        key = f"{self.PREFIX}{user_id}"
        data = await self._redis.get(key)
        return data is not None

    async def require_reauth(self, user_id: str) -> None:
        """Check if re-authentication is required.

        Args:
            user_id: The user ID

        Raises:
            ReauthenticationRequired: If user has not recently re-authenticated
        """
        if not await self.is_recently_authenticated(user_id):
            raise ReauthenticationRequired(
                "Password re-authentication required for this operation."
            )

    async def invalidate(self, user_id: str) -> None:
        """Invalidate re-authentication token.

        Use after completing sensitive operations.

        Args:
            user_id: The user ID
        """
        key = f"{self.PREFIX}{user_id}"
        await self._redis.delete(key)


class ReauthenticationRequired(Exception):
    """Raised when an operation requires password re-authentication."""

    pass
