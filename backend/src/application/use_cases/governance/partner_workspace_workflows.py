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
from src.infrastructure.monitoring.instrumentation.partner_runtime import (
    PARTNER_ADMIN_SURFACE,
    PARTNER_PORTAL_SURFACE,
    log_partner_runtime_event,
    observe_partner_case_action,
    observe_partner_notification_generated,
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
        surface = _workflow_surface_for_action(normalized_action_kind)
        notification_type = _notification_type_for_workflow_event(
            subject_kind=normalized_subject_kind,
            action_kind=normalized_action_kind,
        )
        if notification_type is not None:
            observe_partner_notification_generated(
                surface=surface,
                notification_type=notification_type,
                result="success",
            )
        if normalized_subject_kind == "case":
            observe_partner_case_action(
                surface=surface,
                case_type="workspace_case",
                action=normalized_action_kind,
                result="success",
            )
        log_partner_runtime_event(
            "partner_workspace.workflow_event_created",
            surface=surface,
            route_group="workflow",
            workspace_status=workspace.status,
            subject_kind=normalized_subject_kind,
            action_kind=normalized_action_kind,
            subject_id=normalized_subject_id,
            result="success",
        )
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


def _workflow_surface_for_action(action_kind: str) -> str:
    if action_kind.startswith("partner_"):
        return PARTNER_PORTAL_SURFACE
    return PARTNER_ADMIN_SURFACE


def _notification_type_for_workflow_event(
    *,
    subject_kind: str,
    action_kind: str,
) -> str | None:
    if action_kind == "workspace_draft_created":
        return "workspace_draft"
    if action_kind in {"application_submitted", "application_resubmitted"}:
        return "application_submitted"
    if action_kind in {"application_approved_probation", "application_waitlisted", "application_rejected"}:
        return action_kind
    if action_kind in {"lane_application_approved", "lane_application_declined"}:
        return "lane_membership_changed"
    if subject_kind == "review_request":
        if action_kind.startswith("partner_"):
            return None
        return "review_request_opened"
    if subject_kind == "case":
        return "case_reply_received" if action_kind.startswith("partner_") else "case_created"
    if subject_kind == "report_export":
        return "report_export_requested"
    return None
