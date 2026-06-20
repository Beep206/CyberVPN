"""Use case for creating a new partner referral code."""

import logging
from uuid import UUID

from src.application.services.config_service import ConfigService
from src.application.use_cases.partner_attribution.utils import (
    generate_partner_code,
    generate_public_slug,
    hash_partner_attribution_token,
    normalize_partner_code,
)
from src.config.settings import settings
from src.domain.exceptions import DomainError, MarkupExceedsLimitError
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
        partner_user_id: UUID | None,
        code: str,
        markup_pct: float = 0,
        partner_account_id: UUID | None = None,
    ) -> PartnerCodeModel:
        """Create a partner code for *partner_user_id*.

        If *code* is empty, a random 8-character code is generated.

        Raises:
            MarkupExceedsLimitError: if markup_pct exceeds the configured maximum.
        """
        if not settings.partner_codes_enabled:
            raise DomainError("Partner codes are not enabled for this release")
        if markup_pct < 0:
            raise DomainError("Partner code markup cannot be negative")

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

        normalized_code = normalize_partner_code(code) if code else generate_partner_code()
        public_slug = await self._allocate_public_slug()

        model = PartnerCodeModel(
            partner_account_id=partner_account_id,
            partner_user_id=partner_user_id,
            code=normalized_code,
            code_normalized=normalized_code,
            public_slug=public_slug,
            public_token_hash=hash_partner_attribution_token(public_slug),
            markup_pct=markup_pct,
            lifecycle_status="active",
            approval_status="approved",
            owner_type="affiliate",
            lane_key="creator_affiliate",
            attribution_model="last_eligible_touch",
            attribution_window_seconds=30 * 24 * 60 * 60,
            allowed_channels=["content", "telegram", "storefront"],
            allowed_storefront_ids=["*"],
            allowed_geographies=["*"],
            sub_id_schema={},
        )

        result = await self._partner_repo.create_code(model)

        logger.info(
            "partner_code_created",
            extra={
                "partner_user_id": str(partner_user_id) if partner_user_id else None,
                "code": normalized_code,
                "markup_pct": markup_pct,
                "code_id": str(result.id),
            },
        )

        return result

    async def _allocate_public_slug(self) -> str:
        for _ in range(32):
            candidate = generate_public_slug()
            if await self._partner_repo.get_code_by_public_slug(candidate) is None:
                return candidate
        raise DomainError("Could not allocate unique partner public slug")
