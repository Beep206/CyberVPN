from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.enums import PolicyVersionStatus


@dataclass(frozen=True)
class ProgramEligibilityPolicy:
    uuid: UUID
    policy_key: str
    subject_type: str
    subscription_plan_id: UUID | None
    plan_addon_id: UUID | None
    offer_id: UUID | None
    invite_allowed: bool
    referral_credit_allowed: bool
    creator_affiliate_allowed: bool
    performance_allowed: bool
    reseller_allowed: bool
    renewal_commissionable: bool
    addon_commissionable: bool
    version_status: PolicyVersionStatus | str
    effective_from: datetime
    effective_to: datetime | None
    is_active: bool

    def __post_init__(self) -> None:
        referenced_subjects = [self.subscription_plan_id, self.plan_addon_id, self.offer_id]
        if sum(subject is not None for subject in referenced_subjects) != 1:
            raise ValueError("Program eligibility policy must reference exactly one subject")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("Program eligibility effective_to must be greater than effective_from")
