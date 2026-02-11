"""Use case for retrieving a user's trial status."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository

logger = logging.getLogger(__name__)


class TrialStatus:
    """DTO for trial status information."""

    def __init__(
        self,
        is_trial_active: bool,
        trial_start: datetime | None,
        trial_end: datetime | None,
        days_remaining: int,
        is_eligible: bool,
    ):
        self.is_trial_active = is_trial_active
        self.trial_start = trial_start
        self.trial_end = trial_end
        self.days_remaining = days_remaining
        self.is_eligible = is_eligible


class GetTrialStatusUseCase:
    """Use case for retrieving trial status for a user."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session.

        Args:
            session: SQLAlchemy async session for database access
        """
        self.session = session
        self.user_repo = AdminUserRepository(session)

    async def execute(self, user_id: UUID) -> TrialStatus:
        """Get the trial status for a user.

        Args:
            user_id: UUID of the admin user

        Returns:
            TrialStatus with current trial information

        Raises:
            ValueError: If user not found
        """
        # Fetch user from database
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        now = datetime.now(UTC)

        # Check if user has ever activated a trial
        if user.trial_activated_at is None:
            # Never used trial - eligible
            return TrialStatus(
                is_trial_active=False,
                trial_start=None,
                trial_end=None,
                days_remaining=0,
                is_eligible=True,
            )

        # User has used trial - check if it's still active
        is_active = user.trial_expires_at is not None and user.trial_expires_at > now

        days_remaining = 0
        if is_active and user.trial_expires_at:
            days_remaining = (user.trial_expires_at - now).days

        logger.info(
            "Trial status retrieved",
            extra={
                "user_id": str(user_id),
                "is_active": is_active,
                "days_remaining": days_remaining,
            },
        )

        return TrialStatus(
            is_trial_active=is_active,
            trial_start=user.trial_activated_at,
            trial_end=user.trial_expires_at,
            days_remaining=days_remaining,
            is_eligible=False,  # Already used trial
        )
