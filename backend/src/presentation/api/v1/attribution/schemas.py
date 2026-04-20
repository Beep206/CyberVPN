from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domain.enums import AttributionTouchpointType, CommercialOwnerSource, CommercialOwnerType


class RecordAttributionTouchpointRequest(BaseModel):
    touchpoint_type: AttributionTouchpointType
    auth_realm_id: UUID | None = None
    auth_realm_key: str | None = Field(None, min_length=1, max_length=50)
    user_id: UUID | None = None
    storefront_id: UUID | None = None
    quote_session_id: UUID | None = None
    checkout_session_id: UUID | None = None
    order_id: UUID | None = None
    partner_code: str | None = Field(None, max_length=30)
    partner_code_id: UUID | None = None
    sale_channel: str | None = Field(None, min_length=1, max_length=30)
    source_host: str | None = Field(None, max_length=255)
    source_path: str | None = Field(None, max_length=500)
    campaign_params: dict[str, Any] = Field(default_factory=dict)
    evidence_payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None

    @model_validator(mode="after")
    def validate_realm_target(self) -> RecordAttributionTouchpointRequest:
        if self.auth_realm_id and self.auth_realm_key:
            raise ValueError("Specify either auth_realm_id or auth_realm_key, not both")
        return self


class AttributionTouchpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    touchpoint_type: AttributionTouchpointType
    user_id: UUID | None = None
    auth_realm_id: UUID | None = None
    storefront_id: UUID | None = None
    quote_session_id: UUID | None = None
    checkout_session_id: UUID | None = None
    order_id: UUID | None = None
    partner_code_id: UUID | None = None
    sale_channel: str | None = None
    source_host: str | None = None
    source_path: str | None = None
    campaign_params: dict[str, Any] = Field(default_factory=dict)
    evidence_payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime
    created_at: datetime


class OrderAttributionResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    order_id: UUID
    user_id: UUID
    auth_realm_id: UUID
    storefront_id: UUID
    owner_type: CommercialOwnerType
    owner_source: CommercialOwnerSource | None = None
    partner_account_id: UUID | None = None
    partner_code_id: UUID | None = None
    winning_touchpoint_id: UUID | None = None
    winning_binding_id: UUID | None = None
    rule_path: list[str] = Field(default_factory=list)
    evidence_snapshot: dict[str, Any] = Field(default_factory=dict)
    explainability_snapshot: dict[str, Any] = Field(default_factory=dict)
    policy_snapshot: dict[str, Any] = Field(default_factory=dict)
    resolved_at: datetime
    created_at: datetime
