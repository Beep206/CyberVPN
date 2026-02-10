"""Abstract repository interface for wallet operations."""

from abc import ABC, abstractmethod
from decimal import Decimal
from uuid import UUID

from src.domain.entities.wallet import Wallet, WalletTransaction
from src.domain.enums import WalletTxReason


class WalletRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Wallet | None: ...

    @abstractmethod
    async def get_or_create(self, user_id: UUID) -> Wallet: ...

    @abstractmethod
    async def credit(
        self,
        user_id: UUID,
        amount: Decimal,
        reason: WalletTxReason,
        description: str | None = None,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
    ) -> WalletTransaction: ...

    @abstractmethod
    async def debit(
        self,
        user_id: UUID,
        amount: Decimal,
        reason: WalletTxReason,
        description: str | None = None,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
    ) -> WalletTransaction: ...

    @abstractmethod
    async def freeze(self, user_id: UUID, amount: Decimal) -> Wallet: ...

    @abstractmethod
    async def unfreeze(self, user_id: UUID, amount: Decimal) -> Wallet: ...

    @abstractmethod
    async def get_transactions(
        self, user_id: UUID, offset: int = 0, limit: int = 50
    ) -> list[WalletTransaction]: ...
