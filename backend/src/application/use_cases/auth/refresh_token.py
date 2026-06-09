"""Refresh token use case for JWT token rotation.

Includes device fingerprint validation (MED-002) when ENFORCE_TOKEN_BINDING is enabled.
"""

import logging
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.domain.exceptions import InvalidCredentialsError
from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
from src.infrastructure.database.models.refresh_token_model import RefreshToken
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository

logger = logging.getLogger("cybervpn")

BENIGN_REFRESH_REPLAY_TOLERANCE = timedelta(seconds=10)


class RefreshTokenReplayError(InvalidCredentialsError):
    """Raised when a previously consumed refresh token is presented again."""

    def __init__(self, *, clear_cookies: bool) -> None:
        super().__init__()
        self.clear_cookies = clear_cookies


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
        access_extra: dict | None = None,
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
        token_filters = [
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == user_id,
            RefreshToken.principal_class == principal_type,
            RefreshToken.principal_subject == str(user_id),
            RefreshToken.scope_family == scope_family,
        ]
        if auth_realm_id is not None:
            token_filters.append(RefreshToken.auth_realm_id == auth_realm_id)
        if audience is not None:
            token_filters.append(RefreshToken.audience == audience)

        result = await self._session.execute(select(RefreshToken).where(*token_filters).with_for_update())
        token_record = result.scalar_one_or_none()

        if not token_record:
            raise InvalidCredentialsError()

        now = datetime.now(UTC)

        # Verify token is not expired
        if self._normalize_utc(token_record.expires_at) < now:
            raise InvalidCredentialsError()

        if token_record.revoked_at is not None or token_record.consumed_at is not None:
            await self._handle_consumed_token(token_record, now=now)

        user_repo = (
            MobileUserRepository(self._session) if principal_type == "customer" else AdminUserRepository(self._session)
        )
        user = await user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise InvalidCredentialsError()
        if auth_realm_id is not None and user.auth_realm_id != auth_realm_id:
            if not (include_legacy_default and user.auth_realm_id is None):
                raise InvalidCredentialsError()
        role = "mobile_user" if principal_type == "customer" else user.role

        principal_session = await self._load_token_session(token_record)
        if principal_session is not None:
            self._validate_principal_session(
                principal_session,
                token_record=token_record,
                now=now,
                user_id=user_id,
                auth_realm_id=auth_realm_id,
                audience=audience,
                principal_type=principal_type,
                scope_family=scope_family,
            )
        elif auth_realm_id is not None or audience is not None:
            raise InvalidCredentialsError()

        # Create new token pair
        # MED-003: Properly unpack token tuple (token, jti, expires_at)
        new_access_token, new_access_jti, _access_expire = self._auth_service.create_access_token(
            subject=str(user.id),
            role=role,
            extra=access_extra,
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
        family_id = token_record.family_id or token_record.id
        token_record.family_id = family_id
        new_refresh_record = RefreshToken(
            user_id=user.id,
            auth_realm_id=auth_realm_id or token_record.auth_realm_id,
            principal_class=principal_type,
            principal_subject=str(user.id),
            audience=audience or token_record.audience,
            scope_family=scope_family,
            token_hash=sha256(new_refresh_token.encode()).hexdigest(),
            expires_at=new_refresh_expire,
            device_id=token_record.device_id,
            ip_address=client_ip or token_record.ip_address,
            user_agent=user_agent or token_record.user_agent,
            jti=_refresh_jti,
            family_id=family_id,
            parent_token_id=token_record.id,
            principal_session_id=principal_session.id if principal_session else token_record.principal_session_id,
        )
        self._session.add(new_refresh_record)
        await self._session.flush()

        token_record.consumed_at = now
        token_record.revoked_at = now
        token_record.revoked_reason = "rotated"
        token_record.replaced_by_token_id = new_refresh_record.id
        token_record.last_used_at = now

        if principal_session:
            principal_session.current_refresh_token_id = new_refresh_record.id
            principal_session.access_token_jti = new_access_jti
            principal_session.last_seen_at = now
            principal_session.expires_at = new_refresh_expire
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

    async def _load_token_session(self, token_record: RefreshToken) -> PrincipalSessionModel | None:
        if token_record.principal_session_id is not None:
            result = await self._session.execute(
                select(PrincipalSessionModel)
                .where(PrincipalSessionModel.id == token_record.principal_session_id)
                .with_for_update()
            )
            return result.scalar_one_or_none()

        result = await self._session.execute(
            select(PrincipalSessionModel)
            .where(
                or_(
                    PrincipalSessionModel.refresh_token_id == token_record.id,
                    PrincipalSessionModel.current_refresh_token_id == token_record.id,
                )
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    def _validate_principal_session(
        self,
        principal_session: PrincipalSessionModel,
        *,
        token_record: RefreshToken,
        now: datetime,
        user_id: UUID,
        auth_realm_id: UUID | None,
        audience: str | None,
        principal_type: str,
        scope_family: str,
    ) -> None:
        if principal_session.current_refresh_token_id != token_record.id:
            raise InvalidCredentialsError()
        if principal_session.status != "active" or principal_session.revoked_at is not None:
            raise InvalidCredentialsError()
        if self._normalize_utc(principal_session.expires_at) < now:
            raise InvalidCredentialsError()
        if principal_session.principal_subject != str(user_id):
            raise InvalidCredentialsError()
        if auth_realm_id is not None and principal_session.auth_realm_id != auth_realm_id:
            raise InvalidCredentialsError()
        if audience is not None and principal_session.audience != audience:
            raise InvalidCredentialsError()
        if principal_session.principal_class != principal_type:
            raise InvalidCredentialsError()
        if principal_session.scope_family != scope_family:
            raise InvalidCredentialsError()

    async def _handle_consumed_token(self, token_record: RefreshToken, *, now: datetime) -> None:
        consumed_at = self._normalize_utc(token_record.consumed_at) if token_record.consumed_at else None
        if (
            consumed_at is not None
            and token_record.replaced_by_token_id is not None
            and now - consumed_at <= BENIGN_REFRESH_REPLAY_TOLERANCE
        ):
            raise RefreshTokenReplayError(clear_cookies=False)

        await self._revoke_refresh_family(token_record, now=now)
        raise RefreshTokenReplayError(clear_cookies=True)

    async def _revoke_refresh_family(self, token_record: RefreshToken, *, now: datetime) -> None:
        principal_session = await self._load_token_session(token_record)
        if principal_session is not None:
            principal_session.status = "revoked"
            principal_session.revoked_at = now
            principal_session.last_seen_at = now

        family_id = token_record.family_id
        if family_id is not None:
            await self._session.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == family_id)
                .values(revoked_at=now, revoked_reason="replay_detected")
            )
        elif token_record.principal_session_id is not None:
            await self._session.execute(
                update(RefreshToken)
                .where(RefreshToken.principal_session_id == token_record.principal_session_id)
                .values(revoked_at=now, revoked_reason="replay_detected")
            )
        else:
            token_record.revoked_at = now
            token_record.revoked_reason = "replay_detected"
        await self._session.flush()
