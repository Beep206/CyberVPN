"""
Logout use case for refresh token revocation.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
from src.infrastructure.database.models.refresh_token_model import RefreshToken
from src.infrastructure.database.models.user_device_model import UserDeviceModel


@dataclass(frozen=True)
class RevokedAccessToken:
    jti: str
    expires_at: datetime


@dataclass(frozen=True)
class LogoutResult:
    refresh_token_revoked: bool
    access_tokens: tuple[RevokedAccessToken, ...] = ()
    refresh_tokens_revoked: int = 0
    principal_sessions_revoked: int = 0


@dataclass(frozen=True)
class LogoutScopeResult:
    access_tokens: tuple[RevokedAccessToken, ...] = ()
    refresh_tokens_revoked: int = 0
    principal_sessions_revoked: int = 0
    devices_revoked: int = 0


class LogoutUseCase:
    """
    Handles logout operations by revoking refresh tokens.

    Supports both single token revocation and revoking all tokens for a user.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, refresh_token: str) -> LogoutResult:
        """
        Revoke a specific refresh token.

        Args:
            refresh_token: JWT refresh token to revoke

        Note:
            Silently succeeds even if token doesn't exist in database.
            This prevents information leakage about token validity.
        """
        # Hash the token to find it in database
        token_hash = sha256(refresh_token.encode()).hexdigest()

        # Find and revoke the token family attached to the current session.
        result = await self._session.execute(
            select(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
            .with_for_update()
        )
        token_record = result.scalar_one_or_none()

        if not token_record:
            return LogoutResult(refresh_token_revoked=False)

        revoked_at = datetime.now(UTC)
        principal_session = await self._load_token_session(token_record)
        scope_result = await self._revoke_principal_session_scope(
            principal_session=principal_session,
            token_record=token_record,
            revoked_at=revoked_at,
            reason="logout",
            revoke_device=False,
        )

        return LogoutResult(
            refresh_token_revoked=scope_result.refresh_tokens_revoked > 0,
            access_tokens=scope_result.access_tokens,
            refresh_tokens_revoked=scope_result.refresh_tokens_revoked,
            principal_sessions_revoked=scope_result.principal_sessions_revoked,
        )

    async def execute_access_token(self, *, access_token_jti: str, expires_at: datetime) -> LogoutResult:
        """Revoke the currently presented access token and linked session.

        This is a defense-in-depth path for web logout: the current access JWT
        must stop working even if the refresh cookie is missing, stale, or could
        not be matched to a principal session.
        """
        revoked_at = datetime.now(UTC)
        result = await self._session.execute(
            select(PrincipalSessionModel)
            .where(
                PrincipalSessionModel.access_token_jti == access_token_jti,
                PrincipalSessionModel.revoked_at.is_(None),
            )
            .with_for_update()
        )
        principal_session = result.scalar_one_or_none()

        scope_result = await self._revoke_principal_session_scope(
            principal_session=principal_session,
            token_record=None,
            revoked_at=revoked_at,
            reason="logout",
            revoke_device=False,
        )
        access_tokens = list(scope_result.access_tokens)
        if not any(access_token.jti == access_token_jti for access_token in access_tokens):
            access_tokens.append(RevokedAccessToken(jti=access_token_jti, expires_at=expires_at))

        return LogoutResult(
            refresh_token_revoked=scope_result.refresh_tokens_revoked > 0,
            access_tokens=tuple(access_tokens),
            refresh_tokens_revoked=scope_result.refresh_tokens_revoked,
            principal_sessions_revoked=scope_result.principal_sessions_revoked,
        )

    async def execute_all(self, user_id: UUID) -> int:
        """
        Revoke all refresh tokens for a specific user.

        Useful for:
        - Logout from all devices
        - Security incident response
        - Password reset flows

        Args:
            user_id: UUID of the user whose tokens should be revoked

        Returns:
            Number of refresh token records revoked
        """
        # Revoke all active tokens for the user
        result = await self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.flush()
        return int(result.rowcount or 0)

    async def execute_realm(
        self,
        *,
        auth_realm_id: UUID,
        principal_subject: str,
        principal_class: str,
        reason: str = "logout_all",
    ) -> LogoutScopeResult:
        """Revoke all active sessions for one principal inside one auth realm."""

        result = await self._session.execute(
            select(PrincipalSessionModel)
            .where(
                PrincipalSessionModel.auth_realm_id == auth_realm_id,
                PrincipalSessionModel.principal_subject == principal_subject,
                PrincipalSessionModel.principal_class == principal_class,
                PrincipalSessionModel.revoked_at.is_(None),
            )
            .with_for_update()
        )
        sessions = list(result.scalars().all())
        return await self._revoke_sessions(sessions=sessions, reason=reason, revoke_devices=True)

    async def execute_device(
        self,
        *,
        auth_realm_id: UUID,
        principal_subject: str,
        principal_class: str,
        user_device_id: UUID,
        reason: str = "device_revoked",
    ) -> LogoutScopeResult:
        """Revoke active sessions for a selected stable user device."""

        result = await self._session.execute(
            select(PrincipalSessionModel)
            .where(
                PrincipalSessionModel.auth_realm_id == auth_realm_id,
                PrincipalSessionModel.principal_subject == principal_subject,
                PrincipalSessionModel.principal_class == principal_class,
                PrincipalSessionModel.user_device_id == user_device_id,
                PrincipalSessionModel.revoked_at.is_(None),
            )
            .with_for_update()
        )
        sessions = list(result.scalars().all())
        return await self._revoke_sessions(sessions=sessions, reason=reason, revoke_devices=True)

    async def execute_other_devices(
        self,
        *,
        auth_realm_id: UUID,
        principal_subject: str,
        principal_class: str,
        current_user_device_id: UUID,
        reason: str = "logout_others",
    ) -> LogoutScopeResult:
        """Revoke all active device sessions except the current device."""

        result = await self._session.execute(
            select(PrincipalSessionModel)
            .where(
                PrincipalSessionModel.auth_realm_id == auth_realm_id,
                PrincipalSessionModel.principal_subject == principal_subject,
                PrincipalSessionModel.principal_class == principal_class,
                PrincipalSessionModel.user_device_id.is_not(None),
                PrincipalSessionModel.user_device_id != current_user_device_id,
                PrincipalSessionModel.revoked_at.is_(None),
            )
            .with_for_update()
        )
        sessions = list(result.scalars().all())
        return await self._revoke_sessions(sessions=sessions, reason=reason, revoke_devices=True)

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

    async def _revoke_principal_session_scope(
        self,
        *,
        principal_session: PrincipalSessionModel | None,
        token_record: RefreshToken | None,
        revoked_at: datetime,
        reason: str,
        revoke_device: bool,
    ) -> LogoutScopeResult:
        if principal_session is None:
            refresh_tokens_revoked = 0
            if token_record is not None and token_record.revoked_at is None:
                token_record.revoked_at = revoked_at
                token_record.revoked_reason = reason
                refresh_tokens_revoked = 1
                await self._session.flush()
            return LogoutScopeResult(refresh_tokens_revoked=refresh_tokens_revoked)

        return await self._revoke_sessions(
            sessions=[principal_session],
            reason=reason,
            revoke_devices=revoke_device,
            token_record=token_record,
        )

    async def _revoke_sessions(
        self,
        *,
        sessions: list[PrincipalSessionModel],
        reason: str,
        revoke_devices: bool,
        token_record: RefreshToken | None = None,
    ) -> LogoutScopeResult:
        if not sessions:
            return LogoutScopeResult()

        revoked_at = datetime.now(UTC)
        access_tokens: list[RevokedAccessToken] = []
        session_ids: list[UUID] = []
        direct_refresh_ids: set[UUID] = set()
        device_ids: set[UUID] = set()

        for principal_session in sessions:
            session_ids.append(principal_session.id)
            principal_session.revoked_at = revoked_at
            principal_session.status = "revoked"
            principal_session.last_seen_at = revoked_at
            if principal_session.access_token_jti:
                access_tokens.append(
                    RevokedAccessToken(
                        jti=principal_session.access_token_jti,
                        expires_at=principal_session.expires_at,
                    )
                )
            if principal_session.refresh_token_id:
                direct_refresh_ids.add(principal_session.refresh_token_id)
            if principal_session.current_refresh_token_id:
                direct_refresh_ids.add(principal_session.current_refresh_token_id)
            if principal_session.user_device_id:
                device_ids.add(principal_session.user_device_id)

        if token_record is not None:
            direct_refresh_ids.add(token_record.id)

        refresh_filters = [RefreshToken.principal_session_id.in_(session_ids)]
        if direct_refresh_ids:
            refresh_filters.append(RefreshToken.id.in_(direct_refresh_ids))

        refresh_result = await self._session.execute(
            update(RefreshToken)
            .where(
                or_(*refresh_filters),
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at, revoked_reason=reason)
        )
        refresh_tokens_revoked = int(refresh_result.rowcount or 0)

        devices_revoked = 0
        if revoke_devices and device_ids:
            device_result = await self._session.execute(
                update(UserDeviceModel)
                .where(
                    UserDeviceModel.id.in_(device_ids),
                    UserDeviceModel.revoked_at.is_(None),
                )
                .values(revoked_at=revoked_at, revoked_reason=reason)
            )
            devices_revoked = int(device_result.rowcount or 0)

        await self._session.flush()
        return LogoutScopeResult(
            access_tokens=tuple(access_tokens),
            refresh_tokens_revoked=refresh_tokens_revoked,
            principal_sessions_revoked=len(sessions),
            devices_revoked=devices_revoked,
        )
