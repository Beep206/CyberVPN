"""Pydantic schemas for messaging REST APIs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.entities.messaging import (
    BroadcastAudienceType,
    BroadcastCampaignStatus,
    MessagingBodyFormat,
    MessagingConversationCategory,
    MessagingConversationStatus,
    MessagingMessageVisibility,
    MessagingPriority,
    MessagingResponseState,
    MessagingSenderType,
    SiteNotificationDeliveryStatus,
    SiteNotificationSeverity,
    SiteNotificationType,
)


class MessagingWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_message_id: str | None = Field(None, min_length=1, max_length=80)
    body: str = Field(..., min_length=1, max_length=4000)


class MessagingReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    last_read_message_id: UUID | None = None


class MessagingMessageResponse(BaseModel):
    id: UUID
    public_id: str
    conversation_id: UUID
    sender_type: MessagingSenderType
    sender_id: UUID | None = None
    visibility: MessagingMessageVisibility
    body: str
    body_format: MessagingBodyFormat
    client_message_id: str | None = None
    created_at: datetime
    updated_at: datetime


class CustomerMessagingMessageResponse(BaseModel):
    id: UUID
    public_id: str
    conversation_id: UUID
    sender_type: MessagingSenderType
    visibility: MessagingMessageVisibility
    body: str
    created_at: datetime


class MessagingReadStateResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    participant_id: UUID
    last_read_message_id: UUID | None = None
    last_read_at: datetime
    updated_at: datetime


class CustomerConversationSummaryResponse(BaseModel):
    id: UUID
    public_id: str
    status: MessagingConversationStatus
    response_state: MessagingResponseState
    category: MessagingConversationCategory
    priority: MessagingPriority
    subject: str
    unread_count: int = 0
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None = None
    closed_at: datetime | None = None


class CustomerConversationDetailResponse(CustomerConversationSummaryResponse):
    messages: list[CustomerMessagingMessageResponse] = Field(default_factory=list)


class CustomerConversationListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    conversations: list[CustomerConversationSummaryResponse]
    next_cursor: str | None = Field(None, alias="nextCursor")


class AdminConversationSummaryResponse(BaseModel):
    id: UUID
    public_id: str
    customer_account_id: UUID
    status: MessagingConversationStatus
    response_state: MessagingResponseState
    category: MessagingConversationCategory
    priority: MessagingPriority
    subject: str
    created_by_admin_id: UUID | None = None
    assigned_admin_id: UUID | None = None
    related_support_ticket_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None = None
    closed_at: datetime | None = None


class AdminConversationDetailResponse(AdminConversationSummaryResponse):
    messages: list[MessagingMessageResponse] = Field(default_factory=list)
    read_states: list[MessagingReadStateResponse] = Field(default_factory=list)


class AdminConversationListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    conversations: list[AdminConversationSummaryResponse]
    next_cursor: str | None = Field(None, alias="nextCursor")


class MessagingMessageWriteResponse(BaseModel):
    message: MessagingMessageResponse
    conversation: AdminConversationSummaryResponse
    created: bool


class CustomerMessagingMessageWriteResponse(BaseModel):
    message: CustomerMessagingMessageResponse
    conversation: CustomerConversationSummaryResponse
    created: bool


class AdminCreateConversationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: UUID
    subject: str = Field(..., min_length=1, max_length=160)
    category: MessagingConversationCategory = MessagingConversationCategory.OTHER
    priority: MessagingPriority = MessagingPriority.NORMAL
    assigned_admin_id: UUID | None = None
    related_support_ticket_id: UUID | None = None
    initial_message: MessagingWriteRequest


class AdminConversationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assigned_admin_id: UUID | None = None
    priority: MessagingPriority | None = None
    category: MessagingConversationCategory | None = None


class SiteNotificationResponse(BaseModel):
    id: UUID
    delivery_id: UUID
    notification_type: SiteNotificationType
    severity: SiteNotificationSeverity
    title: str
    body: str | None = None
    action_url: str | None = None
    aggregate_type: str | None = None
    aggregate_id: str | None = None
    conversation_id: UUID | None = None
    message_id: UUID | None = None
    status: SiteNotificationDeliveryStatus
    created_at: datetime
    updated_at: datetime
    read_at: datetime | None = None


class SiteNotificationListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    notifications: list[SiteNotificationResponse]
    next_cursor: str | None = Field(None, alias="nextCursor")


class SiteNotificationReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notification_ids: list[UUID] = Field(default_factory=list)
    read_all_before: datetime | None = None


class SiteNotificationReadResponse(BaseModel):
    notifications: list[SiteNotificationResponse]


class MessagingUnreadCountsResponse(BaseModel):
    conversations: int
    notifications: int


class MessagingRealtimeSyncResponse(BaseModel):
    cursor: str
    conversations: list[CustomerConversationSummaryResponse]
    messages: list[CustomerMessagingMessageResponse] = Field(default_factory=list)
    notifications: list[SiteNotificationResponse]
    unread_counts: MessagingUnreadCountsResponse


class MessagingRealtimeTicketResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ticket: str
    expires_in: int = Field(30, alias="expiresIn")


class BroadcastCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=160)
    audience_type: BroadcastAudienceType
    audience_filter: dict[str, object] = Field(default_factory=dict)
    title: str = Field(..., min_length=1, max_length=160)
    body: str = Field(..., min_length=1, max_length=4000)
    action_url: str | None = Field(None, max_length=500)
    scheduled_at: datetime | None = None


class BroadcastCampaignResponse(BaseModel):
    id: UUID
    public_id: str
    name: str
    status: BroadcastCampaignStatus
    audience_type: BroadcastAudienceType
    audience_filter: dict[str, object]
    title: str
    body: str
    action_url: str | None = None
    scheduled_at: datetime | None = None
    created_by_admin_id: UUID
    created_at: datetime
    updated_at: datetime
