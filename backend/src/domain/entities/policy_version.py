from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.enums import PolicyApprovalState, PolicyVersionStatus


@dataclass(frozen=True)
class PolicyVersion:
    uuid: UUID
    policy_family: str
    policy_key: str
    subject_type: str
    subject_id: UUID | None
    version_number: int
    payload: dict[str, Any]
    approval_state: PolicyApprovalState | str
    version_status: PolicyVersionStatus | str
    effective_from: datetime
    effective_to: datetime | None
    created_by_admin_user_id: UUID | None
    approved_by_admin_user_id: UUID | None
    approved_at: datetime | None
    rejection_reason: str | None
    supersedes_policy_version_id: UUID | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.version_number <= 0:
            raise ValueError("Policy version_number must be positive")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("Policy effective_to must be greater than effective_from")
        if str(self.version_status) == "active" and str(self.approval_state) != "approved":
            raise ValueError("Active policy versions must be approved")
