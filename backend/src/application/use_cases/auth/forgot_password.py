"""Forgot password use case - generates OTP for password reset."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.otp_service import OtpService
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.tasks.email_task_dispatcher import EmailTaskDispatcher

logger = logging.getLogger(__name__)


class ForgotPasswordUseCase:
    """Generate and send password reset OTP code.

    Always returns success to prevent email enumeration.
    """

    def __init__(
        self,
        user_repo: AdminUserRepository,
        otp_service: OtpService,
        email_dispatcher: EmailTaskDispatcher,
        session: AsyncSession,
    ) -> None:
        self._user_repo = user_repo
        self._otp_service = otp_service
        self._email_dispatcher = email_dispatcher
        self._session = session

    async def execute(self, email: str) -> None:
        """Generate password reset OTP and dispatch email.

        Silently succeeds even if email not found (prevent enumeration).
        """
        user = await self._user_repo.get_by_email(email.lower())
        if not user:
            # Silent success to prevent email enumeration
            logger.info(
                "Password reset requested for unknown email",
                extra={"email_domain": email.split("@")[-1]},
            )
            return

        if not user.is_active:
            # Don't send reset to inactive accounts
            return

        # Generate OTP with password_reset purpose
        otp = await self._otp_service.generate_otp(
            user_id=user.id,
            purpose="password_reset",
        )
        await self._session.flush()

        # Dispatch password reset email
        try:
            await self._email_dispatcher.dispatch_password_reset_email(
                email=user.email or email,
                otp_code=otp.code,
            )
        except Exception as e:
            logger.exception("Failed to dispatch password reset email: %s", e)
