from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.domain.enums import RiskReviewDecision, RiskReviewStatus
from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository


class ResolveRiskReviewUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._risk_repo = RiskSubjectGraphRepository(session)
        self._admin_user_repo = AdminUserRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        risk_review_id: UUID,
        decision: RiskReviewDecision | str,
        resolution_status: RiskReviewStatus | str,
        resolution_reason: str | None,
        resolution_evidence: dict | None,
        resolved_by_admin_user_id: UUID,
    ) -> RiskReviewModel:
        review = await self._risk_repo.get_review_by_id(risk_review_id)
        if review is None:
            raise ValueError("Risk review not found")
        if review.status != RiskReviewStatus.OPEN.value:
            raise ValueError("Risk review is not open")

        admin_user = await self._admin_user_repo.get_by_id(resolved_by_admin_user_id)
        if admin_user is None:
            raise ValueError("Admin actor not found")

        normalized_status = RiskReviewStatus(resolution_status)
        if normalized_status == RiskReviewStatus.OPEN:
            raise ValueError("resolution_status must close the review")
        normalized_decision = RiskReviewDecision(decision)
        now = datetime.now(UTC)

        review.status = normalized_status.value
        review.decision = normalized_decision.value
        review.resolved_by_admin_user_id = resolved_by_admin_user_id
        review.resolved_at = now

        merged_evidence = dict(review.evidence or {})
        if resolution_reason:
            merged_evidence["resolution_reason"] = resolution_reason.strip()
        if resolution_evidence:
            merged_evidence["resolution_evidence"] = dict(resolution_evidence)
        review.evidence = merged_evidence

        await self._session.flush()
        await self._session.refresh(review)

        actor_context = OutboxActorContext(principal_type="admin", principal_id=str(resolved_by_admin_user_id))
        await self._outbox.append_event(
            event_name="risk.decision.recorded",
            aggregate_type="risk_review",
            aggregate_id=str(review.id),
            partition_key=str(review.risk_subject_id),
            event_payload={
                "risk_review_id": str(review.id),
                "risk_subject_id": str(review.risk_subject_id),
                "decision": review.decision,
                "status": review.status,
            },
            actor_context=actor_context,
            source_context={"source_use_case": "ResolveRiskReviewUseCase"},
        )
        await self._outbox.append_event(
            event_name="risk.review.resolved",
            aggregate_type="risk_review",
            aggregate_id=str(review.id),
            partition_key=str(review.risk_subject_id),
            event_payload={
                "risk_review_id": str(review.id),
                "risk_subject_id": str(review.risk_subject_id),
                "decision": review.decision,
                "status": review.status,
                "resolved_at": review.resolved_at.isoformat() if review.resolved_at else None,
            },
            actor_context=actor_context,
            source_context={"source_use_case": "ResolveRiskReviewUseCase"},
        )
        await self._session.flush()
        return review
