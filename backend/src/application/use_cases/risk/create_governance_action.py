from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.domain.enums import GovernanceActionStatus, GovernanceActionType
from src.infrastructure.database.models.governance_action_model import GovernanceActionModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository


class CreateGovernanceActionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._risk_repo = RiskSubjectGraphRepository(session)
        self._admin_user_repo = AdminUserRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        risk_subject_id: UUID,
        risk_review_id: UUID | None,
        action_type: GovernanceActionType | str,
        reason: str,
        target_type: str | None,
        target_ref: str | None,
        action_payload: dict | None,
        apply_now: bool,
        created_by_admin_user_id: UUID,
    ) -> GovernanceActionModel:
        subject = await self._risk_repo.get_subject_by_id(risk_subject_id)
        if subject is None:
            raise ValueError("Risk subject not found")

        review = None
        if risk_review_id is not None:
            review = await self._risk_repo.get_review_by_id(risk_review_id)
            if review is None:
                raise ValueError("Risk review not found")
            if review.risk_subject_id != risk_subject_id:
                raise ValueError("Risk review does not belong to risk subject")

        admin_user = await self._admin_user_repo.get_by_id(created_by_admin_user_id)
        if admin_user is None:
            raise ValueError("Admin actor not found")

        now = datetime.now(UTC)
        normalized_status = GovernanceActionStatus.APPLIED if apply_now else GovernanceActionStatus.REQUESTED
        action = GovernanceActionModel(
            risk_subject_id=risk_subject_id,
            risk_review_id=risk_review_id,
            action_type=GovernanceActionType(action_type).value,
            action_status=normalized_status.value,
            target_type=target_type.strip() if target_type else None,
            target_ref=target_ref.strip() if target_ref else None,
            reason=reason.strip(),
            action_payload=dict(action_payload or {}),
            created_by_admin_user_id=created_by_admin_user_id,
            applied_by_admin_user_id=created_by_admin_user_id if apply_now else None,
            applied_at=now if apply_now else None,
        )
        created = await self._risk_repo.create_governance_action(action)
        await self._outbox.append_event(
            event_name="risk.governance_action.recorded",
            aggregate_type="risk_subject",
            aggregate_id=str(risk_subject_id),
            partition_key=str(risk_subject_id),
            event_payload={
                "governance_action_id": str(created.id),
                "risk_subject_id": str(created.risk_subject_id),
                "risk_review_id": str(created.risk_review_id) if created.risk_review_id else None,
                "action_type": created.action_type,
                "action_status": created.action_status,
                "target_type": created.target_type,
                "target_ref": created.target_ref,
            },
            actor_context=OutboxActorContext(principal_type="admin", principal_id=str(created_by_admin_user_id)),
            source_context={"source_use_case": "CreateGovernanceActionUseCase"},
        )
        await self._session.flush()
        return created
