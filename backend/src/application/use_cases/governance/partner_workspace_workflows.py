from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.partner_workspace_workflow_event_model import (
    PartnerWorkspaceWorkflowEventModel,
)
from src.infrastructure.database.repositories.governance_repo import GovernanceRepository
from src.infrastructure.database.repositories.partner_account_repository import (
    PartnerAccountRepository,
)


class CreatePartnerWorkspaceWorkflowEventUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GovernanceRepository(session)
        self._partners = PartnerAccountRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        subject_kind: str,
        subject_id: str,
        action_kind: str,
        message: str,
        event_payload: dict | None = None,
        created_by_admin_user_id: UUID | None = None,
    ) -> PartnerWorkspaceWorkflowEventModel:
        workspace = await self._partners.get_account_by_id(partner_account_id)
        if workspace is None:
            raise ValueError("Partner workspace not found")

        normalized_subject_kind = subject_kind.strip()
        normalized_subject_id = subject_id.strip()
        normalized_action_kind = action_kind.strip()
        normalized_message = message.strip()
        if not normalized_subject_kind:
            raise ValueError("subject_kind is required")
        if not normalized_subject_id:
            raise ValueError("subject_id is required")
        if not normalized_action_kind:
            raise ValueError("action_kind is required")
        if not normalized_message:
            raise ValueError("message is required")

        created = await self._repo.create_workspace_workflow_event(
            PartnerWorkspaceWorkflowEventModel(
                partner_account_id=partner_account_id,
                subject_kind=normalized_subject_kind,
                subject_id=normalized_subject_id,
                action_kind=normalized_action_kind,
                message=normalized_message,
                event_payload=dict(event_payload or {}),
                created_by_admin_user_id=created_by_admin_user_id,
            )
        )
        await self._session.commit()
        await self._session.refresh(created)
        return created


class ListPartnerWorkspaceWorkflowEventsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = GovernanceRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        subject_kind: str | None = None,
        subject_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PartnerWorkspaceWorkflowEventModel]:
        return await self._repo.list_workspace_workflow_events(
            partner_account_id=partner_account_id,
            subject_kind=subject_kind,
            subject_id=subject_id,
            limit=limit,
            offset=offset,
        )
