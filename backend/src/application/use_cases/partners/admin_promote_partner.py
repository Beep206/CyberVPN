"""Use case for promoting a mobile user to partner status."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.partners.create_partner_workspace import CreatePartnerWorkspaceUseCase
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository

logger = logging.getLogger(__name__)


class AdminPromotePartnerUseCase:
    """Admin-only action to promote a regular user to partner.

    Sets ``is_partner=True`` and records the promotion timestamp.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self,
        user_id: UUID,
        *,
        created_by_admin_user_id: UUID | None = None,
    ) -> tuple[MobileUserModel, UUID]:
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
        workspace_use_case = CreatePartnerWorkspaceUseCase(
            session=self._session,
            partner_account_repo=PartnerAccountRepository(self._session),
        )
        workspace, _membership = await workspace_use_case.execute(
            display_name=user.username or user.email,
            legacy_owner_user_id=user.id,
            created_by_admin_user_id=created_by_admin_user_id,
        )
        user.partner_account_id = workspace.id
        await self._session.flush()

        logger.info(
            "partner_promoted",
            extra={
                "user_id": str(user_id),
                "partner_account_id": str(workspace.id),
                "promoted_at": str(user.partner_promoted_at),
            },
        )

        return user, workspace.id
