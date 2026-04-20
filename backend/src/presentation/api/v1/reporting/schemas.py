from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OutboxPublicationResponse(BaseModel):
    id: UUID
    outbox_event_id: UUID
    consumer_key: str
    publication_status: str
    attempts: int
    lease_owner: str | None
    leased_until: datetime | None
    next_attempt_at: datetime
    submitted_at: datetime | None
    published_at: datetime | None
    last_error: str | None
    publication_payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class OutboxEventResponse(BaseModel):
    id: UUID
    event_key: str
    event_name: str
    event_family: str
    aggregate_type: str
    aggregate_id: str
    partition_key: str
    schema_version: int
    event_status: str
    event_payload: dict[str, Any]
    actor_context: dict[str, Any]
    source_context: dict[str, Any]
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime
    publications: list[OutboxPublicationResponse]


class ClaimOutboxPublicationsRequest(BaseModel):
    consumer_key: str = Field(min_length=1, max_length=80)
    lease_owner: str = Field(min_length=1, max_length=120)
    batch_size: int = Field(default=20, ge=1, le=200)
    lease_seconds: int = Field(default=60, ge=5, le=3600)


class ClaimOutboxPublicationsResponse(BaseModel):
    claimed_publications: list[OutboxPublicationResponse]


class MarkOutboxPublicationSubmittedRequest(BaseModel):
    lease_owner: str = Field(min_length=1, max_length=120)


class MarkOutboxPublicationPublishedRequest(BaseModel):
    lease_owner: str = Field(min_length=1, max_length=120)
    publication_payload: dict[str, Any] | None = None


class MarkOutboxPublicationFailedRequest(BaseModel):
    lease_owner: str = Field(min_length=1, max_length=120)
    retry_after_seconds: int = Field(default=60, ge=5, le=86400)
    error_message: str = Field(min_length=1, max_length=4000)


class PartnerReportingDeliveryLogResponse(BaseModel):
    id: str
    channel: str
    status: str
    destination: str
    last_attempt_at: datetime
    notes: list[str] = Field(default_factory=list)


class PartnerReportingPostbackReadinessResponse(BaseModel):
    status: str
    delivery_status: str
    scope_label: str
    credential_id: UUID | None = None
    notes: list[str] = Field(default_factory=list)


class PartnerReportingApiSnapshotResponse(BaseModel):
    workspace_id: UUID
    workspace_key: str
    generated_at: datetime
    partner_reporting_row: dict[str, Any]
    consumer_health_views: list[dict[str, Any]] = Field(default_factory=list)
    delivery_logs: list[PartnerReportingDeliveryLogResponse] = Field(default_factory=list)
    postback_readiness: PartnerReportingPostbackReadinessResponse
