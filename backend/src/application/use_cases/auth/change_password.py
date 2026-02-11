"""Use case for changing a user's password."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository

logger = logging.getLogger(__name__)


class ChangePasswordUseCase:
    """Use case for changing a user's password with verification."""

    def __init__(self, session: AsyncSession, auth_service: AuthService):
        """Initialize with database session and auth service.

        Args:
            session: SQLAlchemy async session for database access
            auth_service: Auth service for password hashing
        """
        self.session = session
        self.auth_service = auth_service
        self.user_repo = AdminUserRepository(session)

    async def execute(self, user_id: UUID, current_password: str, new_password: str) -> None:
        """Change user's password after verifying current password.

        Args:
            user_id: UUID of the user
            current_password: Current password for verification
            new_password: New password to set (must meet strength requirements)

        Raises:
            ValueError: If user not found, current password incorrect, or new password invalid
        """
        # Fetch user from database
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Check if user has a password (OAuth-only users don't)
        if not user.password_hash:
            raise ValueError("Password authentication is not available for this account")

        # Verify current password
        if not self.auth_service.verify_password(current_password, user.password_hash):
            logger.warning(
                "Password change failed - incorrect current password",
                extra={"user_id": str(user_id)},
            )
            raise ValueError("Current password is incorrect")

        # Prevent reusing the same password
        if self.auth_service.verify_password(new_password, user.password_hash):
            raise ValueError("New password must be different from current password")

        # Hash new password
        new_password_hash = await self.auth_service.hash_password(new_password)

        # Update user password
        user.password_hash = new_password_hash
        await self.user_repo.update(user)

        logger.info(
            "Password changed successfully",
            extra={"user_id": str(user_id)},
        )
