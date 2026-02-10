"""Use case for binding a user to a partner via a partner code."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import PartnerCodeNotFoundError, UserAlreadyBoundToPartnerError
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.partner_repo import PartnerRepository

logger = logging.getLogger(__name__)


class BindPartnerUseCase:
    """Bind a mobile user to a partner through an active partner code.

    Once bound, future payments from this user generate earnings for
    the partner who owns the code.
    """

    def __init__(self, session: AsyncSession, partner_repo: PartnerRepository) -> None:
        self._session = session
        self._partner_repo = partner_repo

    async def execute(self, user_id: UUID, partner_code: str) -> MobileUserModel:
        """Bind *user_id* to the partner who owns *partner_code*.

        Raises:
            ValueError: if the user is not found or tries to bind to their own code.
            UserAlreadyBoundToPartnerError: if the user is already bound.
            PartnerCodeNotFoundError: if the code does not exist or is inactive.
        """
        user = await self._session.get(MobileUserModel, user_id)
        if user is None:
            msg = f"User not found: {user_id}"
            raise ValueError(msg)

        if user.partner_user_id is not None:
            logger.warning(
                "bind_partner_already_bound",
                extra={"user_id": str(user_id), "existing_partner": str(user.partner_user_id)},
            )
            raise UserAlreadyBoundToPartnerError(str(user_id))

        code_model = await self._partner_repo.get_active_code_by_code(partner_code)
        if code_model is None:
            logger.warning(
                "bind_partner_code_not_found",
                extra={"user_id": str(user_id), "code": partner_code},
            )
            raise PartnerCodeNotFoundError(partner_code)

        if code_model.partner_user_id == user_id:
            msg = "Cannot bind to own partner code"
            raise ValueError(msg)

        user.partner_user_id = code_model.partner_user_id
        await self._session.flush()

        logger.info(
            "user_bound_to_partner",
            extra={
                "user_id": str(user_id),
                "partner_user_id": str(code_model.partner_user_id),
                "code": partner_code,
            },
        )

        return user
