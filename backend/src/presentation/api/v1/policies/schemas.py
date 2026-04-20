from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PolicyVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_family: str
    policy_key: str
    subject_type: str
    subject_id: UUID | None
    version_number: int
    payload: dict
    approval_state: str
    version_status: str
    effective_from: datetime
    effective_to: datetime | None
    created_by_admin_user_id: UUID | None
    approved_by_admin_user_id: UUID | None
    approved_at: datetime | None
    rejection_reason: str | None
    supersedes_policy_version_id: UUID | None


class CreatePolicyVersionRequest(BaseModel):
    policy_family: str = Field(..., min_length=1, max_length=50)
    policy_key: str = Field(..., min_length=1, max_length=80)
    subject_type: str = Field(..., min_length=1, max_length=40)
    subject_id: UUID | None = None
    version_number: int = Field(..., ge=1)
    payload: dict = Field(default_factory=dict)
    approval_state: str = "draft"
    version_status: str = "draft"
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    rejection_reason: str | None = Field(default=None, max_length=2000)
    supersedes_policy_version_id: UUID | None = None


class ApprovePolicyVersionRequest(BaseModel):
    version_status: str = "active"
    effective_from: datetime | None = None
    effective_to: datetime | None = None
