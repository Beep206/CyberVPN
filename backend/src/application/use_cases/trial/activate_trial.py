"""Use case for activating a user's trial period."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository

logger = logging.getLogger(__name__)

TRIAL_DURATION_DAYS = 7


class TrialActivationResult:
    """Result of trial activation attempt."""

    def __init__(self, activated: bool, trial_end: datetime, message: str):
        self.activated = activated
        self.trial_end = trial_end
        self.message = message


class ActivateTrialUseCase:
    """Use case for activating a user's trial period."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session.

        Args:
            session: SQLAlchemy async session for database access
        """
        self.session = session
        self.user_repo = AdminUserRepository(session)

    async def execute(self, user_id: UUID) -> TrialActivationResult:
        """Activate a trial period for the user.

        Args:
            user_id: UUID of the admin user

        Returns:
            TrialActivationResult with activation status and details

        Raises:
            ValueError: If user not found or already used trial
        """
        # Fetch user from database
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Check if user already used trial
        if user.trial_activated_at is not None:
            raise ValueError("Trial already activated. Only one trial per user is allowed.")

        # Check if user has an active trial
        now = datetime.now(UTC)
        if user.trial_expires_at and user.trial_expires_at > now:
            # Trial is still active
            days_remaining = (user.trial_expires_at - now).days
            return TrialActivationResult(
                activated=False,
                trial_end=user.trial_expires_at,
                message=f"Trial is already active. {days_remaining} days remaining.",
            )

        # Activate trial
        trial_end = now + timedelta(days=TRIAL_DURATION_DAYS)
        user.trial_activated_at = now
        user.trial_expires_at = trial_end

        await self.user_repo.update(user)

        logger.info(
            "Trial activated",
            extra={
                "user_id": str(user_id),
                "trial_end": trial_end.isoformat(),
            },
        )

        return TrialActivationResult(
            activated=True,
            trial_end=trial_end,
            message=f"Trial activated successfully. Expires in {TRIAL_DURATION_DAYS} days.",
        )
