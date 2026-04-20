"""Canonical renewal-order lineage and ownership entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class RenewalOrder:
    id: UUID
    order_id: UUID
    initial_order_id: UUID
    prior_order_id: UUID
    user_id: UUID
    auth_realm_id: UUID
    storefront_id: UUID
    originating_attribution_result_id: UUID | None
    winning_binding_id: UUID | None
    renewal_sequence_number: int
    renewal_mode: str
    provenance_owner_type: str
    provenance_owner_source: str | None
    provenance_partner_account_id: UUID | None
    provenance_partner_code_id: UUID | None
    effective_owner_type: str
    effective_owner_source: str | None
    effective_partner_account_id: UUID | None
    effective_partner_code_id: UUID | None
    payout_eligible: bool
    payout_block_reason_codes: list[str]
    lineage_snapshot: dict[str, Any]
    explainability_snapshot: dict[str, Any]
    policy_snapshot: dict[str, Any]
    resolved_at: datetime
    created_at: datetime
    updated_at: datetime
