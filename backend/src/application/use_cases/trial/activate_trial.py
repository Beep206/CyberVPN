"""Use case for activating a user's trial period."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_create_attempts import (
    RemnawaveCreateAttemptConflict,
    RemnawaveCreateAttemptService,
    remnawave_create_request_hash,
    remnawave_customer_create_key,
)
from src.application.services.remnawave_identity_access import (
    persist_runtime_mapped_mobile_identity,
    resolve_exact_mapped_mobile_user_ref,
)
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
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
        create_attempts: RemnawaveCreateAttemptService | None = None
        create_record = None
        if self._provisioning is not None:
            existing_ref = await resolve_exact_mapped_mobile_user_ref(self.session, user)
            if existing_ref is None:
                create_attempts = RemnawaveCreateAttemptService(self.session)
                try:
                    decision = await create_attempts.begin(
                        scope="remnawave-customer:create",
                        idempotency_key=remnawave_customer_create_key(user_id),
                        request_hash=remnawave_create_request_hash(
                            {
                                "customer_account_id": str(user_id),
                                "trial_expires_at": trial_end,
                                "traffic_limit_bytes": STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES,
                                "device_limit": STAGE1_TRIAL_DEVICE_LIMIT,
                            }
                        ),
                        customer_account_id=user_id,
                    )
                except RemnawaveCreateAttemptConflict as exc:
                    raise ValueError("Trial Remnawave creation requires reconciliation") from exc
                if not decision.should_mutate:
                    raise ValueError("Trial Remnawave creation requires reconciliation")
                create_record = decision.record
            try:
                provisioning_result = await self._provisioning.provision(
                    customer_account_id=user_id,
                    email=user.email,
                    username=user.username,
                    telegram_id=user.telegram_id,
                    trial_expires_at=trial_end,
                    existing_remnawave_uuid=(
                        str(existing_ref.legacy_uuid)
                        if existing_ref is not None and existing_ref.legacy_uuid is not None
                        else None
                    ),
                    existing_remnawave_user_id=(
                        existing_ref.require_numeric_id() if existing_ref is not None else None
                    ),
                )
            except Exception:
                if create_attempts is not None and create_record is not None:
                    await create_attempts.mark_reconciliation_required(create_record)
                raise

        # Activate trial only after upstream provisioning succeeds when a gateway is configured.
        user.trial_activated_at = now
        user.trial_expires_at = trial_end
        if provisioning_result is not None:
            await persist_runtime_mapped_mobile_identity(
                self.session,
                customer=user,
                remnawave_user_id=provisioning_result.remnawave_user_id,
                remnawave_uuid=provisioning_result.remnawave_uuid,
                source="trial_activation",
            )
            user.subscription_url = provisioning_result.subscription_url
            if create_attempts is not None and create_record is not None:
                await create_attempts.mark_completed(
                    create_record,
                    user_ref=RemnawaveUserRef(
                        id=provisioning_result.remnawave_user_id,
                        legacy_uuid=(
                            UUID(provisioning_result.remnawave_uuid)
                            if provisioning_result.remnawave_uuid is not None
                            else None
                        ),
                    ),
                )

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
