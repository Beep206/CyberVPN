"""PromoCode and PromoCodeUsage domain entities."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.enums import DiscountType


@dataclass(frozen=True)
class PromoCode:
    id: UUID
    code: str
    discount_type: DiscountType
    discount_value: Decimal
    currency: str
    current_uses: int
    is_single_use: bool
    is_active: bool
    created_at: datetime
    max_uses: int | None = None
    plan_ids: list[UUID] | None = None
    min_amount: Decimal | None = None
    expires_at: datetime | None = None
    description: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True)
class PromoCodeUsage:
    id: UUID
    promo_code_id: UUID
    user_id: UUID
    payment_id: UUID
    discount_applied: Decimal
    created_at: datetime
