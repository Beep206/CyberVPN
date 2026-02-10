"""Use case for generating invite codes after a successful payment."""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.application.services.config_service import ConfigService
from src.domain.enums import InviteSource
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository

logger = logging.getLogger(__name__)


class GenerateInvitesForPaymentUseCase:
    """Create invite codes for a user who completed a plan purchase.

    The number of codes and the ``free_days`` value are driven by the
    invite plan rules stored in the system configuration.  If the
    purchased plan has no associated rule the use case returns an empty
    list (no-op).
    """

    def __init__(
        self,
        invite_repo: InviteCodeRepository,
        config_service: ConfigService,
    ) -> None:
        self._invite_repo = invite_repo
        self._config_service = config_service

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
        rules = await self._config_service.get_invite_plan_rules()

        rule = next(
            (r for r in rules if str(r["plan_id"]) == str(plan_id)),
            None,
        )

        if rule is None:
            logger.debug(
                "no_invite_rule_for_plan",
                extra={"plan_id": str(plan_id), "owner_user_id": str(owner_user_id)},
            )
            return []

        invite_count: int = int(rule["invite_count"])
        free_days: int = int(rule["free_days"])
        default_expiry_days = await self._config_service.get_invite_default_expiry_days()
        expires_at = datetime.now(UTC) + timedelta(days=default_expiry_days)

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
