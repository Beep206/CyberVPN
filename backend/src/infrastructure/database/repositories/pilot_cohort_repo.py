from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.pilot_cohort_model import (
    PilotCohortModel,
    PilotGoNoGoDecisionModel,
    PilotOwnerAcknowledgementModel,
    PilotRollbackDrillModel,
    PilotRolloutWindowModel,
)


class PilotCohortRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pilot_cohort(self, model: PilotCohortModel) -> PilotCohortModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def create_pilot_rollout_window(
        self,
        model: PilotRolloutWindowModel,
    ) -> PilotRolloutWindowModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def create_owner_acknowledgement(
        self,
        model: PilotOwnerAcknowledgementModel,
    ) -> PilotOwnerAcknowledgementModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def create_rollback_drill(
        self,
        model: PilotRollbackDrillModel,
    ) -> PilotRollbackDrillModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def create_go_no_go_decision(
        self,
        model: PilotGoNoGoDecisionModel,
    ) -> PilotGoNoGoDecisionModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_pilot_cohort_by_id(self, cohort_id: UUID) -> PilotCohortModel | None:
        return await self._session.get(PilotCohortModel, cohort_id)

    async def get_pilot_cohort_by_key(self, cohort_key: str) -> PilotCohortModel | None:
        result = await self._session.execute(
            select(PilotCohortModel).where(PilotCohortModel.cohort_key == cohort_key)
        )
        return result.scalar_one_or_none()

    async def list_pilot_cohorts(
        self,
        *,
        partner_account_id: UUID | None = None,
        lane_key: str | None = None,
        surface_key: str | None = None,
        cohort_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PilotCohortModel]:
        query = select(PilotCohortModel)
        if partner_account_id is not None:
            query = query.where(PilotCohortModel.partner_account_id == partner_account_id)
        if lane_key is not None:
            query = query.where(PilotCohortModel.lane_key == lane_key)
        if surface_key is not None:
            query = query.where(PilotCohortModel.surface_key == surface_key)
        if cohort_status is not None:
            query = query.where(PilotCohortModel.cohort_status == cohort_status)
        query = query.order_by(
            PilotCohortModel.scheduled_start_at.asc(),
            PilotCohortModel.created_at.asc(),
        ).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_rollout_windows_for_cohort(self, cohort_id: UUID) -> list[PilotRolloutWindowModel]:
        result = await self._session.execute(
            select(PilotRolloutWindowModel)
            .where(PilotRolloutWindowModel.pilot_cohort_id == cohort_id)
            .order_by(
                PilotRolloutWindowModel.starts_at.asc(),
                PilotRolloutWindowModel.target_ref.asc(),
            )
        )
        return list(result.scalars().all())

    async def list_rollout_windows_for_cohorts(
        self,
        cohort_ids: list[UUID],
    ) -> list[PilotRolloutWindowModel]:
        if not cohort_ids:
            return []
        result = await self._session.execute(
            select(PilotRolloutWindowModel)
            .where(PilotRolloutWindowModel.pilot_cohort_id.in_(cohort_ids))
            .order_by(
                PilotRolloutWindowModel.starts_at.asc(),
                PilotRolloutWindowModel.target_ref.asc(),
            )
        )
        return list(result.scalars().all())

    async def list_owner_acknowledgements_for_cohort(
        self,
        cohort_id: UUID,
    ) -> list[PilotOwnerAcknowledgementModel]:
        result = await self._session.execute(
            select(PilotOwnerAcknowledgementModel)
            .where(PilotOwnerAcknowledgementModel.pilot_cohort_id == cohort_id)
            .order_by(
                PilotOwnerAcknowledgementModel.acknowledged_at.desc(),
                PilotOwnerAcknowledgementModel.created_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def list_rollback_drills_for_cohort(
        self,
        cohort_id: UUID,
    ) -> list[PilotRollbackDrillModel]:
        result = await self._session.execute(
            select(PilotRollbackDrillModel)
            .where(PilotRollbackDrillModel.pilot_cohort_id == cohort_id)
            .order_by(
                PilotRollbackDrillModel.executed_at.desc(),
                PilotRollbackDrillModel.created_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def list_go_no_go_decisions_for_cohort(
        self,
        cohort_id: UUID,
    ) -> list[PilotGoNoGoDecisionModel]:
        result = await self._session.execute(
            select(PilotGoNoGoDecisionModel)
            .where(PilotGoNoGoDecisionModel.pilot_cohort_id == cohort_id)
            .order_by(
                PilotGoNoGoDecisionModel.decided_at.desc(),
                PilotGoNoGoDecisionModel.created_at.desc(),
            )
        )
        return list(result.scalars().all())
