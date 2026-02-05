"""Login brute force protection service (HIGH-1).

Implements progressive lockout to prevent credential stuffing and brute force attacks:
- 5 failed attempts: 30-second lockout
- 10 failed attempts: 5-minute lockout
- 15 failed attempts: 30-minute lockout
- 20+ failed attempts: account locked (requires admin unlock)
"""

import logging
from dataclasses import dataclass
from datetime import timedelta

import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LockoutThreshold:
    """Lockout threshold configuration."""

    attempts: int
    duration: timedelta | None  # None = permanent lock


class LockoutPolicy:
    """Progressive lockout policy."""

    THRESHOLDS: list[LockoutThreshold] = [
        LockoutThreshold(5, timedelta(seconds=30)),
        LockoutThreshold(10, timedelta(minutes=5)),
        LockoutThreshold(15, timedelta(minutes=30)),
        LockoutThreshold(20, None),  # Permanent - requires admin unlock
    ]

    @classmethod
    def get_lockout_duration(cls, attempts: int) -> timedelta | None:
        """Get lockout duration for given number of attempts.

        Args:
            attempts: Number of failed login attempts

        Returns:
            Lockout duration, None for permanent lock, or timedelta(0) for no lockout
        """
        for threshold in reversed(cls.THRESHOLDS):
            if attempts >= threshold.attempts:
                return threshold.duration
        return timedelta(0)  # No lockout


class LoginProtectionService:
    """Service for managing login brute force protection.

    Uses Redis to track failed login attempts and implement progressive lockout.
    """

    ATTEMPTS_PREFIX = "login_attempts:"
    LOCKOUT_PREFIX = "lockout:"
    ATTEMPT_WINDOW_SECONDS = 3600  # 1 hour window for counting attempts

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def record_failed_attempt(self, identifier: str) -> int:
        """Record a failed login attempt.

        Args:
            identifier: The account identifier (email or username)

        Returns:
            Total number of failed attempts
        """
        key = f"{self.ATTEMPTS_PREFIX}{identifier}"

        attempts = await self._redis.incr(key)
        await self._redis.expire(key, self.ATTEMPT_WINDOW_SECONDS)

        # Check if lockout should be applied
        lockout_duration = LockoutPolicy.get_lockout_duration(attempts)

        if lockout_duration is None:
            # Permanent lock
            lockout_key = f"{self.LOCKOUT_PREFIX}{identifier}"
            await self._redis.set(lockout_key, "permanent")
            logger.warning(
                "Account permanently locked due to excessive failed attempts",
                extra={"identifier": identifier, "attempts": attempts},
            )
        elif lockout_duration.total_seconds() > 0:
            # Temporary lockout
            lockout_key = f"{self.LOCKOUT_PREFIX}{identifier}"
            await self._redis.setex(
                lockout_key,
                int(lockout_duration.total_seconds()),
                str(attempts),
            )
            logger.warning(
                "Account locked due to failed attempts",
                extra={
                    "identifier": identifier,
                    "attempts": attempts,
                    "lockout_seconds": lockout_duration.total_seconds(),
                },
            )

        return attempts

    async def get_attempts(self, identifier: str) -> int:
        """Get number of failed login attempts.

        Args:
            identifier: The account identifier

        Returns:
            Number of failed attempts
        """
        key = f"{self.ATTEMPTS_PREFIX}{identifier}"
        attempts = await self._redis.get(key)
        return int(attempts) if attempts else 0

    async def is_locked(self, identifier: str) -> bool:
        """Check if an account is currently locked.

        Args:
            identifier: The account identifier

        Returns:
            True if locked, False otherwise
        """
        key = f"{self.LOCKOUT_PREFIX}{identifier}"
        return await self._redis.exists(key) > 0

    async def get_lockout_remaining(self, identifier: str) -> int | None:
        """Get remaining lockout time in seconds.

        Args:
            identifier: The account identifier

        Returns:
            Seconds remaining, -1 for permanent lock, None if not locked
        """
        key = f"{self.LOCKOUT_PREFIX}{identifier}"
        value = await self._redis.get(key)

        if not value:
            return None

        if value == "permanent":
            return -1  # Permanent lock

        ttl = await self._redis.ttl(key)
        return max(0, ttl)

    async def reset_on_success(self, identifier: str) -> None:
        """Reset failed attempts on successful login.

        Args:
            identifier: The account identifier
        """
        attempts_key = f"{self.ATTEMPTS_PREFIX}{identifier}"
        lockout_key = f"{self.LOCKOUT_PREFIX}{identifier}"

        # Only reset if not permanently locked
        lockout_value = await self._redis.get(lockout_key)
        if lockout_value == "permanent":
            logger.info(
                "Successful login on permanently locked account - keeping lock",
                extra={"identifier": identifier},
            )
            return

        await self._redis.delete(attempts_key, lockout_key)

        logger.debug(
            "Login attempts reset on successful login",
            extra={"identifier": identifier},
        )

    async def admin_unlock(self, identifier: str) -> bool:
        """Admin action to unlock a locked account.

        Args:
            identifier: The account identifier

        Returns:
            True if account was unlocked, False if wasn't locked
        """
        attempts_key = f"{self.ATTEMPTS_PREFIX}{identifier}"
        lockout_key = f"{self.LOCKOUT_PREFIX}{identifier}"

        deleted = await self._redis.delete(attempts_key, lockout_key)

        if deleted:
            logger.info(
                "Account unlocked by admin",
                extra={"identifier": identifier},
            )
            return True

        return False

    async def check_and_raise_if_locked(self, identifier: str) -> None:
        """Check if account is locked and raise exception if so.

        Args:
            identifier: The account identifier

        Raises:
            AccountLockedException: If account is locked
        """
        if not await self.is_locked(identifier):
            return

        remaining = await self.get_lockout_remaining(identifier)

        if remaining == -1:
            raise AccountLockedException(
                identifier=identifier,
                permanent=True,
                message="Account is locked. Contact support for assistance.",
            )

        raise AccountLockedException(
            identifier=identifier,
            permanent=False,
            remaining_seconds=remaining,
            message=f"Too many failed login attempts. Try again in {remaining} seconds.",
        )


class AccountLockedException(Exception):
    """Raised when attempting to login to a locked account."""

    def __init__(
        self,
        identifier: str,
        permanent: bool = False,
        remaining_seconds: int | None = None,
        message: str = "Account is locked.",
    ) -> None:
        self.identifier = identifier
        self.permanent = permanent
        self.remaining_seconds = remaining_seconds
        super().__init__(message)
