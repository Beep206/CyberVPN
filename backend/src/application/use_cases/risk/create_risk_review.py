from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.domain.enums import RiskReviewDecision
from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository


class CreateRiskReviewUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._risk_repo = RiskSubjectGraphRepository(session)
        self._admin_user_repo = AdminUserRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        risk_subject_id: UUID,
        review_type: str,
        reason: str,
        evidence: dict | None,
        created_by_admin_user_id: UUID,
        decision: RiskReviewDecision | str = RiskReviewDecision.PENDING,
    ) -> RiskReviewModel:
        subject = await self._risk_repo.get_subject_by_id(risk_subject_id)
        if subject is None:
            raise ValueError("Risk subject not found")

        admin_user = await self._admin_user_repo.get_by_id(created_by_admin_user_id)
        if admin_user is None:
            raise ValueError("Admin actor not found")

        normalized_decision = RiskReviewDecision(decision)
        review = RiskReviewModel(
            risk_subject_id=risk_subject_id,
            review_type=review_type.strip(),
            status="open",
            decision=normalized_decision.value,
            reason=reason.strip(),
            evidence=evidence or {},
            created_by_admin_user_id=created_by_admin_user_id,
        )
        created = await self._risk_repo.create_review(review)
        await self._outbox.append_event(
            event_name="risk.review.opened",
            aggregate_type="risk_review",
            aggregate_id=str(created.id),
            partition_key=str(created.risk_subject_id),
            event_payload={
                "risk_review_id": str(created.id),
                "risk_subject_id": str(created.risk_subject_id),
                "review_type": created.review_type,
                "decision": created.decision,
                "status": created.status,
            },
            actor_context=OutboxActorContext(principal_type="admin", principal_id=str(created_by_admin_user_id)),
            source_context={"source_use_case": "CreateRiskReviewUseCase"},
        )
        await self._session.flush()
        return created
