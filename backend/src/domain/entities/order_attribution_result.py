"""Immutable order attribution result domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class OrderAttributionResult:
    id: UUID
    order_id: UUID
    user_id: UUID
    auth_realm_id: UUID
    storefront_id: UUID
    owner_type: str
    owner_source: str | None
    partner_account_id: UUID | None
    partner_code_id: UUID | None
    winning_touchpoint_id: UUID | None
    winning_binding_id: UUID | None
    rule_path: list[str]
    evidence_snapshot: dict[str, Any]
    explainability_snapshot: dict[str, Any]
    policy_snapshot: dict[str, Any]
    resolved_at: datetime
    created_at: datetime
