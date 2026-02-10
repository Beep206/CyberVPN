"""Partner code and partner earning domain entities."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class PartnerCode:
    id: UUID
    code: str
    partner_user_id: UUID
    markup_pct: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PartnerEarning:
    id: UUID
    partner_user_id: UUID
    client_user_id: UUID
    payment_id: UUID
    partner_code_id: UUID
    base_price: Decimal
    markup_amount: Decimal
    commission_pct: Decimal
    commission_amount: Decimal
    total_earning: Decimal
    currency: str
    created_at: datetime
    wallet_tx_id: UUID | None = None
