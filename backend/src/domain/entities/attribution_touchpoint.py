"""Attribution touchpoint domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class AttributionTouchpoint:
    id: UUID
    touchpoint_type: str
    user_id: UUID | None
    auth_realm_id: UUID | None
    storefront_id: UUID | None
    quote_session_id: UUID | None
    checkout_session_id: UUID | None
    order_id: UUID | None
    partner_code_id: UUID | None
    sale_channel: str | None
    source_host: str | None
    source_path: str | None
    campaign_params: dict[str, Any]
    evidence_payload: dict[str, Any]
    occurred_at: datetime
    created_at: datetime
