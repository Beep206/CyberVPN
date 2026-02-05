"""Refresh token use case for JWT token rotation.

Includes device fingerprint validation (MED-002) when ENFORCE_TOKEN_BINDING is enabled.
"""

import logging
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.domain.exceptions import InvalidCredentialsError
from src.infrastructure.database.models.refresh_token_model import RefreshToken
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository

logger = logging.getLogger("cybervpn")


class RefreshTokenUseCase:
    """
    Handles JWT refresh token rotation.

    Validates existing refresh token, revokes it, and issues a new token pair.
    Implements token rotation pattern for enhanced security.
    """

    def __init__(
        self,
        auth_service: AuthService,
        session: AsyncSession,
    ) -> None:
        self._auth_service = auth_service
        self._session = session

    async def execute(
        self,
        refresh_token: str,
        client_fingerprint: str | None = None,
    ) -> dict:
        """
        Rotate refresh token and generate new token pair.

        Args:
            refresh_token: Current JWT refresh token
            client_fingerprint: Current client device fingerprint (MED-002)

        Returns:
            Dictionary containing:
            - access_token: New JWT access token
            - refresh_token: New JWT refresh token
            - token_type: "bearer"
            - expires_in: Access token expiration in seconds

        Raises:
            InvalidCredentialsError: If token is invalid, expired, revoked,
                or fingerprint mismatch (when ENFORCE_TOKEN_BINDING=true)
        """
        # Decode and validate refresh token
        try:
            payload = self._auth_service.decode_token(refresh_token)
        except JWTError:
            raise InvalidCredentialsError()

        # Verify token type
        if payload.get("type") != "refresh":
            raise InvalidCredentialsError()

        # MED-002: Validate device fingerprint if binding is enforced
        if settings.enforce_token_binding:
            token_fingerprint = payload.get("fgp")
            if token_fingerprint and client_fingerprint:
                if token_fingerprint != client_fingerprint:
                    logger.warning(
                        "Token fingerprint mismatch: expected %s, got %s",
                        token_fingerprint[:8] + "...",
                        client_fingerprint[:8] + "..." if client_fingerprint else "none",
                    )
                    raise InvalidCredentialsError()

        # Extract user ID
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise InvalidCredentialsError()

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            raise InvalidCredentialsError()

        # Find token in database
        token_hash = sha256(refresh_token.encode()).hexdigest()
        result = await self._session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.user_id == user_id,
            )
        )
        token_record = result.scalar_one_or_none()

        if not token_record:
            raise InvalidCredentialsError()

        # Verify token is not revoked
        if token_record.revoked_at is not None:
            raise InvalidCredentialsError()

        # Verify token is not expired
        if token_record.expires_at < datetime.now(UTC):
            raise InvalidCredentialsError()

        # Get user to retrieve role
        user_repo = AdminUserRepository(self._session)
        user = await user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise InvalidCredentialsError()

        # Revoke old token
        token_record.revoked_at = datetime.now(UTC)
        await self._session.flush()

        # Create new token pair
        # MED-003: Properly unpack token tuple (token, jti, expires_at)
        new_access_token, _access_jti, _access_expire = self._auth_service.create_access_token(
            subject=str(user.id),
            role=user.role,
        )
        # MED-002: Include client fingerprint in new refresh token for device binding
        new_refresh_token, _refresh_jti, new_refresh_expire = self._auth_service.create_refresh_token(
            subject=str(user.id),
            fingerprint=client_fingerprint,
        )

        # Store new refresh token hash in database
        new_token_hash = sha256(new_refresh_token.encode()).hexdigest()
        new_expires_at = new_refresh_expire  # Use actual expiry from token creation

        new_token_record = RefreshToken(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
        )
        self._session.add(new_token_record)
        await self._session.flush()

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }
