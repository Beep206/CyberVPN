"""Use case for admin-initiated wallet top-up."""

import logging
from decimal import Decimal
from uuid import UUID

from src.application.services.wallet_service import WalletService
from src.domain.enums import WalletTxReason
from src.infrastructure.database.models.wallet_model import WalletTransactionModel

logger = logging.getLogger(__name__)


class AdminTopupUseCase:
    """Admin-only action to credit a user's wallet with funds.

    Creates a CREDIT transaction with reason ADMIN_TOPUP.
    """

    def __init__(self, wallet_service: WalletService) -> None:
        self._wallet = wallet_service

    async def execute(
        self,
        user_id: UUID,
        amount: Decimal,
        description: str | None = None,
    ) -> WalletTransactionModel:
        """Top up *user_id* wallet by *amount*.

        Returns the created wallet transaction.
        """
        tx = await self._wallet.credit(
            user_id=user_id,
            amount=amount,
            reason=WalletTxReason.ADMIN_TOPUP,
            description=description,
        )

        logger.info(
            "admin_wallet_topup",
            extra={
                "user_id": str(user_id),
                "amount": str(amount),
                "tx_id": str(tx.id),
                "description": description,
            },
        )

        return tx
