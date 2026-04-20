from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.program_eligibility_policy_model import ProgramEligibilityPolicyModel
from src.infrastructure.database.repositories.program_eligibility_policy_repo import (
    ProgramEligibilityPolicyRepository,
)


class ListProgramEligibilityPoliciesUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ProgramEligibilityPolicyRepository(session)

    async def execute(
        self,
        *,
        at: datetime | None = None,
        subject_type: str | None = None,
        subscription_plan_id: UUID | None = None,
        plan_addon_id: UUID | None = None,
        offer_id: UUID | None = None,
        include_inactive: bool = False,
    ) -> list[ProgramEligibilityPolicyModel]:
        return await self._repo.list_active(
            at=at,
            subject_type=subject_type,
            subscription_plan_id=subscription_plan_id,
            plan_addon_id=plan_addon_id,
            offer_id=offer_id,
            include_inactive=include_inactive,
        )
