"""Use case for requesting a wallet balance withdrawal."""

import logging
from decimal import Decimal
from uuid import UUID

from src.application.services.config_service import ConfigService
from src.application.services.wallet_service import WalletService
from src.domain.exceptions import WithdrawalBelowMinimumError
from src.infrastructure.database.models.withdrawal_request_model import WithdrawalRequestModel
from src.infrastructure.database.repositories.withdrawal_repo import WithdrawalRepository

logger = logging.getLogger(__name__)


class RequestWithdrawalUseCase:
    """Create a withdrawal request, freezing the requested amount in the wallet.

    The frozen amount prevents the user from spending funds that are
    pending withdrawal. An admin later approves/rejects the request.
    """

    def __init__(
        self,
        wallet_service: WalletService,
        withdrawal_repo: WithdrawalRepository,
        config_service: ConfigService,
    ) -> None:
        self._wallet = wallet_service
        self._withdrawal_repo = withdrawal_repo
        self._config = config_service

    async def execute(
        self,
        user_id: UUID,
        amount: Decimal,
        method: str = "cryptobot",
    ) -> WithdrawalRequestModel:
        """Request a withdrawal of *amount* for *user_id*.

        Raises:
            ValueError: if withdrawals are disabled.
            WithdrawalBelowMinimumError: if amount is below the configured minimum.
            InsufficientWalletBalanceError: if the wallet has insufficient available balance.
        """
        enabled = await self._config.is_withdrawal_enabled()
        if not enabled:
            logger.warning("withdrawal_disabled", extra={"user_id": str(user_id)})
            msg = "Withdrawals are currently disabled"
            raise ValueError(msg)

        min_config = await self._config.get_wallet_min_withdrawal()
        min_amount = Decimal(str(min_config.get("amount", 5.0)))
        if amount < min_amount:
            logger.warning(
                "withdrawal_below_minimum",
                extra={
                    "user_id": str(user_id),
                    "amount": str(amount),
                    "minimum": str(min_amount),
                },
            )
            raise WithdrawalBelowMinimumError(amount=str(amount), minimum=str(min_amount))

        fee_pct = await self._config.get_withdrawal_fee_pct()
        fee = amount * (Decimal(str(fee_pct)) / Decimal("100"))
        net_amount = amount - fee

        # Freeze the full withdrawal amount (including fee) in the wallet
        wallet = await self._wallet.freeze(user_id, amount)

        request_model = WithdrawalRequestModel(
            user_id=user_id,
            wallet_id=wallet.id,
            amount=amount,
            currency="USD",
            method=method,
            status="pending",
        )
        result = await self._withdrawal_repo.create(request_model)

        logger.info(
            "withdrawal_requested",
            extra={
                "user_id": str(user_id),
                "withdrawal_id": str(result.id),
                "amount": str(amount),
                "fee": str(fee),
                "net_amount": str(net_amount),
                "method": method,
                "wallet_id": str(wallet.id),
            },
        )

        return result
