"""OTP Service for generating, validating, and managing verification codes."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.config.settings import settings
from src.infrastructure.database.models.otp_code_model import OtpCodeModel
from src.infrastructure.database.repositories.otp_code_repo import OtpCodeRepository


class OtpServiceError(Exception):
    """Base exception for OTP service errors."""

    pass


class OtpExpiredError(OtpServiceError):
    """OTP code has expired."""

    pass


class OtpExhaustedError(OtpServiceError):
    """Maximum OTP verification attempts reached."""

    pass


class OtpInvalidError(OtpServiceError):
    """OTP code is invalid."""

    pass


class OtpRateLimitError(OtpServiceError):
    """Rate limit exceeded for OTP operations."""

    def __init__(self, message: str, next_available_at: datetime | None = None) -> None:
        super().__init__(message)
        self.next_available_at = next_available_at


class OtpVerificationResult:
    """Result of OTP verification attempt."""

    def __init__(
        self,
        success: bool,
        *,
        attempts_remaining: int = 0,
        error_code: str | None = None,
        message: str | None = None,
    ) -> None:
        self.success = success
        self.attempts_remaining = attempts_remaining
        self.error_code = error_code
        self.message = message


class OtpService:
    """
    Service for OTP (One-Time Password) operations.

    Handles:
    - OTP generation with cryptographically secure randomness
    - OTP validation with attempt tracking
    - OTP invalidation
    - Rate limiting for generation/resend
    """

    # Configuration defaults (can be overridden via settings)
    DEFAULT_EXPIRATION_HOURS = 3
    DEFAULT_MAX_ATTEMPTS = 5
    DEFAULT_MAX_RESENDS = 3
    DEFAULT_RESEND_WINDOW_HOURS = 1
    DEFAULT_RESEND_COOLDOWN_SECONDS = 30

    def __init__(self, otp_repo: OtpCodeRepository) -> None:
        self._otp_repo = otp_repo

        # Load configuration from settings with defaults
        self._expiration_hours = getattr(settings, "otp_expiration_hours", self.DEFAULT_EXPIRATION_HOURS)
        self._max_attempts = getattr(settings, "otp_max_attempts", self.DEFAULT_MAX_ATTEMPTS)
        self._max_resends = getattr(settings, "otp_max_resends", self.DEFAULT_MAX_RESENDS)
        self._resend_window_hours = getattr(settings, "otp_resend_window_hours", self.DEFAULT_RESEND_WINDOW_HOURS)
        self._resend_cooldown_seconds = getattr(
            settings, "otp_resend_cooldown_seconds", self.DEFAULT_RESEND_COOLDOWN_SECONDS
        )

    @staticmethod
    def _generate_code() -> str:
        """Generate a cryptographically secure 6-digit OTP code."""
        # secrets.randbelow is cryptographically secure
        return f"{secrets.randbelow(1_000_000):06d}"

    async def generate_otp(
        self,
        user_id: UUID,
        purpose: str = "email_verification",
        is_resend: bool = False,
    ) -> OtpCodeModel:
        """
        Generate a new OTP code for a user.

        Args:
            user_id: The user's UUID
            purpose: OTP purpose (email_verification, password_reset, login_2fa)
            is_resend: Whether this is a resend request

        Returns:
            The created OtpCodeModel

        Raises:
            OtpRateLimitError: If rate limit exceeded
        """
        now = datetime.now(UTC)

        # Check rate limits for resend
        if is_resend:
            # Get existing active OTP to check resend count
            existing = await self._otp_repo.get_active_by_user_id(user_id, purpose)

            if existing:
                # Check resend cooldown
                if existing.last_resend_at:
                    cooldown_expires = existing.last_resend_at + timedelta(seconds=self._resend_cooldown_seconds)
                    if now < cooldown_expires:
                        raise OtpRateLimitError(
                            f"Please wait {self._resend_cooldown_seconds} seconds before requesting a new code",
                            next_available_at=cooldown_expires,
                        )

                # Check resend count
                if not existing.can_resend:
                    window_end = existing.created_at + timedelta(hours=self._resend_window_hours)
                    raise OtpRateLimitError(
                        f"Maximum {self._max_resends} resends reached. Please wait.",
                        next_available_at=window_end,
                    )

                # Increment resend count on existing OTP
                existing.resend_count += 1
                existing.last_resend_at = now
                await self._otp_repo.update(existing)

        # Invalidate any existing active codes for this user/purpose
        await self._otp_repo.invalidate_all_for_user(user_id, purpose)

        # Generate new code
        code = self._generate_code()
        expires_at = now + timedelta(hours=self._expiration_hours)

        otp = OtpCodeModel(
            user_id=user_id,
            code=code,
            purpose=purpose,
            max_attempts=self._max_attempts,
            max_resends=self._max_resends,
            resend_count=1 if is_resend else 0,
            last_resend_at=now if is_resend else None,
            expires_at=expires_at,
        )

        return await self._otp_repo.create(otp)

    async def validate_otp(
        self,
        user_id: UUID,
        code: str,
        purpose: str = "email_verification",
    ) -> OtpVerificationResult:
        """
        Validate an OTP code for a user.

        Args:
            user_id: The user's UUID
            code: The 6-digit OTP code to validate
            purpose: OTP purpose

        Returns:
            OtpVerificationResult with success status and details
        """
        # Find the OTP record
        otp = await self._otp_repo.get_by_user_id_and_code(user_id, code, purpose)

        if not otp:
            # Try to find any active OTP to update attempt count
            active_otp = await self._otp_repo.get_active_by_user_id(user_id, purpose)
            if active_otp:
                active_otp.attempts_used += 1
                await self._otp_repo.update(active_otp)

                if active_otp.is_exhausted:
                    return OtpVerificationResult(
                        success=False,
                        attempts_remaining=0,
                        error_code="OTP_EXHAUSTED",
                        message="Too many attempts. Please request a new code.",
                    )

                return OtpVerificationResult(
                    success=False,
                    attempts_remaining=active_otp.attempts_remaining,
                    error_code="OTP_INVALID",
                    message="Invalid verification code",
                )

            return OtpVerificationResult(
                success=False,
                attempts_remaining=0,
                error_code="OTP_NOT_FOUND",
                message="No active verification code found. Please request a new one.",
            )

        # Check if exhausted
        if otp.is_exhausted:
            return OtpVerificationResult(
                success=False,
                attempts_remaining=0,
                error_code="OTP_EXHAUSTED",
                message="Too many attempts. Please request a new code.",
            )

        # Check if expired
        if otp.is_expired:
            return OtpVerificationResult(
                success=False,
                attempts_remaining=otp.attempts_remaining,
                error_code="OTP_EXPIRED",
                message="Verification code expired. Please request a new one.",
            )

        # Code matches - mark as verified
        otp.verified_at = datetime.now(UTC)
        await self._otp_repo.update(otp)

        return OtpVerificationResult(
            success=True,
            attempts_remaining=otp.attempts_remaining,
        )

    async def invalidate_otp(
        self,
        user_id: UUID,
        purpose: str = "email_verification",
    ) -> int:
        """
        Invalidate all active OTP codes for a user.

        Used when user successfully verifies or requests account deletion.

        Args:
            user_id: The user's UUID
            purpose: OTP purpose

        Returns:
            Number of codes invalidated
        """
        return await self._otp_repo.invalidate_all_for_user(user_id, purpose)

    async def get_active_otp(
        self,
        user_id: UUID,
        purpose: str = "email_verification",
    ) -> OtpCodeModel | None:
        """
        Get the active OTP code for a user.

        Args:
            user_id: The user's UUID
            purpose: OTP purpose

        Returns:
            Active OtpCodeModel or None
        """
        return await self._otp_repo.get_active_by_user_id(user_id, purpose)

    async def can_resend(
        self,
        user_id: UUID,
        purpose: str = "email_verification",
    ) -> tuple[bool, int | None, datetime | None]:
        """
        Check if user can request OTP resend.

        Args:
            user_id: The user's UUID
            purpose: OTP purpose

        Returns:
            Tuple of (can_resend, resends_remaining, next_available_at)
        """
        otp = await self._otp_repo.get_active_by_user_id(user_id, purpose)

        if not otp:
            # No active OTP, can generate new one
            return True, self._max_resends, None

        if not otp.can_resend:
            # Max resends reached
            window_end = otp.created_at + timedelta(hours=self._resend_window_hours)
            return False, 0, window_end

        # Check cooldown
        if otp.last_resend_at:
            cooldown_expires = otp.last_resend_at + timedelta(seconds=self._resend_cooldown_seconds)
            now = datetime.now(UTC)
            if now < cooldown_expires:
                return False, otp.resends_remaining, cooldown_expires

        return True, otp.resends_remaining, None

    async def resend_existing_otp(
        self,
        user_id: UUID,
        purpose: str = "email_verification",
    ) -> OtpCodeModel | None:
        """
        Resend the existing OTP code without generating a new one.

        This keeps the same code across all resend attempts so users
        don't get confused when multiple emails arrive with different codes.

        Args:
            user_id: The user's UUID
            purpose: OTP purpose

        Returns:
            The existing OtpCodeModel with updated resend count, or None if no active OTP

        Raises:
            OtpRateLimitError: If rate limit exceeded
        """
        now = datetime.now(UTC)

        # Get existing active OTP
        existing = await self._otp_repo.get_active_by_user_id(user_id, purpose)

        if not existing:
            # No active OTP - caller should generate a new one
            return None

        # Check if expired
        if existing.is_expired:
            # Expired OTP - caller should generate a new one
            return None

        # Check resend cooldown
        if existing.last_resend_at:
            cooldown_expires = existing.last_resend_at + timedelta(seconds=self._resend_cooldown_seconds)
            if now < cooldown_expires:
                raise OtpRateLimitError(
                    f"Please wait {self._resend_cooldown_seconds} seconds before requesting a new code",
                    next_available_at=cooldown_expires,
                )

        # Check resend count
        if not existing.can_resend:
            window_end = existing.created_at + timedelta(hours=self._resend_window_hours)
            raise OtpRateLimitError(
                f"Maximum {self._max_resends} resends reached. Please wait.",
                next_available_at=window_end,
            )

        # Increment resend count and update timestamp
        existing.resend_count += 1
        existing.last_resend_at = now
        await self._otp_repo.update(existing)

        return existing
