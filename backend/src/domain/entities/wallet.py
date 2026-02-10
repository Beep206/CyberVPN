"""Wallet and wallet transaction domain entities."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.enums import WalletTxReason, WalletTxType


@dataclass(frozen=True)
class Wallet:
    id: UUID
    user_id: UUID
    balance: Decimal
    currency: str
    frozen: Decimal
    created_at: datetime
    updated_at: datetime

    @property
    def available_balance(self) -> Decimal:
        """Balance minus frozen amount — what the user can actually spend."""
        return self.balance - self.frozen


@dataclass(frozen=True)
class WalletTransaction:
    id: UUID
    wallet_id: UUID
    user_id: UUID
    type: WalletTxType
    amount: Decimal
    currency: str
    balance_after: Decimal
    reason: WalletTxReason
    created_at: datetime
    reference_type: str | None = None
    reference_id: UUID | None = None
    description: str | None = None
