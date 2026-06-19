from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PrivacyRequestTypeLiteral = Literal["account_deletion", "data_export"]
PrivacyRequestStatusLiteral = Literal[
    "submitted",
    "identity_verification",
    "pending_decision",
    "approved",
    "scheduled",
    "fulfilled",
    "denied",
    "canceled",
    "failed",
]


class PrivacyRequestCreateRequest(BaseModel):
    request_type: PrivacyRequestTypeLiteral
    reason_code: str | None = Field(default=None, max_length=64)
    reason: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=700)
    feedback: str | None = Field(default=None, max_length=700)
    locale: str | None = Field(default=None, max_length=10)


class PrivacyRequestAcceptedResponse(BaseModel):
    privacy_request_reference: str
    ticket_reference: str
    request_type: PrivacyRequestTypeLiteral
    status: PrivacyRequestStatusLiteral
    message: str
    submitted_at: datetime
    manual_fulfillment_target_days: int
    existing: bool


class PrivacyRequestSummaryResponse(BaseModel):
    privacy_request_reference: str
    ticket_reference: str | None = None
    request_type: PrivacyRequestTypeLiteral
    status: PrivacyRequestStatusLiteral
    submitted_at: datetime
    updated_at: datetime
    scheduled_for: datetime | None = None
    fulfilled_at: datetime | None = None
    canceled_at: datetime | None = None
    manual_fulfillment_target_days: int
    existing: bool = False
    allowed_actions: list[str] = Field(default_factory=list)


class PrivacyRequestEventResponse(BaseModel):
    event_type: str
    actor_type: Literal["customer", "admin", "system"]
    from_status: PrivacyRequestStatusLiteral | None = None
    to_status: PrivacyRequestStatusLiteral | None = None
    safe_summary: str
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class CustomerPrivacyRequestDetailResponse(PrivacyRequestSummaryResponse):
    reason_code: str | None = None
    notes_redacted: str | None = None
    events: list[PrivacyRequestEventResponse] = Field(default_factory=list)


class PrivacyRequestListResponse(BaseModel):
    requests: list[PrivacyRequestSummaryResponse]
    next_cursor: str | None = None


class AdminPrivacyRequestSummaryResponse(PrivacyRequestSummaryResponse):
    safe_customer_reference: str
    assigned_admin_id: str | None = None
    overdue: bool = False


class AdminPrivacyRequestListResponse(BaseModel):
    requests: list[AdminPrivacyRequestSummaryResponse]
    next_cursor: str | None = None


class AdminPrivacyRequestDetailResponse(AdminPrivacyRequestSummaryResponse):
    reason_code: str | None = None
    notes_redacted: str | None = None
    policy_snapshot: dict[str, object] = Field(default_factory=dict)
    customer_account_public_uid: int | None = None
    principal_subject: str
    support_ticket_reference: str | None = None
    decision_reason: str | None = None
    last_error_code: str | None = None
    last_error_redacted: str | None = None
    review_started_at: datetime | None = None
    identity_verified_at: datetime | None = None
    decision_at: datetime | None = None
    version: int
    events: list[PrivacyRequestEventResponse] = Field(default_factory=list)


class StartReviewRequest(BaseModel):
    assign_to_self: bool = True


class RequestIdentityVerificationRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


class VerifyIdentityRequest(BaseModel):
    verification_method: str = Field(..., min_length=1, max_length=80)
    safe_note: str | None = Field(default=None, max_length=500)


class DecisionRequest(BaseModel):
    decision_reason: str = Field(..., min_length=1, max_length=500)


class ScheduleRequest(BaseModel):
    scheduled_for: datetime | None = None


class ExecuteRequest(BaseModel):
    confirm_text: str = Field(..., min_length=6, max_length=6)
    step_up_token: str | None = Field(default=None, max_length=200)
