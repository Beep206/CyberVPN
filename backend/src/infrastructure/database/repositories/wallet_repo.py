"""Infrastructure repository for wallets and wallet_transactions tables."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import WalletTxReason, WalletTxType
from src.infrastructure.database.models.wallet_model import (
    WalletModel,
    WalletTransactionModel,
)


class WalletRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: UUID) -> WalletModel | None:
        result = await self._session.execute(
            select(WalletModel).where(WalletModel.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id_for_update(self, user_id: UUID) -> WalletModel | None:
        """SELECT ... FOR UPDATE to prevent concurrent wallet modifications."""
        result = await self._session.execute(
            select(WalletModel)
            .where(WalletModel.user_id == user_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: UUID) -> WalletModel:
        wallet = await self.get_by_user_id(user_id)
        if wallet is None:
            wallet = WalletModel(user_id=user_id)
            self._session.add(wallet)
            await self._session.flush()
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
        wallet = await self.get_by_user_id_for_update(user_id)
        if wallet is None:
            wallet = WalletModel(user_id=user_id)
            self._session.add(wallet)
            await self._session.flush()

        wallet.balance = wallet.balance + amount
        new_balance = wallet.balance

        tx = WalletTransactionModel(
            wallet_id=wallet.id,
            user_id=user_id,
            type=WalletTxType.CREDIT,
            amount=amount,
            balance_after=new_balance,
            reason=reason,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        self._session.add(tx)
        await self._session.flush()
        return tx

    async def debit(
        self,
        user_id: UUID,
        amount: Decimal,
        reason: WalletTxReason,
        description: str | None = None,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
    ) -> WalletTransactionModel:
        wallet = await self.get_by_user_id_for_update(user_id)
        if wallet is None:
            msg = f"Wallet not found for user {user_id}"
            raise ValueError(msg)

        available = wallet.balance - wallet.frozen
        if available < amount:
            msg = f"Insufficient balance: available={available}, requested={amount}"
            raise ValueError(msg)

        wallet.balance = wallet.balance - amount
        new_balance = wallet.balance

        tx = WalletTransactionModel(
            wallet_id=wallet.id,
            user_id=user_id,
            type=WalletTxType.DEBIT,
            amount=amount,
            balance_after=new_balance,
            reason=reason,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        self._session.add(tx)
        await self._session.flush()
        return tx

    async def freeze(self, user_id: UUID, amount: Decimal) -> WalletModel:
        wallet = await self.get_by_user_id_for_update(user_id)
        if wallet is None:
            msg = f"Wallet not found for user {user_id}"
            raise ValueError(msg)

        available = wallet.balance - wallet.frozen
        if available < amount:
            msg = f"Insufficient balance to freeze: available={available}, requested={amount}"
            raise ValueError(msg)

        wallet.frozen = wallet.frozen + amount
        await self._session.flush()
        return wallet

    async def unfreeze(self, user_id: UUID, amount: Decimal) -> WalletModel:
        wallet = await self.get_by_user_id_for_update(user_id)
        if wallet is None:
            msg = f"Wallet not found for user {user_id}"
            raise ValueError(msg)

        if wallet.frozen < amount:
            msg = f"Cannot unfreeze more than frozen: frozen={wallet.frozen}, requested={amount}"
            raise ValueError(msg)

        wallet.frozen = wallet.frozen - amount
        await self._session.flush()
        return wallet

    async def get_transactions(
        self, user_id: UUID, offset: int = 0, limit: int = 50
    ) -> list[WalletTransactionModel]:
        result = await self._session.execute(
            select(WalletTransactionModel)
            .where(WalletTransactionModel.user_id == user_id)
            .order_by(WalletTransactionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_transaction_by_id(self, tx_id: UUID) -> WalletTransactionModel | None:
        return await self._session.get(WalletTransactionModel, tx_id)
