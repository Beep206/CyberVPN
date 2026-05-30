"""Use case for activating a user's trial period."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository

from .stage1_trial_policy import (
    STAGE1_TRIAL_DEVICE_LIMIT,
    STAGE1_TRIAL_DURATION_DAYS,
    STAGE1_TRIAL_ONE_PER_ACCOUNT,
    STAGE1_TRIAL_POLICY_CONTEXT,
    STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES,
)
from .stage1_trial_provisioning import (
    Stage1TrialProvisioningGateway,
    Stage1TrialProvisioningResult,
    Stage1TrialProvisioningService,
)

logger = logging.getLogger(__name__)

TRIAL_DURATION_DAYS = STAGE1_TRIAL_DURATION_DAYS


class TrialActivationResult:
    """Result of trial activation attempt."""

    def __init__(
        self,
        activated: bool,
        trial_end: datetime,
        message: str,
        provisioning: Stage1TrialProvisioningResult | None = None,
    ):
        self.activated = activated
        self.trial_end = trial_end
        self.message = message
        self.provisioning = provisioning
        self.provisioning_state = "ready" if provisioning is not None else "not_requested"
        self.duration_days = STAGE1_TRIAL_DURATION_DAYS
        self.device_limit = STAGE1_TRIAL_DEVICE_LIMIT
        self.traffic_limit_bytes = STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES
        self.one_trial_per_account = STAGE1_TRIAL_ONE_PER_ACCOUNT
        self.policy_context = dict(STAGE1_TRIAL_POLICY_CONTEXT)


class ActivateTrialUseCase:
    """Use case for activating a user's trial period."""

    def __init__(
        self,
        session: AsyncSession,
        provisioning_gateway: Stage1TrialProvisioningGateway | None = None,
    ):
        """Initialize with database session.

        Args:
            session: SQLAlchemy async session for database access
        """
        self.session = session
        self.user_repo = MobileUserRepository(session)
        self._provisioning = (
            Stage1TrialProvisioningService(provisioning_gateway) if provisioning_gateway is not None else None
        )

    async def execute(self, user_id: UUID) -> TrialActivationResult:
        """Activate a trial period for the user.

        Args:
            user_id: UUID of the mobile user

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

        trial_end = now + timedelta(days=TRIAL_DURATION_DAYS)
        provisioning_result = None
        if self._provisioning is not None:
            provisioning_result = await self._provisioning.provision(
                customer_account_id=user_id,
                email=user.email,
                username=user.username,
                telegram_id=user.telegram_id,
                trial_expires_at=trial_end,
                existing_remnawave_uuid=user.remnawave_uuid,
            )

        # Activate trial only after upstream provisioning succeeds when a gateway is configured.
        user.trial_activated_at = now
        user.trial_expires_at = trial_end
        if provisioning_result is not None:
            user.remnawave_uuid = provisioning_result.remnawave_uuid
            user.subscription_url = provisioning_result.subscription_url

        await self.user_repo.update(user)

        logger.info(
            "Trial activated",
            extra={
                "user_id": str(user_id),
                "trial_end": trial_end.isoformat(),
                "provisioning_state": "ready" if provisioning_result is not None else "not_requested",
                "vpn_profile_id": provisioning_result.profile_id if provisioning_result is not None else None,
            },
        )

        return TrialActivationResult(
            activated=True,
            trial_end=trial_end,
            message=f"Trial activated successfully. Expires in {TRIAL_DURATION_DAYS} days.",
            provisioning=provisioning_result,
        )
