"""Admin approve/reject withdrawal use case."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from src.application.services.wallet_service import WalletService
from src.domain.enums import WalletTxReason
from src.infrastructure.database.models.withdrawal_request_model import WithdrawalRequestModel
from src.infrastructure.database.repositories.withdrawal_repo import WithdrawalRepository


class ProcessWithdrawalUseCase:
    """Admin approves or rejects a pending withdrawal request."""

    def __init__(self, withdrawal_repo: WithdrawalRepository, wallet_service: WalletService) -> None:
        self._withdrawal_repo = withdrawal_repo
        self._wallet_service = wallet_service

    async def approve(
        self, withdrawal_id: UUID, admin_id: UUID, admin_note: str | None = None
    ) -> WithdrawalRequestModel:
        wd = await self._withdrawal_repo.get_by_id(withdrawal_id)
        if wd is None or wd.status != "pending":
            msg = f"Withdrawal {withdrawal_id} not found or not pending"
            raise ValueError(msg)

        # Debit the frozen amount from wallet
        tx = await self._wallet_service.debit(
            user_id=wd.user_id,
            amount=Decimal(str(wd.amount)),
            reason=WalletTxReason.WITHDRAWAL,
            description=f"Withdrawal approved #{withdrawal_id}",
            reference_type="withdrawal",
            reference_id=withdrawal_id,
        )

        # Unfreeze the same amount (was frozen at request time)
        await self._wallet_service.unfreeze(wd.user_id, Decimal(str(wd.amount)))

        wd.status = "completed"
        wd.processed_at = datetime.now(UTC)
        wd.processed_by = admin_id
        wd.wallet_tx_id = tx.id
        if admin_note:
            wd.admin_note = admin_note

        return await self._withdrawal_repo.update(wd)

    async def reject(
        self, withdrawal_id: UUID, admin_id: UUID, admin_note: str | None = None
    ) -> WithdrawalRequestModel:
        wd = await self._withdrawal_repo.get_by_id(withdrawal_id)
        if wd is None or wd.status != "pending":
            msg = f"Withdrawal {withdrawal_id} not found or not pending"
            raise ValueError(msg)

        # Unfreeze the amount back to available balance
        await self._wallet_service.unfreeze(wd.user_id, Decimal(str(wd.amount)))

        wd.status = "failed"
        wd.processed_at = datetime.now(UTC)
        wd.processed_by = admin_id
        if admin_note:
            wd.admin_note = admin_note

        return await self._withdrawal_repo.update(wd)
