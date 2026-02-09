"""Reset password use case - validates OTP and updates password."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.otp_service import OtpService
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository

logger = logging.getLogger(__name__)


class ResetPasswordResult:
    """Result of password reset attempt."""

    def __init__(
        self,
        success: bool,
        *,
        error_code: str | None = None,
        message: str | None = None,
        attempts_remaining: int = 0,
    ) -> None:
        self.success = success
        self.error_code = error_code
        self.message = message
        self.attempts_remaining = attempts_remaining


class ResetPasswordUseCase:
    """Validate password reset OTP and set new password."""

    def __init__(
        self,
        user_repo: AdminUserRepository,
        auth_service: AuthService,
        otp_service: OtpService,
        session: AsyncSession,
    ) -> None:
        self._user_repo = user_repo
        self._auth_service = auth_service
        self._otp_service = otp_service
        self._session = session

    async def execute(self, email: str, code: str, new_password: str) -> ResetPasswordResult:
        """Validate OTP code and reset user's password.

        Args:
            email: User's email address
            code: 6-digit OTP code
            new_password: New password (already validated by schema)
        """
        user = await self._user_repo.get_by_email(email.lower())
        if not user:
            return ResetPasswordResult(
                success=False,
                error_code="OTP_INVALID",
                message="Invalid verification code",
            )

        # Validate OTP
        otp_result = await self._otp_service.validate_otp(
            user_id=user.id,
            code=code,
            purpose="password_reset",
        )

        if not otp_result.success:
            return ResetPasswordResult(
                success=False,
                error_code=otp_result.error_code,
                message=otp_result.message,
                attempts_remaining=otp_result.attempts_remaining,
            )

        # OTP valid - update password
        user.password_hash = await self._auth_service.hash_password(new_password)
        await self._session.flush()

        logger.info("Password reset successful", extra={"user_id": str(user.id)})

        return ResetPasswordResult(success=True)
