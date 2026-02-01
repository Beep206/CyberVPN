"""Login use case for admin user authentication."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.domain.exceptions import InvalidCredentialsError
from src.infrastructure.database.models.refresh_token_model import RefreshToken
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository


class LoginUseCase:
    """
    Handles admin user login with username/email and password.

    Returns access and refresh tokens upon successful authentication.
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

    async def execute(self, login_or_email: str, password: str) -> dict:
        """
        Authenticate user and generate token pair.

        Args:
            login_or_email: Username or email address
            password: Plain text password

        Returns:
            Dictionary containing:
            - access_token: JWT access token
            - refresh_token: JWT refresh token
            - token_type: "bearer"
            - expires_in: Access token expiration in seconds

        Raises:
            InvalidCredentialsError: If credentials are invalid or user not found
        """
        # Find user by login or email
        user = await self._user_repo.get_by_login_or_email(login_or_email)
        if not user:
            raise InvalidCredentialsError()

        # Verify user is active
        if not user.is_active:
            raise InvalidCredentialsError()

        # Verify password
        if not user.password_hash:
            raise InvalidCredentialsError()

        if not await self._auth_service.verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        # Create access and refresh tokens
        access_token = self._auth_service.create_access_token(
            subject=str(user.id),
            role=user.role,
        )
        refresh_token = self._auth_service.create_refresh_token(subject=str(user.id))

        # Store refresh token hash in database
        token_hash = sha256(refresh_token.encode()).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

        refresh_token_record = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(refresh_token_record)
        await self._session.flush()

        # Update last login information
        user.last_login_at = datetime.now(UTC)
        await self._session.flush()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }
