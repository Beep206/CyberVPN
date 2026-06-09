"""Login use case for admin user authentication."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.auth_session_issuer import AuthSessionIssuer, AuthSessionIssueRequest
from src.domain.exceptions import InvalidCredentialsError
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository


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
        self._session_issuer = AuthSessionIssuer(auth_service=auth_service, session=session)

    async def execute(
        self,
        login_or_email: str,
        password: str,
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

        return {
            **issued_session.as_token_dict(),
            "requires_2fa": False,
            "tfa_token": None,
            "is_first_username_only_login": is_first_username_only_login,
        }
