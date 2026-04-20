"""Pydantic schemas for security and risk endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import (
    GovernanceActionType,
    PrincipalClass,
    RiskIdentifierType,
    RiskReviewDecision,
    RiskReviewStatus,
)


class SetAntiPhishingCodeRequest(BaseModel):
    """Request to set or update anti-phishing code."""

    code: str = Field(..., min_length=1, max_length=50, description="User's anti-phishing code")


class AntiPhishingCodeResponse(BaseModel):
    """Response with anti-phishing code."""

    code: str | None = Field(None, description="User's anti-phishing code (null if not set)")


class DeleteAntiPhishingCodeResponse(BaseModel):
    """Response after deleting anti-phishing code."""

    message: str = "Anti-phishing code deleted successfully"


class RiskSubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    principal_class: str
    principal_subject: str
    auth_realm_id: UUID | None
    storefront_id: UUID | None
    status: str
    risk_level: str
    subject_metadata: dict = Field(
        validation_alias="metadata_payload",
        serialization_alias="metadata",
    )
    created_at: datetime
    updated_at: datetime


class CreateRiskSubjectRequest(BaseModel):
    principal_class: PrincipalClass
    principal_subject: UUID
    auth_realm_id: UUID | None = None
    storefront_id: UUID | None = None
    status: str = Field(default="active", min_length=1, max_length=20)
    risk_level: str = Field(default="low", min_length=1, max_length=20)
    metadata: dict = Field(default_factory=dict)


class RiskIdentifierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    risk_subject_id: UUID
    identifier_type: str
    value_hash: str
    value_preview: str
    is_verified: bool
    source: str
    created_at: datetime


class AttachRiskIdentifierRequest(BaseModel):
    identifier_type: RiskIdentifierType
    value: str = Field(..., min_length=1, max_length=255)
    is_verified: bool = False
    source: str = Field(..., min_length=1, max_length=40)


class RiskLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    left_subject_id: UUID
    right_subject_id: UUID
    link_type: str
    identifier_type: str
    source_identifier_id: UUID | None
    status: str
    evidence: dict
    created_at: datetime
    updated_at: datetime


class AttachRiskIdentifierResponse(BaseModel):
    identifier: RiskIdentifierResponse
    links_created: list[RiskLinkResponse]


class RiskReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    risk_subject_id: UUID
    review_type: str
    status: str
    decision: str
    reason: str
    evidence: dict
    created_by_admin_user_id: UUID | None
    resolved_by_admin_user_id: UUID | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CreateRiskReviewRequest(BaseModel):
    risk_subject_id: UUID
    review_type: str = Field(..., min_length=1, max_length=40)
    reason: str = Field(..., min_length=1, max_length=2000)
    decision: RiskReviewDecision = RiskReviewDecision.PENDING
    evidence: dict = Field(default_factory=dict)


class RiskReviewAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    risk_review_id: UUID
    attachment_type: str
    storage_key: str
    file_name: str | None
    metadata: dict = Field(
        validation_alias="attachment_metadata",
        serialization_alias="metadata",
    )
    created_by_admin_user_id: UUID | None
    created_at: datetime


class AttachRiskReviewAttachmentRequest(BaseModel):
    attachment_type: str = Field(..., min_length=1, max_length=40)
    storage_key: str = Field(..., min_length=1, max_length=255)
    file_name: str | None = Field(default=None, max_length=255)
    metadata: dict = Field(default_factory=dict)


class ResolveRiskReviewRequest(BaseModel):
    decision: RiskReviewDecision
    resolution_status: RiskReviewStatus = RiskReviewStatus.RESOLVED
    resolution_reason: str | None = Field(default=None, max_length=2000)
    resolution_evidence: dict = Field(default_factory=dict)


class GovernanceActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    risk_subject_id: UUID
    risk_review_id: UUID | None
    action_type: str
    status: str = Field(validation_alias="action_status")
    target_type: str | None
    target_ref: str | None
    reason: str
    payload: dict = Field(
        validation_alias="action_payload",
        serialization_alias="payload",
    )
    created_by_admin_user_id: UUID | None
    applied_by_admin_user_id: UUID | None
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CreateGovernanceActionRequest(BaseModel):
    risk_subject_id: UUID
    risk_review_id: UUID | None = None
    action_type: GovernanceActionType
    reason: str = Field(..., min_length=1, max_length=2000)
    target_type: str | None = Field(default=None, max_length=60)
    target_ref: str | None = Field(default=None, max_length=255)
    payload: dict = Field(default_factory=dict)
    apply_now: bool = False


class RiskReviewQueueItemResponse(BaseModel):
    review: RiskReviewResponse
    subject: RiskSubjectResponse
    attachment_count: int
    governance_action_count: int


class RiskReviewDetailResponse(BaseModel):
    review: RiskReviewResponse
    subject: RiskSubjectResponse
    attachments: list[RiskReviewAttachmentResponse]
    governance_actions: list[GovernanceActionResponse]


class EligibilityCheckRequest(BaseModel):
    check_type: str = Field(..., min_length=1, max_length=40)
    risk_subject_id: UUID
    counterparty_subject_id: UUID | None = None
    context: dict = Field(default_factory=dict)


class EligibilityCheckResponse(BaseModel):
    check_type: str
    risk_subject_id: UUID
    allowed: bool
    reason_codes: list[str]
    linked_subject_ids: list[UUID]
    checked_at: datetime
