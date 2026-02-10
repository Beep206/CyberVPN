"""Use case for promoting a mobile user to partner status."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.mobile_user_model import MobileUserModel

logger = logging.getLogger(__name__)


class AdminPromotePartnerUseCase:
    """Admin-only action to promote a regular user to partner.

    Sets ``is_partner=True`` and records the promotion timestamp.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, user_id: UUID) -> MobileUserModel:
        """Promote *user_id* to partner.

        Raises:
            ValueError: if user not found or already a partner.
        """
        user = await self._session.get(MobileUserModel, user_id)
        if user is None:
            logger.warning("promote_partner_user_not_found", extra={"user_id": str(user_id)})
            msg = f"User not found: {user_id}"
            raise ValueError(msg)

        if user.is_partner:
            logger.warning("promote_partner_already_partner", extra={"user_id": str(user_id)})
            msg = f"User {user_id} is already a partner"
            raise ValueError(msg)

        user.is_partner = True
        user.partner_promoted_at = datetime.now(UTC)
        await self._session.flush()

        logger.info(
            "partner_promoted",
            extra={"user_id": str(user_id), "promoted_at": str(user.partner_promoted_at)},
        )

        return user
