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
from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
from src.infrastructure.database.models.refresh_token_model import RefreshToken
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.presentation.api.v1.auth.session_tokens import store_refresh_token

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

    @staticmethod
    def _normalize_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    async def execute(
        self,
        refresh_token: str,
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
            payload = self._auth_service.decode_token(refresh_token, audience=audience)
        except JWTError:
            try:
                payload = self._auth_service.decode_token(refresh_token, audience=None)
            except JWTError:
                raise InvalidCredentialsError() from None

        if audience and payload.get("aud") and payload.get("aud") != audience:
            raise InvalidCredentialsError()
        if auth_realm_key and payload.get("realm_key") and payload.get("realm_key") != auth_realm_key:
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
            raise InvalidCredentialsError() from None

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
        if self._normalize_utc(token_record.expires_at) < datetime.now(UTC):
            raise InvalidCredentialsError()

        # Get user to retrieve role
        user_repo = AdminUserRepository(self._session)
        user = await user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise InvalidCredentialsError()
        if auth_realm_id is not None and user.auth_realm_id != auth_realm_id:
            if not (include_legacy_default and user.auth_realm_id is None):
                raise InvalidCredentialsError()

        # Revoke old token
        token_record.revoked_at = datetime.now(UTC)
        await self._session.flush()

        # Create new token pair
        # MED-003: Properly unpack token tuple (token, jti, expires_at)
        new_access_token, new_access_jti, _access_expire = self._auth_service.create_access_token(
            subject=str(user.id),
            role=user.role,
            audience=audience,
            principal_type=principal_type,
            realm_id=str(auth_realm_id) if auth_realm_id else payload.get("realm_id"),
            realm_key=auth_realm_key or payload.get("realm_key"),
            scope_family=scope_family,
        )
        # MED-002: Include client fingerprint in new refresh token for device binding
        new_refresh_token, _refresh_jti, new_refresh_expire = self._auth_service.create_refresh_token(
            subject=str(user.id),
            fingerprint=client_fingerprint,
            audience=audience,
            principal_type=principal_type,
            realm_id=str(auth_realm_id) if auth_realm_id else payload.get("realm_id"),
            realm_key=auth_realm_key or payload.get("realm_key"),
            scope_family=scope_family,
        )
        await store_refresh_token(
            self._session,
            user_id=user.id,
            refresh_token=new_refresh_token,
            expires_at=new_refresh_expire,
            device_id=client_fingerprint or token_record.device_id,
            ip_address=client_ip or token_record.ip_address,
            user_agent=user_agent or token_record.user_agent,
            auth_realm_id=auth_realm_id or user.auth_realm_id,
            principal_class=principal_type,
            principal_subject=str(user.id),
            audience=audience or payload.get("aud"),
            scope_family=scope_family,
            access_token_jti=new_access_jti,
        )

        result = await self._session.execute(
            select(PrincipalSessionModel).where(PrincipalSessionModel.refresh_token_id == token_record.id)
        )
        principal_session = result.scalar_one_or_none()
        if principal_session:
            principal_session.revoked_at = datetime.now(UTC)
            principal_session.status = "revoked"
            await self._session.flush()

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "auth_realm_id": (
                str(auth_realm_id or user.auth_realm_id) if (auth_realm_id or user.auth_realm_id) else None
            ),
            "auth_realm_key": auth_realm_key or payload.get("realm_key"),
            "audience": audience or payload.get("aud"),
        }
