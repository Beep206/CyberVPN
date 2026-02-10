"""Referral commission domain entity."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class ReferralCommission:
    id: UUID
    referrer_user_id: UUID
    referred_user_id: UUID
    payment_id: UUID
    commission_rate: Decimal
    base_amount: Decimal
    commission_amount: Decimal
    currency: str
    created_at: datetime
    wallet_tx_id: UUID | None = None
