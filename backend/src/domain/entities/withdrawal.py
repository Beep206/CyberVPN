"""Withdrawal request domain entity."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.enums import WithdrawalMethod, WithdrawalStatus


@dataclass(frozen=True)
class WithdrawalRequest:
    id: UUID
    user_id: UUID
    wallet_id: UUID
    amount: Decimal
    currency: str
    method: WithdrawalMethod
    status: WithdrawalStatus
    created_at: datetime
    updated_at: datetime
    external_id: str | None = None
    admin_note: str | None = None
    processed_at: datetime | None = None
    processed_by: UUID | None = None
    wallet_tx_id: UUID | None = None
