"""Use case for processing a partner earning when a client payment occurs."""

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.application.services.config_service import ConfigService
from src.application.services.wallet_service import WalletService
from src.domain.enums import WalletTxReason
from src.domain.exceptions import PartnerCodeNotFoundError
from src.infrastructure.database.models.partner_model import PartnerEarningModel
from src.infrastructure.database.repositories.partner_repo import PartnerRepository

logger = logging.getLogger(__name__)


class ProcessPartnerEarningUseCase:
    """Calculate and credit a partner earning from a client payment.

    Computes markup + tiered commission, credits the partner wallet,
    and records the earning in the ledger.
    """

    def __init__(
        self,
        partner_repo: PartnerRepository,
        wallet_service: WalletService,
        config_service: ConfigService,
    ) -> None:
        self._partner_repo = partner_repo
        self._wallet = wallet_service
        self._config = config_service

    async def execute(
        self,
        partner_user_id: UUID,
        client_user_id: UUID,
        payment_id: UUID,
        partner_code_id: UUID,
        base_price: Decimal,
    ) -> PartnerEarningModel:
        """Process a partner earning for a client payment.

        Raises:
            PartnerCodeNotFoundError: if the partner code does not exist.
        """
        code = await self._partner_repo.get_code_by_id(partner_code_id)
        if code is None:
            raise PartnerCodeNotFoundError(str(partner_code_id))

        # Calculate markup
        markup_pct = Decimal(str(code.markup_pct))
        markup_amount = base_price * (markup_pct / Decimal("100"))

        # Determine commission from tier
        tiers = await self._config.get_partner_tiers()
        client_count = await self._partner_repo.count_clients(partner_user_id)
        commission_pct = self._resolve_commission_pct(client_count, tiers)

        commission_amount = base_price * (Decimal(str(commission_pct)) / Decimal("100"))
        total_earning = markup_amount + commission_amount

        # Credit partner wallet
        tx = await self._wallet.credit(
            user_id=partner_user_id,
            amount=total_earning,
            reason=WalletTxReason.PARTNER_EARNING,
            description=(
                f"Partner earning: markup={markup_amount}, commission={commission_amount} (payment={payment_id})"
            ),
            reference_type="payment",
            reference_id=payment_id,
        )

        # Record earning in ledger
        earning = PartnerEarningModel(
            partner_user_id=partner_user_id,
            client_user_id=client_user_id,
            payment_id=payment_id,
            partner_code_id=partner_code_id,
            base_price=base_price,
            markup_amount=markup_amount,
            commission_pct=commission_pct,
            commission_amount=commission_amount,
            total_earning=total_earning,
            wallet_tx_id=tx.id,
        )
        result = await self._partner_repo.record_earning(earning)

        logger.info(
            "partner_earning_processed",
            extra={
                "partner_user_id": str(partner_user_id),
                "client_user_id": str(client_user_id),
                "payment_id": str(payment_id),
                "base_price": str(base_price),
                "markup_amount": str(markup_amount),
                "commission_pct": commission_pct,
                "commission_amount": str(commission_amount),
                "total_earning": str(total_earning),
                "wallet_tx_id": str(tx.id),
            },
        )

        return result

    @staticmethod
    def _resolve_commission_pct(client_count: int, tiers: list[dict[str, Any]]) -> float:
        """Find commission percentage from tier configuration based on client count."""
        if not tiers:
            return 0.0

        sorted_tiers = sorted(tiers, key=lambda t: t.get("min_clients", 0))
        commission: float = 0.0

        for tier in sorted_tiers:
            if client_count >= tier.get("min_clients", 0):
                commission = float(tier.get("commission_pct", 0))

        return commission
