"""Delete account use case for soft-deleting the current user (FEAT-03).

Soft-deletes the user account by setting is_active=False and deleted_at,
then revokes all refresh tokens and JWT sessions.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.jwt_revocation_service import JWTRevocationService
from src.application.use_cases.auth.logout import LogoutUseCase
from src.domain.exceptions.domain_errors import UserNotFoundError
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository

logger = logging.getLogger(__name__)


class DeleteAccountUseCase:
    """Soft-delete the authenticated user's account.

    Operations:
    1. Verify user exists
    2. Set is_active=False, deleted_at=now
    3. Revoke all DB refresh tokens
    4. Revoke all Redis-tracked JWT access tokens
    """

    def __init__(
        self,
        user_repo: AdminUserRepository,
        session: AsyncSession,
        redis_client: aioredis.Redis,
    ) -> None:
        self._user_repo = user_repo
        self._session = session
        self._redis_client = redis_client

    async def execute(self, user_id: UUID) -> None:
        """Soft-delete user account and revoke all tokens.

        Args:
            user_id: UUID of the authenticated user requesting deletion.

        Raises:
            UserNotFoundError: If the user does not exist.
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))

        # Soft-delete: deactivate and stamp deletion time
        user.is_active = False
        user.deleted_at = datetime.now(UTC)
        await self._session.flush()

        # Revoke all DB refresh tokens
        logout_use_case = LogoutUseCase(session=self._session)
        await logout_use_case.execute_all(user_id)

        # Revoke all Redis-tracked JWT access tokens
        revocation_service = JWTRevocationService(self._redis_client)
        revoked_count = await revocation_service.revoke_all_user_tokens(str(user_id))

        logger.info(
            "Account soft-deleted",
            extra={
                "user_id": str(user_id),
                "jwt_sessions_revoked": revoked_count,
            },
        )
