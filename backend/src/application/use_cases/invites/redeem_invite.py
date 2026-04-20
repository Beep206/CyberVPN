"""Use case for redeeming an invite code."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from src.application.use_cases.growth_rewards import CreateGrowthRewardAllocationUseCase
from src.domain.exceptions import (
    InviteCodeAlreadyUsedError,
    InviteCodeExpiredError,
    InviteCodeNotFoundError,
)
from src.domain.enums import GrowthRewardType
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository

logger = logging.getLogger(__name__)


class RedeemInviteUseCase:
    """Validate and redeem an invite code for a given user.

    Returns the redeemed invite so the caller can read ``free_days``
    and provision the subscription accordingly.
    """

    def __init__(
        self,
        invite_repo: InviteCodeRepository,
        growth_rewards: CreateGrowthRewardAllocationUseCase | None = None,
    ) -> None:
        self._invite_repo = invite_repo
        self._growth_rewards = growth_rewards

    async def execute(self, code: str, user_id: UUID) -> InviteCodeModel:
        """Redeem *code* on behalf of *user_id*.

        Raises:
            InviteCodeNotFoundError: code does not exist or is unavailable.
            InviteCodeAlreadyUsedError: code has already been redeemed.
            InviteCodeExpiredError: code has passed its expiry date.
        """
        invite = await self._invite_repo.get_by_code(code)

        if invite is None:
            logger.warning("invite_redeem_not_found", extra={"code": code, "user_id": str(user_id)})
            raise InviteCodeNotFoundError(code)

        if invite.is_used:
            logger.warning(
                "invite_redeem_already_used",
                extra={"code": code, "user_id": str(user_id)},
            )
            raise InviteCodeAlreadyUsedError(code)

        if invite.expires_at is not None and invite.expires_at < datetime.now(UTC):
            logger.warning(
                "invite_redeem_expired",
                extra={"code": code, "expires_at": str(invite.expires_at)},
            )
            raise InviteCodeExpiredError(code)

        result = await self._invite_repo.mark_used(invite.id, user_id)

        if self._growth_rewards is not None:
            await self._growth_rewards.execute(
                reward_type=GrowthRewardType.BONUS_DAYS.value,
                beneficiary_user_id=user_id,
                invite_code_id=invite.id,
                quantity=invite.free_days,
                unit="days",
                source_key=f"invite:{invite.id}:bonus_days:{user_id}",
                reward_payload={
                    "code": code,
                    "free_days": invite.free_days,
                    "source": invite.source,
                    "owner_user_id": str(invite.owner_user_id),
                },
                commit=False,
            )

        logger.info(
            "invite_redeemed",
            extra={
                "code": code,
                "invite_id": str(invite.id),
                "user_id": str(user_id),
                "free_days": invite.free_days,
            },
        )

        # mark_used returns the updated model; fall back to the original if
        # the repo unexpectedly returns None (defensive).
        return result if result is not None else invite
