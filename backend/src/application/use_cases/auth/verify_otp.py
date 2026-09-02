"""Verify OTP use case for email verification with auto-login."""

import logging
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.auth_session_issuer import AuthSessionIssuer, AuthSessionIssueRequest
from src.application.services.otp_service import OtpService, OtpVerificationResult
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository

logger = logging.getLogger(__name__)


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
    2. Issues access and refresh tokens (auto-login)

    VPN provisioning is intentionally owned by canonical MobileUser
    subscription/trial flows that atomically persist the identity ledger.
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
        self._session_issuer = AuthSessionIssuer(auth_service=auth_service, session=session)

    async def execute(
        self,
        email: str,
        code: str,
        client_fingerprint: str | None = None,
        client_device_key: str | None = None,
        client_ip: str | None = None,
        client_ip_source: str | None = None,
        proxy_peer: str | None = None,
        user_agent: str | None = None,
        auth_realm_id: UUID | None = None,
        auth_realm_key: str | None = None,
        audience: str | None = None,
        principal_type: str = "admin",
        scope_family: str = "admin",
        include_legacy_default: bool = False,
    ) -> VerifyOtpResult:
        """
        Verify OTP code and activate user.

        Args:
            email: User's email address
            code: 6-digit OTP code

        Returns:
            VerifyOtpResult with tokens on success, error details on failure
        """
        # Find user by email
        user = await self._user_repo.get_by_email(
            email,
            realm_id=auth_realm_id,
            include_legacy_default=include_legacy_default,
        )
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

        issued_session = await self._session_issuer.issue_auth_session(
            AuthSessionIssueRequest(
                user_id=user.id,
                role=user.role,
                device_key=client_device_key,
                refresh_fingerprint=client_fingerprint,
                ip_address=client_ip,
                ip_source=client_ip_source,
                proxy_peer=proxy_peer,
                user_agent=user_agent,
                auth_realm_id=auth_realm_id,
                auth_realm_key=auth_realm_key,
                audience=audience,
                principal_class=principal_type,
                principal_subject=str(user.id),
                scope_family=scope_family,
                platform="web",
            )
        )

        # Update last login information
        user.last_login_at = datetime.now(UTC)
        await self._session.flush()

        return VerifyOtpResult(
            success=True,
            access_token=issued_session.access_token,
            refresh_token=issued_session.refresh_token,
            token_type=issued_session.token_type,
            expires_in=issued_session.expires_in,
            user_id=str(user.id),
        )
