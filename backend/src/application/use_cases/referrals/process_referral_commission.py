"""Use case: calculate and credit a referral commission for a payment."""

import logging
from decimal import Decimal
from uuid import UUID

from src.application.services.config_service import ConfigService
from src.application.services.wallet_service import WalletService
from src.domain.enums import ReferralDurationMode, WalletTxReason
from src.infrastructure.database.models.referral_commission_model import (
    ReferralCommissionModel,
)
from src.infrastructure.database.repositories.referral_commission_repo import (
    ReferralCommissionRepository,
)

logger = logging.getLogger(__name__)


class ProcessReferralCommissionUseCase:
    def __init__(
        self,
        commission_repo: ReferralCommissionRepository,
        wallet_service: WalletService,
        config_service: ConfigService,
    ) -> None:
        self._commission_repo = commission_repo
        self._wallet_service = wallet_service
        self._config_service = config_service

    async def execute(
        self,
        referrer_user_id: UUID,
        referred_user_id: UUID,
        payment_id: UUID,
        base_amount: Decimal,
    ) -> ReferralCommissionModel | None:
        """Process a referral commission if the referrer is eligible.

        Returns the created ``ReferralCommissionModel`` on success,
        or ``None`` when the referral programme is disabled or the
        referrer is not eligible for this particular payment.
        """
        if not await self._config_service.is_referral_enabled():
            logger.info("Referral programme disabled, skipping commission")
            return None

        commission_rate = await self._config_service.get_referral_commission_rate()
        duration_cfg = await self._config_service.get_referral_duration_mode()
        mode = duration_cfg.get("mode", ReferralDurationMode.INDEFINITE)

        if not await self._check_eligibility(mode, duration_cfg, referrer_user_id, referred_user_id):
            logger.info(
                "Referrer %s not eligible for commission on payment %s (mode=%s)",
                referrer_user_id,
                payment_id,
                mode,
            )
            return None

        commission_amount = base_amount * Decimal(str(commission_rate))

        tx = await self._wallet_service.credit(
            user_id=referrer_user_id,
            amount=commission_amount,
            reason=WalletTxReason.REFERRAL_COMMISSION,
            description=f"Referral commission from payment {payment_id}",
            reference_type="payment",
            reference_id=payment_id,
        )

        commission = await self._commission_repo.create(
            ReferralCommissionModel(
                referrer_user_id=referrer_user_id,
                referred_user_id=referred_user_id,
                payment_id=payment_id,
                commission_rate=commission_rate,
                base_amount=base_amount,
                commission_amount=commission_amount,
                wallet_tx_id=tx.id,
            )
        )

        logger.info(
            "Credited referral commission %s to user %s (amount=%s, payment=%s)",
            commission.id,
            referrer_user_id,
            commission_amount,
            payment_id,
        )
        return commission

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _check_eligibility(
        self,
        mode: str,
        duration_cfg: dict,
        referrer_user_id: UUID,
        referred_user_id: UUID,
    ) -> bool:
        """Determine whether the referrer is eligible for a commission."""
        if mode == ReferralDurationMode.INDEFINITE:
            return True

        existing_count = await self._commission_repo.count_by_referrer_for_referred(referrer_user_id, referred_user_id)

        if mode == ReferralDurationMode.FIRST_PAYMENT_ONLY:
            return existing_count == 0

        if mode == ReferralDurationMode.PAYMENT_COUNT:
            max_count = int(duration_cfg.get("count", 1))
            return existing_count < max_count

        # TIME_LIMITED and any unknown modes: allow for now
        return True
