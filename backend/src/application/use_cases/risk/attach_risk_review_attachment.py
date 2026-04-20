from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.infrastructure.database.models.risk_review_attachment_model import RiskReviewAttachmentModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository


class AttachRiskReviewAttachmentUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._risk_repo = RiskSubjectGraphRepository(session)
        self._admin_user_repo = AdminUserRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        risk_review_id: UUID,
        attachment_type: str,
        storage_key: str,
        file_name: str | None,
        attachment_metadata: dict | None,
        created_by_admin_user_id: UUID,
    ) -> RiskReviewAttachmentModel:
        review = await self._risk_repo.get_review_by_id(risk_review_id)
        if review is None:
            raise ValueError("Risk review not found")

        admin_user = await self._admin_user_repo.get_by_id(created_by_admin_user_id)
        if admin_user is None:
            raise ValueError("Admin actor not found")

        attachment = RiskReviewAttachmentModel(
            risk_review_id=risk_review_id,
            attachment_type=attachment_type.strip(),
            storage_key=storage_key.strip(),
            file_name=file_name.strip() if file_name else None,
            attachment_metadata=dict(attachment_metadata or {}),
            created_by_admin_user_id=created_by_admin_user_id,
        )
        created = await self._risk_repo.create_review_attachment(attachment)
        await self._outbox.append_event(
            event_name="risk.evidence.attached",
            aggregate_type="risk_review",
            aggregate_id=str(review.id),
            partition_key=str(review.risk_subject_id),
            event_payload={
                "risk_review_id": str(review.id),
                "risk_subject_id": str(review.risk_subject_id),
                "risk_review_attachment_id": str(created.id),
                "attachment_type": created.attachment_type,
            },
            actor_context=OutboxActorContext(principal_type="admin", principal_id=str(created_by_admin_user_id)),
            source_context={"source_use_case": "AttachRiskReviewAttachmentUseCase"},
        )
        await self._session.flush()
        return created
