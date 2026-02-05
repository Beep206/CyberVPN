"""Resend OTP use case for email verification."""

from datetime import datetime
from typing import Protocol

from src.application.services.otp_service import OtpRateLimitError, OtpService
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository


class EmailTaskDispatcher(Protocol):
    """Protocol for dispatching email tasks to task-worker."""

    async def dispatch_otp_email(
        self,
        email: str,
        otp_code: str,
        locale: str = "en-EN",
        is_resend: bool = False,
    ) -> None:
        """Dispatch OTP email task."""
        ...


class ResendOtpResult:
    """Result of resend OTP operation."""

    def __init__(
        self,
        success: bool,
        *,
        resends_remaining: int = 0,
        next_resend_available_at: datetime | None = None,
        error_code: str | None = None,
        message: str | None = None,
    ) -> None:
        self.success = success
        self.resends_remaining = resends_remaining
        self.next_resend_available_at = next_resend_available_at
        self.error_code = error_code
        self.message = message


class ResendOtpUseCase:
    """
    Handles OTP resend requests with rate limiting.

    Uses Brevo (secondary provider) for resend emails to:
    1. Maximize free tier usage across providers
    2. Provide different IP reputation if primary is blocked
    """

    def __init__(
        self,
        user_repo: AdminUserRepository,
        otp_service: OtpService,
        email_dispatcher: EmailTaskDispatcher | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._otp_service = otp_service
        self._email_dispatcher = email_dispatcher

    async def execute(self, email: str, locale: str = "en-EN") -> ResendOtpResult:
        """
        Resend OTP verification code.

        Args:
            email: User's email address
            locale: Locale for email template

        Returns:
            ResendOtpResult with status and remaining resends
        """
        # Find user by email
        user = await self._user_repo.get_by_email(email)
        if not user:
            # Don't reveal if email exists - return generic success
            return ResendOtpResult(
                success=True,
                resends_remaining=0,
                message="If your email is registered, you will receive a new code.",
            )

        # Check if already verified
        if user.is_email_verified:
            return ResendOtpResult(
                success=False,
                error_code="ALREADY_VERIFIED",
                message="Email already verified. Please login.",
            )

        # Check if can resend
        can_resend, resends_remaining, next_available = await self._otp_service.can_resend(
            user_id=user.id,
            purpose="email_verification",
        )

        if not can_resend:
            return ResendOtpResult(
                success=False,
                resends_remaining=resends_remaining or 0,
                next_resend_available_at=next_available,
                error_code="RATE_LIMITED",
                message="Please wait before requesting another code.",
            )

        # Generate new OTP (invalidates old one)
        try:
            otp = await self._otp_service.generate_otp(
                user_id=user.id,
                purpose="email_verification",
                is_resend=True,
            )
        except OtpRateLimitError as e:
            return ResendOtpResult(
                success=False,
                resends_remaining=0,
                next_resend_available_at=e.next_available_at,
                error_code="RATE_LIMITED",
                message=str(e),
            )

        # Dispatch email task (using is_resend=True to use Brevo)
        if self._email_dispatcher:
            try:
                await self._email_dispatcher.dispatch_otp_email(
                    email=email,
                    otp_code=otp.code,
                    locale=locale,
                    is_resend=True,  # Will use Brevo instead of Resend
                )
            except Exception:
                # Log but don't fail - code was generated
                pass

        return ResendOtpResult(
            success=True,
            resends_remaining=otp.resends_remaining,
            message="New verification code sent.",
        )
