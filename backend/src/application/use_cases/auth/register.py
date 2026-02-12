"""
Registration use case for creating new admin users with email verification.
"""

import logging
from typing import Protocol

from src.application.services.auth_service import AuthService

logger = logging.getLogger(__name__)
from src.application.services.otp_service import OtpService
from src.domain.enums import AdminRole
from src.domain.exceptions import DuplicateUsernameError
from src.infrastructure.database.models.admin_user_model import AdminUserModel
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


class RegisterResult:
    """Result of registration operation."""

    def __init__(self, user: AdminUserModel, otp_sent: bool = True) -> None:
        self.user = user
        self.otp_sent = otp_sent


class RegisterUseCase:
    """
    Handles admin user registration with email verification.

    Creates new admin user with hashed password after validating
    login and email uniqueness. User is created as inactive until
    email is verified via OTP.
    """

    def __init__(
        self,
        user_repo: AdminUserRepository,
        auth_service: AuthService,
        otp_service: OtpService,
        email_dispatcher: EmailTaskDispatcher | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._auth_service = auth_service
        self._otp_service = otp_service
        self._email_dispatcher = email_dispatcher

    async def execute(
        self,
        login: str,
        password: str,
        email: str | None = None,
        role: AdminRole = AdminRole.VIEWER,
        locale: str = "en-EN",
    ) -> RegisterResult:
        """
        Register new admin user, optionally with email verification.

        Supports two flows:
        - With email: user created as inactive, OTP sent for verification.
        - Without email (username-only): user created as immediately active.

        Args:
            login: Unique username
            password: Plain text password (will be hashed)
            email: Optional unique email address
            role: User role (default: "viewer")
            locale: User's locale for email template

        Returns:
            RegisterResult with created user and OTP status

        Raises:
            DuplicateUsernameError: If login or email already exists
        """
        # Check login uniqueness
        existing_user = await self._user_repo.get_by_login(login)
        if existing_user:
            raise DuplicateUsernameError(username=login)

        # Check email uniqueness (only if email provided)
        if email:
            existing_user = await self._user_repo.get_by_email(email)
            if existing_user:
                raise DuplicateUsernameError(username=email)

        # Hash password
        password_hash = await self._auth_service.hash_password(password)

        # Create user — active immediately if no email, inactive if email (needs OTP verification)
        user = AdminUserModel(
            login=login,
            email=email,
            password_hash=password_hash,
            role=role.value,
            is_active=email is None,  # Active immediately for username-only registration
            is_email_verified=False,
        )

        # Persist to database
        created_user = await self._user_repo.create(user)

        # Generate OTP and dispatch email only when email is provided
        otp_sent = False
        if email and self._email_dispatcher:
            otp = await self._otp_service.generate_otp(
                user_id=created_user.id,
                purpose="email_verification",
            )
            try:
                await self._email_dispatcher.dispatch_otp_email(
                    email=email,
                    otp_code=otp.code,
                    locale=locale,
                    is_resend=False,
                )
                otp_sent = True
            except Exception as e:  # noqa: S110
                # Log but don't fail registration
                # User can request resend
                logger.warning("Failed to dispatch OTP email during registration: %s", e)

        return RegisterResult(user=created_user, otp_sent=otp_sent)
