"""Pydantic schemas for support ticket APIs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.entities.support_ticket import (
    SupportActorType,
    SupportMessageVisibility,
    SupportTicketCategory,
    SupportTicketEventType,
    SupportTicketOwnerType,
    SupportTicketPriority,
    SupportTicketSource,
    SupportTicketStatus,
)


class SupportTicketCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: SupportTicketCategory
    subject: str = Field(..., min_length=3, max_length=120)
    message: str = Field(..., min_length=1, max_length=4000)
    priority: SupportTicketPriority = SupportTicketPriority.NORMAL


class PartnerSupportTicketCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: SupportTicketCategory
    subject: str = Field(..., min_length=3, max_length=120)
    message: str = Field(..., min_length=1, max_length=4000)
    priority: SupportTicketPriority = SupportTicketPriority.NORMAL


class SupportTicketReplyRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class AdminSupportTicketUpdateRequest(BaseModel):
    status: SupportTicketStatus | None = None
    category: SupportTicketCategory | None = None
    priority: SupportTicketPriority | None = None
    assigned_admin_id: UUID | None = None


class SupportTicketMessageResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    author_type: SupportActorType
    author_id: UUID | None = None
    visibility: SupportMessageVisibility
    body: str
    created_at: datetime


class SupportTicketEventResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    actor_type: SupportActorType
    actor_id: UUID | None = None
    event_type: SupportTicketEventType
    from_value: str | None = None
    to_value: str | None = None
    audit_summary: str
    created_at: datetime


class SupportTicketSummaryResponse(BaseModel):
    id: UUID
    public_id: str
    owner_type: SupportTicketOwnerType
    customer_account_id: UUID | None = None
    partner_workspace_id: UUID | None = None
    source: SupportTicketSource
    status: SupportTicketStatus
    category: SupportTicketCategory
    priority: SupportTicketPriority
    subject: str
    last_message_preview: str
    assigned_admin_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    last_customer_message_at: datetime | None = None
    last_support_message_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None


class SupportTicketDetailResponse(SupportTicketSummaryResponse):
    messages: list[SupportTicketMessageResponse] = Field(default_factory=list)
    events: list[SupportTicketEventResponse] = Field(default_factory=list)


class SupportTicketListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tickets: list[SupportTicketSummaryResponse]
    next_cursor: str | None = Field(None, alias="nextCursor")


class PublicSupportTicketMessageResponse(BaseModel):
    author_label: str
    body: str
    created_at: datetime


class PublicSupportTicketEventResponse(BaseModel):
    actor_label: str
    event_type: SupportTicketEventType
    from_value: str | None = None
    to_value: str | None = None
    audit_summary: str
    created_at: datetime


class PublicSupportTicketSummaryResponse(BaseModel):
    public_id: str
    status: SupportTicketStatus
    category: SupportTicketCategory
    priority: SupportTicketPriority
    subject: str
    last_message_preview: str
    created_at: datetime
    updated_at: datetime
    last_customer_message_at: datetime | None = None
    last_support_message_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None


class PublicSupportTicketDetailResponse(PublicSupportTicketSummaryResponse):
    messages: list[PublicSupportTicketMessageResponse] = Field(default_factory=list)
    events: list[PublicSupportTicketEventResponse] = Field(default_factory=list)


class PublicSupportTicketListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tickets: list[PublicSupportTicketSummaryResponse]
    next_cursor: str | None = Field(None, alias="nextCursor")
