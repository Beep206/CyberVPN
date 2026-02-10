"""Use case for creating a new partner referral code."""

import logging
import secrets
from uuid import UUID

from src.application.services.config_service import ConfigService
from src.domain.exceptions import MarkupExceedsLimitError
from src.infrastructure.database.models.partner_model import PartnerCodeModel
from src.infrastructure.database.repositories.partner_repo import PartnerRepository

logger = logging.getLogger(__name__)


class CreatePartnerCodeUseCase:
    """Create a new partner code with optional markup percentage.

    The markup is validated against the system-configured maximum.
    """

    def __init__(
        self,
        partner_repo: PartnerRepository,
        config_service: ConfigService,
    ) -> None:
        self._partner_repo = partner_repo
        self._config = config_service

    async def execute(
        self,
        partner_user_id: UUID,
        code: str,
        markup_pct: float = 0,
    ) -> PartnerCodeModel:
        """Create a partner code for *partner_user_id*.

        If *code* is empty, a random 8-character code is generated.

        Raises:
            MarkupExceedsLimitError: if markup_pct exceeds the configured maximum.
        """
        max_markup = await self._config.get_partner_max_markup_pct()
        if markup_pct > max_markup:
            logger.warning(
                "partner_code_markup_exceeds_limit",
                extra={
                    "partner_user_id": str(partner_user_id),
                    "markup_pct": markup_pct,
                    "max_markup_pct": max_markup,
                },
            )
            raise MarkupExceedsLimitError(markup_pct=markup_pct, max_pct=float(max_markup))

        if not code:
            code = secrets.token_urlsafe(6)[:8].upper()

        model = PartnerCodeModel(
            partner_user_id=partner_user_id,
            code=code,
            markup_pct=markup_pct,
        )

        result = await self._partner_repo.create_code(model)

        logger.info(
            "partner_code_created",
            extra={
                "partner_user_id": str(partner_user_id),
                "code": code,
                "markup_pct": markup_pct,
                "code_id": str(result.id),
            },
        )

        return result
