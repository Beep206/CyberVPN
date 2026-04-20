"""Login use case for admin user authentication."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.domain.exceptions import InvalidCredentialsError
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.presentation.api.v1.auth.session_tokens import store_refresh_token


class LoginUseCase:
    """
    Handles admin user login with username/email and password.

    Returns access and refresh tokens upon successful authentication, or a
    short-lived pending-2FA token when TOTP is enabled for the user.
    Stores refresh token hash in database for rotation and revocation.
    """

    def __init__(
        self,
        user_repo: AdminUserRepository,
        auth_service: AuthService,
        session: AsyncSession,
    ) -> None:
        self._user_repo = user_repo
        self._auth_service = auth_service
        self._session = session

    async def execute(
        self,
        login_or_email: str,
        password: str,
        client_fingerprint: str | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
        auth_realm_id: UUID | None = None,
        auth_realm_key: str | None = None,
        audience: str | None = None,
        principal_type: str = "admin",
        scope_family: str = "admin",
        include_legacy_default: bool = False,
    ) -> dict:
        """
        Authenticate user and generate token pair.

        Args:
            login_or_email: Username or email address
            password: Plain text password
            client_fingerprint: Client device fingerprint for token binding (MED-002)

        Returns:
            Dictionary containing:
            - access_token: JWT access token
            - refresh_token: JWT refresh token
            - token_type: "bearer"
            - expires_in: Access token expiration in seconds
            - requires_2fa: Whether the login is paused behind TOTP
            - tfa_token: Short-lived pending-2FA token when required

        Raises:
            InvalidCredentialsError: If credentials are invalid or user not found
        """
        # Find user by login or email
        user = await self._user_repo.get_by_login_or_email(
            login_or_email,
            realm_id=auth_realm_id,
            include_legacy_default=include_legacy_default,
        )
        if not user:
            raise InvalidCredentialsError()

        # Verify user is active and email is verified
        if not user.is_active or not user.is_email_verified:
            raise InvalidCredentialsError()

        # Verify password
        if not user.password_hash:
            raise InvalidCredentialsError()

        if not self._auth_service.verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            await self._session.flush()
            raise InvalidCredentialsError()

        is_first_username_only_login = user.email is None and user.sign_in_count == 0

        # Update last login information before issuing either the full session
        # or a short-lived pending 2FA token.
        user.last_login_at = user.current_sign_in_at
        user.last_login_ip = user.current_sign_in_ip
        user.current_sign_in_at = datetime.now(UTC)
        user.current_sign_in_ip = client_ip
        user.sign_in_count += 1
        user.failed_login_attempts = 0
        await self._session.flush()

        if user.totp_enabled:
            tfa_token, _, _ = self._auth_service.create_access_token(
                subject=str(user.id),
                role="2fa_pending",
                extra={"type": "2fa_pending"},
                audience=audience,
                principal_type=principal_type,
                realm_id=str(auth_realm_id) if auth_realm_id else None,
                realm_key=auth_realm_key,
                scope_family=scope_family,
            )
            return {
                "access_token": "",
                "refresh_token": "",
                "token_type": "bearer",
                "expires_in": 0,
                "requires_2fa": True,
                "tfa_token": tfa_token,
                "is_first_username_only_login": is_first_username_only_login,
            }

        # Create access and refresh tokens
        # MED-003: Properly unpack token tuple (token, jti, expires_at)
        access_token, access_jti, _access_expire = self._auth_service.create_access_token(
            subject=str(user.id),
            role=user.role,
            audience=audience,
            principal_type=principal_type,
            realm_id=str(auth_realm_id) if auth_realm_id else None,
            realm_key=auth_realm_key,
            scope_family=scope_family,
        )
        # MED-002: Include client fingerprint in refresh token for device binding
        refresh_token, _refresh_jti, refresh_expire = self._auth_service.create_refresh_token(
            subject=str(user.id),
            fingerprint=client_fingerprint,
            audience=audience,
            principal_type=principal_type,
            realm_id=str(auth_realm_id) if auth_realm_id else None,
            realm_key=auth_realm_key,
            scope_family=scope_family,
        )
        await store_refresh_token(
            self._session,
            user_id=user.id,
            refresh_token=refresh_token,
            expires_at=refresh_expire,
            device_id=client_fingerprint,
            ip_address=client_ip,
            user_agent=user_agent,
            auth_realm_id=auth_realm_id,
            principal_class=principal_type,
            principal_subject=str(user.id),
            audience=audience,
            scope_family=scope_family,
            access_token_jti=access_jti,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "requires_2fa": False,
            "tfa_token": None,
            "is_first_username_only_login": is_first_username_only_login,
            "auth_realm_id": str(auth_realm_id) if auth_realm_id else None,
            "auth_realm_key": auth_realm_key,
            "audience": audience,
        }
