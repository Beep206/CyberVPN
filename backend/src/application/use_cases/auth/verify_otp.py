"""Verify OTP use case for email verification with auto-login."""

from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.otp_service import OtpService, OtpVerificationResult
from src.config.settings import settings
from src.infrastructure.database.models.refresh_token_model import RefreshToken
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository


class RemnawaveGateway(Protocol):
    """Protocol for Remnawave VPN backend integration."""

    async def create_user(
        self,
        username: str,
        email: str,
        telegram_id: int | None = None,
    ) -> dict:
        """Create user in Remnawave."""
        ...


class VerifyOtpResult:
    """Result of OTP verification."""

    def __init__(
        self,
        success: bool,
        *,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_type: str = "bearer",
        expires_in: int = 0,
        user_id: str | None = None,
        error_code: str | None = None,
        message: str | None = None,
        attempts_remaining: int = 0,
    ) -> None:
        self.success = success
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.user_id = user_id
        self.error_code = error_code
        self.message = message
        self.attempts_remaining = attempts_remaining


class VerifyOtpUseCase:
    """
    Handles OTP verification for email verification.

    Upon successful verification:
    1. Activates user account (is_active=True, is_email_verified=True)
    2. Creates user in Remnawave VPN backend
    3. Issues access and refresh tokens (auto-login)
    """

    def __init__(
        self,
        user_repo: AdminUserRepository,
        auth_service: AuthService,
        otp_service: OtpService,
        session: AsyncSession,
        remnawave_gateway: RemnawaveGateway | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._auth_service = auth_service
        self._otp_service = otp_service
        self._session = session
        self._remnawave_gateway = remnawave_gateway

    async def execute(self, email: str, code: str) -> VerifyOtpResult:
        """
        Verify OTP code and activate user.

        Args:
            email: User's email address
            code: 6-digit OTP code

        Returns:
            VerifyOtpResult with tokens on success, error details on failure
        """
        # Find user by email
        user = await self._user_repo.get_by_email(email)
        if not user:
            # Don't reveal if email exists
            return VerifyOtpResult(
                success=False,
                error_code="OTP_INVALID",
                message="Invalid verification code",
                attempts_remaining=0,
            )

        # Check if already verified
        if user.is_email_verified:
            return VerifyOtpResult(
                success=False,
                error_code="ALREADY_VERIFIED",
                message="Email already verified. Please login.",
                attempts_remaining=0,
            )

        # Validate OTP
        otp_result: OtpVerificationResult = await self._otp_service.validate_otp(
            user_id=user.id,
            code=code,
            purpose="email_verification",
        )

        if not otp_result.success:
            return VerifyOtpResult(
                success=False,
                error_code=otp_result.error_code,
                message=otp_result.message,
                attempts_remaining=otp_result.attempts_remaining,
            )

        # OTP valid - activate user
        user.is_active = True
        user.is_email_verified = True
        await self._session.flush()

        # Register in Remnawave (optional, don't fail if unavailable)
        if self._remnawave_gateway:
            try:
                await self._remnawave_gateway.create_user(
                    username=user.login,
                    email=user.email or email,
                    telegram_id=user.telegram_id,
                )
            except Exception:
                # Log but don't fail - user can still use dashboard
                pass

        # Create tokens (auto-login)
        # MED-003: Properly unpack token tuple (token, jti, expires_at)
        access_token, _access_jti, _access_expire = self._auth_service.create_access_token(
            subject=str(user.id),
            role=user.role,
        )
        refresh_token, _refresh_jti, refresh_expire = self._auth_service.create_refresh_token(subject=str(user.id))

        # Store refresh token hash in database
        token_hash = sha256(refresh_token.encode()).hexdigest()
        expires_at = refresh_expire  # Use actual expiry from token creation

        refresh_token_record = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(refresh_token_record)

        # Update last login information
        user.last_login_at = datetime.now(UTC)
        await self._session.flush()

        return VerifyOtpResult(
            success=True,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user_id=str(user.id),
        )
