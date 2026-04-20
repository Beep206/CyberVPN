from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.program_eligibility_policy_model import ProgramEligibilityPolicyModel


class ProgramEligibilityPolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: ProgramEligibilityPolicyModel) -> ProgramEligibilityPolicyModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def list_active(
        self,
        *,
        at: datetime | None = None,
        subject_type: str | None = None,
        subscription_plan_id: UUID | None = None,
        plan_addon_id: UUID | None = None,
        offer_id: UUID | None = None,
        include_inactive: bool = False,
    ) -> list[ProgramEligibilityPolicyModel]:
        now = at or datetime.now(UTC)
        query: Select[tuple[ProgramEligibilityPolicyModel]] = select(ProgramEligibilityPolicyModel).order_by(
            ProgramEligibilityPolicyModel.policy_key,
            ProgramEligibilityPolicyModel.effective_from.desc(),
        )
        if not include_inactive:
            query = query.where(
                ProgramEligibilityPolicyModel.is_active.is_(True),
                ProgramEligibilityPolicyModel.version_status == "active",
                ProgramEligibilityPolicyModel.effective_from <= now,
                (ProgramEligibilityPolicyModel.effective_to.is_(None))
                | (ProgramEligibilityPolicyModel.effective_to > now),
            )
        if subject_type is not None:
            query = query.where(ProgramEligibilityPolicyModel.subject_type == subject_type)
        if subscription_plan_id is not None:
            query = query.where(ProgramEligibilityPolicyModel.subscription_plan_id == subscription_plan_id)
        if plan_addon_id is not None:
            query = query.where(ProgramEligibilityPolicyModel.plan_addon_id == plan_addon_id)
        if offer_id is not None:
            query = query.where(ProgramEligibilityPolicyModel.offer_id == offer_id)
        result = await self._session.execute(query)
        return list(result.scalars().all())
