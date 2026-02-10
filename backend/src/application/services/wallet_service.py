"""Application service for wallet operations — credit, debit, freeze, unfreeze."""

from decimal import Decimal
from uuid import UUID

from src.domain.enums import WalletTxReason
from src.domain.exceptions import InsufficientWalletBalanceError, WalletNotFoundError
from src.infrastructure.database.models.wallet_model import (
    WalletModel,
    WalletTransactionModel,
)
from src.infrastructure.database.repositories.wallet_repo import WalletRepository


class WalletService:
    """High-level wallet operations with domain error translation."""

    def __init__(self, wallet_repo: WalletRepository) -> None:
        self._repo = wallet_repo

    async def get_or_create(self, user_id: UUID) -> WalletModel:
        return await self._repo.get_or_create(user_id)

    async def get_balance(self, user_id: UUID) -> WalletModel:
        wallet = await self._repo.get_by_user_id(user_id)
        if wallet is None:
            return await self._repo.get_or_create(user_id)
        return wallet

    async def credit(
        self,
        user_id: UUID,
        amount: Decimal,
        reason: WalletTxReason,
        description: str | None = None,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
    ) -> WalletTransactionModel:
        try:
            return await self._repo.credit(
                user_id=user_id,
                amount=amount,
                reason=reason,
                description=description,
                reference_type=reference_type,
                reference_id=reference_id,
            )
        except ValueError as e:
            raise WalletNotFoundError(identifier=str(e)) from e

    async def debit(
        self,
        user_id: UUID,
        amount: Decimal,
        reason: WalletTxReason,
        description: str | None = None,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
    ) -> WalletTransactionModel:
        try:
            return await self._repo.debit(
                user_id=user_id,
                amount=amount,
                reason=reason,
                description=description,
                reference_type=reference_type,
                reference_id=reference_id,
            )
        except ValueError as e:
            msg = str(e)
            if "Insufficient" in msg:
                raise InsufficientWalletBalanceError() from e
            raise WalletNotFoundError(identifier=msg) from e

    async def freeze(self, user_id: UUID, amount: Decimal) -> WalletModel:
        try:
            return await self._repo.freeze(user_id, amount)
        except ValueError as e:
            msg = str(e)
            if "Insufficient" in msg:
                raise InsufficientWalletBalanceError() from e
            raise WalletNotFoundError(identifier=msg) from e

    async def unfreeze(self, user_id: UUID, amount: Decimal) -> WalletModel:
        try:
            return await self._repo.unfreeze(user_id, amount)
        except ValueError as e:
            raise WalletNotFoundError(identifier=str(e)) from e

    async def get_transactions(
        self, user_id: UUID, offset: int = 0, limit: int = 50
    ) -> list[WalletTransactionModel]:
        return await self._repo.get_transactions(user_id, offset=offset, limit=limit)
