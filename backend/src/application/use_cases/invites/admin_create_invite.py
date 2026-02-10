"""Use case for admin-granted invite code creation."""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.application.services.config_service import ConfigService
from src.domain.enums import InviteSource
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository

logger = logging.getLogger(__name__)


class AdminCreateInviteUseCase:
    """Allow an admin to manually create invite codes.

    Unlike payment-generated invites, admin-granted codes are not tied
    to a specific plan or payment.  The admin specifies the ``free_days``
    value and optional ``count`` directly.
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
        free_days: int,
        count: int = 1,
        plan_id: UUID | None = None,
    ) -> list[InviteCodeModel]:
        """Create *count* admin-granted invite codes.

        Args:
            owner_user_id: The user who will own the invite codes.
            free_days: Number of free subscription days the code grants.
            count: How many codes to generate (default 1).
            plan_id: Optional plan to associate with the codes.

        Returns:
            List of newly persisted ``InviteCodeModel`` instances.
        """
        default_expiry_days = await self._config_service.get_invite_default_expiry_days()
        expires_at = datetime.now(UTC) + timedelta(days=default_expiry_days)

        models = [
            InviteCodeModel(
                code=self._generate_code(),
                owner_user_id=owner_user_id,
                free_days=free_days,
                plan_id=plan_id,
                source=InviteSource.ADMIN_GRANT,
                source_payment_id=None,
                expires_at=expires_at,
            )
            for _ in range(count)
        ]

        created = await self._invite_repo.create_batch(models)

        logger.info(
            "admin_invites_created",
            extra={
                "owner_user_id": str(owner_user_id),
                "count": count,
                "free_days": free_days,
                "plan_id": str(plan_id) if plan_id else None,
                "expires_at": str(expires_at),
            },
        )

        return created

    @staticmethod
    def _generate_code() -> str:
        """Return a random 8-character uppercase alphanumeric code."""
        return secrets.token_urlsafe(6)[:8].upper()
