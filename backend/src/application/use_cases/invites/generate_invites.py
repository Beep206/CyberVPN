"""Use case for generating invite codes after a successful payment."""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.domain.enums import InviteSource
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository

logger = logging.getLogger(__name__)


class GenerateInvitesForPaymentUseCase:
    """Create invite codes for a user who completed a plan purchase.

    The number of codes and the ``free_days`` value are driven by the
    canonical ``plan.invite_bundle`` configuration. If the purchased plan
    has no invite bundle the use case returns an empty list (no-op).
    """

    def __init__(
        self,
        invite_repo: InviteCodeRepository,
        plan_repo: SubscriptionPlanRepository,
    ) -> None:
        self._invite_repo = invite_repo
        self._plan_repo = plan_repo

    async def execute(
        self,
        owner_user_id: UUID,
        plan_id: UUID,
        payment_id: UUID,
    ) -> list[InviteCodeModel]:
        """Generate invite codes for *owner_user_id* linked to *payment_id*.

        Returns:
            List of newly persisted ``InviteCodeModel`` instances, or an
            empty list when the plan has no invite rule.
        """
        plan = await self._plan_repo.get_by_id(plan_id)
        if plan is None:
            logger.debug(
                "invite_plan_not_found",
                extra={"plan_id": str(plan_id), "owner_user_id": str(owner_user_id)},
            )
            return []

        bundle = plan.invite_bundle or {}
        invite_count = int(bundle.get("count", 0) or 0)
        free_days = int(bundle.get("friend_days", 0) or 0)
        expiry_days = int(bundle.get("expiry_days", 0) or 0)

        if invite_count <= 0 or free_days <= 0 or expiry_days <= 0:
            logger.debug(
                "invite_bundle_disabled_for_plan",
                extra={"plan_id": str(plan_id), "owner_user_id": str(owner_user_id), "bundle": bundle},
            )
            return []

        expires_at = datetime.now(UTC) + timedelta(days=expiry_days)

        models = [
            InviteCodeModel(
                code=self._generate_code(),
                owner_user_id=owner_user_id,
                free_days=free_days,
                plan_id=plan_id,
                source=InviteSource.PURCHASE,
                source_payment_id=payment_id,
                expires_at=expires_at,
            )
            for _ in range(invite_count)
        ]

        created = await self._invite_repo.create_batch(models)

        logger.info(
            "invites_generated_for_payment",
            extra={
                "owner_user_id": str(owner_user_id),
                "plan_id": str(plan_id),
                "payment_id": str(payment_id),
                "count": invite_count,
                "free_days": free_days,
                "expires_at": str(expires_at),
            },
        )

        return created

    @staticmethod
    def _generate_code() -> str:
        """Return a random 8-character uppercase alphanumeric code."""
        return secrets.token_urlsafe(6)[:8].upper()
