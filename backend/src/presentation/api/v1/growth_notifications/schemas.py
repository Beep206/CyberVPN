"""Schemas for customer growth notification feed."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GrowthNotificationFeedItemResponse(BaseModel):
    id: str
    kind: str
    tone: str
    route_slug: str = "/referral"
    title: str
    message: str
    notes: list[str] = Field(default_factory=list)
    action_required: bool = False
    unread: bool = True
    created_at: datetime
    archived_at: datetime | None = None
    source_kind: str | None = None
    source_id: str | None = None


class GrowthNotificationCountersResponse(BaseModel):
    total_notifications: int = 0
    unread_notifications: int = 0
    action_required_notifications: int = 0


class GrowthNotificationReadStateResponse(BaseModel):
    notification_id: str
    read_at: datetime | None = None
    archived_at: datetime | None = None


class GrowthNotificationPreferencesResponse(BaseModel):
    growth_in_app_invites: bool = True
    growth_email_invites: bool = False
    growth_telegram_invites: bool = True
    growth_in_app_referral_rewards: bool = True
    growth_email_referral_rewards: bool = True
    growth_telegram_referral_rewards: bool = True
    growth_in_app_gifts: bool = True
    growth_email_gifts: bool = True
    growth_telegram_gifts: bool = True
    growth_in_app_admin_updates: bool = True
    growth_email_admin_updates: bool = True
    growth_telegram_admin_updates: bool = True


class GrowthNotificationPreferencesUpdateRequest(BaseModel):
    growth_in_app_invites: bool | None = None
    growth_email_invites: bool | None = None
    growth_telegram_invites: bool | None = None
    growth_in_app_referral_rewards: bool | None = None
    growth_email_referral_rewards: bool | None = None
    growth_telegram_referral_rewards: bool | None = None
    growth_in_app_gifts: bool | None = None
    growth_email_gifts: bool | None = None
    growth_telegram_gifts: bool | None = None
    growth_in_app_admin_updates: bool | None = None
    growth_email_admin_updates: bool | None = None
    growth_telegram_admin_updates: bool | None = None


class GrowthNotificationDeliveryEventResponse(BaseModel):
    event_type: str
    occurred_at: datetime | None = None
    summary: str


class GrowthNotificationRepairTargetResponse(BaseModel):
    kind: str
    summary: str


class GrowthNotificationDeliveryDetailResponse(BaseModel):
    delivery_id: str
    delivery_channel: str
    delivery_status: str
    troubleshooting_state: str
    customer_message_key: str
    customer_summary: str
    recovery_allowed: bool = False
    support_required: bool = False
    repair_target: GrowthNotificationRepairTargetResponse | None = None
    planned_at: datetime
    delivered_at: datetime | None = None
    events: list[GrowthNotificationDeliveryEventResponse] = Field(default_factory=list)


class GrowthNotificationSupportHandoffResponse(BaseModel):
    reference_code: str
    troubleshooting_summary: str
    copy_text: str
    suggested_escalation_channel: str
    contact_subject: str
    contact_body: str


class GrowthNotificationDetailResponse(BaseModel):
    notification: GrowthNotificationFeedItemResponse
    deliveries: list[GrowthNotificationDeliveryDetailResponse] = Field(default_factory=list)
    support_handoff: GrowthNotificationSupportHandoffResponse


class GrowthNotificationRecoveryRequest(BaseModel):
    delivery_channel: str


class GrowthNotificationSupportEscalationRequest(BaseModel):
    delivery_channel: str | None = None
    escalation_channel: str = Field(
        default="contact_form",
        pattern="^(contact_form|support_email|telegram_support)$",
    )
