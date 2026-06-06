"""
Logout use case for refresh token revocation.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
from src.infrastructure.database.models.refresh_token_model import RefreshToken


@dataclass(frozen=True)
class RevokedAccessToken:
    jti: str
    expires_at: datetime


@dataclass(frozen=True)
class LogoutResult:
    refresh_token_revoked: bool
    access_tokens: tuple[RevokedAccessToken, ...] = ()


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

        # Find and revoke the token
        result = await self._session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        token_record = result.scalar_one_or_none()

        if not token_record:
            return LogoutResult(refresh_token_revoked=False)

        revoked_at = datetime.now(UTC)
        token_record.revoked_at = revoked_at
        access_tokens: list[RevokedAccessToken] = []

        principal_session_result = await self._session.execute(
            select(PrincipalSessionModel).where(
                PrincipalSessionModel.refresh_token_id == token_record.id,
                PrincipalSessionModel.revoked_at.is_(None),
            )
        )
        principal_session = principal_session_result.scalar_one_or_none()
        if principal_session:
            principal_session.revoked_at = revoked_at
            principal_session.status = "revoked"
            if principal_session.access_token_jti:
                access_tokens.append(
                    RevokedAccessToken(
                        jti=principal_session.access_token_jti,
                        expires_at=principal_session.expires_at,
                    )
                )

        await self._session.flush()
        return LogoutResult(refresh_token_revoked=True, access_tokens=tuple(access_tokens))

    async def execute_access_token(self, *, access_token_jti: str, expires_at: datetime) -> LogoutResult:
        """Revoke the currently presented access token and linked session.

        This is a defense-in-depth path for web logout: the current access JWT
        must stop working even if the refresh cookie is missing, stale, or could
        not be matched to a principal session.
        """
        revoked_at = datetime.now(UTC)
        refresh_token_revoked = False

        result = await self._session.execute(
            select(PrincipalSessionModel).where(
                PrincipalSessionModel.access_token_jti == access_token_jti,
                PrincipalSessionModel.revoked_at.is_(None),
            )
        )
        principal_session = result.scalar_one_or_none()

        if principal_session:
            principal_session.revoked_at = revoked_at
            principal_session.status = "revoked"
            if principal_session.refresh_token_id:
                refresh_token = await self._session.get(RefreshToken, principal_session.refresh_token_id)
                if refresh_token and refresh_token.revoked_at is None:
                    refresh_token.revoked_at = revoked_at
                    refresh_token_revoked = True
            await self._session.flush()

        return LogoutResult(
            refresh_token_revoked=refresh_token_revoked,
            access_tokens=(RevokedAccessToken(jti=access_token_jti, expires_at=expires_at),),
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
