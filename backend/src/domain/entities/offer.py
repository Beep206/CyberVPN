from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.enums import PolicyVersionStatus


@dataclass(frozen=True)
class Offer:
    uuid: UUID
    offer_key: str
    display_name: str
    subscription_plan_id: UUID
    included_addon_codes: list[str]
    sale_channels: list[str]
    visibility_rules: dict[str, Any]
    invite_bundle: dict[str, Any]
    trial_eligible: bool
    gift_eligible: bool
    referral_eligible: bool
    renewal_incentives: dict[str, Any]
    version_status: PolicyVersionStatus | str
    effective_from: datetime
    effective_to: datetime | None
    is_active: bool

    def __post_init__(self) -> None:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("Offer effective_to must be greater than effective_from")


@dataclass(frozen=True)
class PricebookEntry:
    uuid: UUID
    offer_id: UUID
    visible_price: float
    compare_at_price: float | None
    included_addon_codes: list[str]
    display_order: int


@dataclass(frozen=True)
class Pricebook:
    uuid: UUID
    pricebook_key: str
    display_name: str
    storefront_id: UUID
    merchant_profile_id: UUID | None
    currency_code: str
    region_code: str | None
    discount_rules: dict[str, Any]
    renewal_pricing_policy: dict[str, Any]
    entries: list[PricebookEntry]
    version_status: PolicyVersionStatus | str
    effective_from: datetime
    effective_to: datetime | None
    is_active: bool

    def __post_init__(self) -> None:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("Pricebook effective_to must be greater than effective_from")
        if not self.entries:
            raise ValueError("Pricebook must contain at least one entry")
        offer_ids = [entry.offer_id for entry in self.entries]
        if len(set(offer_ids)) != len(offer_ids):
            raise ValueError("Pricebook cannot contain duplicate offer entries")
