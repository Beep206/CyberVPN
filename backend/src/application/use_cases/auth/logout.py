"""
Logout use case for refresh token revocation.
"""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.refresh_token_model import RefreshToken


class LogoutUseCase:
    """
    Handles logout operations by revoking refresh tokens.

    Supports both single token revocation and revoking all tokens for a user.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, refresh_token: str) -> None:
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

        if token_record:
            token_record.revoked_at = datetime.now(UTC)
            await self._session.flush()

    async def execute_all(self, user_id: UUID) -> None:
        """
        Revoke all refresh tokens for a specific user.

        Useful for:
        - Logout from all devices
        - Security incident response
        - Password reset flows

        Args:
            user_id: UUID of the user whose tokens should be revoked
        """
        # Revoke all active tokens for the user
        await self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.flush()
