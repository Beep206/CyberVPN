"""Partner application and onboarding workflow use cases."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import PartnerAccountStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.partner_application_model import (
    PartnerApplicationAttachmentModel,
    PartnerApplicationDraftModel,
    PartnerApplicationReviewRequestModel,
    PartnerLaneApplicationModel,
)
from src.infrastructure.database.models.partner_model import PartnerAccountModel
from src.infrastructure.database.models.partner_workspace_workflow_event_model import (
    PartnerWorkspaceWorkflowEventModel,
)
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.governance_repo import GovernanceRepository
from src.infrastructure.database.repositories.partner_account_repository import (
    PartnerAccountRepository,
)
from src.infrastructure.database.repositories.partner_application_repository import (
    PartnerApplicationRepository,
)
from src.infrastructure.monitoring.instrumentation.partner_runtime import (
    PARTNER_ADMIN_SURFACE,
    PARTNER_PORTAL_SURFACE,
    PARTNER_PRINCIPAL_CLASS,
    bind_partner_runtime_context,
    log_partner_runtime_event,
    observe_partner_application_decision,
    observe_partner_application_draft_created,
    observe_partner_application_draft_saved,
    observe_partner_application_evidence_upload,
    observe_partner_application_requested_info,
    observe_partner_application_submission,
    observe_partner_notification_generated,
)

from .create_partner_workspace import CreatePartnerWorkspaceUseCase

PARTNER_APPLICATION_REQUIRED_FIELDS = {
    "workspace_name",
    "contact_name",
    "contact_email",
    "country",
    "website",
    "primary_lane",
    "business_description",
    "acquisition_channels",
}
PARTNER_PRIMARY_LANES = {
    "creator_affiliate",
    "performance_media",
    "reseller_api",
}
APPLICATION_REVIEW_REQUEST_OPEN_STATUSES = {"open", "responded"}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_string(value: object | None) -> str:
    return value.strip() if isinstance(value, str) else ""


def _normalize_bool(value: object | None) -> bool:
    return value is True


def _normalize_primary_lane(value: object | None) -> str:
    candidate = _normalize_string(value)
    return candidate if candidate in PARTNER_PRIMARY_LANES else ""


def _primary_lane_from_payload(payload: dict[str, object] | None) -> str | None:
    normalized = normalize_partner_application_payload(payload)
    lane = normalized.get("primary_lane")
    return str(lane) if lane else None


def normalize_partner_application_payload(payload: dict[str, object] | None) -> dict[str, object]:
    payload = payload or {}
    return {
        "workspace_name": _normalize_string(payload.get("workspace_name")),
        "contact_name": _normalize_string(payload.get("contact_name")),
        "contact_email": _normalize_string(payload.get("contact_email")),
        "country": _normalize_string(payload.get("country")),
        "website": _normalize_string(payload.get("website")),
        "primary_lane": _normalize_primary_lane(payload.get("primary_lane")),
        "business_description": _normalize_string(payload.get("business_description")),
        "acquisition_channels": _normalize_string(payload.get("acquisition_channels")),
        "operating_regions": _normalize_string(payload.get("operating_regions")),
        "languages": _normalize_string(payload.get("languages")),
        "support_contact": _normalize_string(payload.get("support_contact")),
        "technical_contact": _normalize_string(payload.get("technical_contact")),
        "finance_contact": _normalize_string(payload.get("finance_contact")),
        "compliance_accepted": _normalize_bool(payload.get("compliance_accepted")),
    }


def merge_partner_application_payload(
    current_payload: dict[str, object] | None,
    patch_payload: dict[str, object] | None,
) -> dict[str, object]:
    merged = dict(normalize_partner_application_payload(current_payload))
    patch_payload = patch_payload or {}
    for key, value in normalize_partner_application_payload(patch_payload).items():
        if key in patch_payload:
            merged[key] = value
    return merged


def validate_partner_application_submission(payload: dict[str, object]) -> None:
    missing_fields = [
        field_name
        for field_name in sorted(PARTNER_APPLICATION_REQUIRED_FIELDS)
        if not payload.get(field_name)
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Partner application is incomplete: missing {missing}")
    if payload.get("compliance_accepted") is not True:
        raise ValueError("Partner application compliance baseline must be accepted before submission")


class PartnerApplicationWorkflowUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._partner_accounts = PartnerAccountRepository(session)
        self._applications = PartnerApplicationRepository(session)
        self._admin_users = AdminUserRepository(session)
        self._governance = GovernanceRepository(session)

    async def get_current_draft(
        self,
        *,
        applicant_admin_user_id: UUID,
    ) -> PartnerApplicationDraftModel | None:
        return await self._applications.get_current_draft_for_applicant(applicant_admin_user_id)

    async def get_draft_by_partner_account(
        self,
        *,
        partner_account_id: UUID,
    ) -> PartnerApplicationDraftModel | None:
        return await self._applications.get_draft_by_partner_account_id(partner_account_id)

    async def create_draft(
        self,
        *,
        applicant_admin_user: AdminUserModel,
        payload: dict[str, object] | None = None,
    ) -> PartnerApplicationDraftModel:
        existing = await self._applications.get_current_draft_for_applicant(applicant_admin_user.id)
        if existing is not None:
            return existing

        normalized_payload = normalize_partner_application_payload(payload)
        workspace_name = (
            normalized_payload.get("workspace_name")
            or applicant_admin_user.email
            or applicant_admin_user.login
            or "partner-workspace"
        )
        initial_status = (
            PartnerAccountStatus.EMAIL_VERIFIED.value
            if applicant_admin_user.is_email_verified
            else PartnerAccountStatus.DRAFT.value
        )
        workspace, _membership = await CreatePartnerWorkspaceUseCase(
            self._session,
            self._partner_accounts,
        ).execute(
            display_name=str(workspace_name),
            initial_status=initial_status,
            owner_admin_user_id=applicant_admin_user.id,
            created_by_admin_user_id=applicant_admin_user.id,
        )
        draft = await self._applications.create_draft(
            PartnerApplicationDraftModel(
                partner_account_id=workspace.id,
                applicant_admin_user_id=applicant_admin_user.id,
                draft_payload=normalized_payload,
                review_ready=False,
            )
        )
        await self._sync_primary_lane_from_payload(draft=draft, payload=normalized_payload)
        await self._append_workflow_event(
            partner_account_id=workspace.id,
            subject_kind="application",
            subject_id=str(draft.id),
            action_kind="workspace_draft_created",
            message="Workspace draft created",
            actor_admin_user_id=applicant_admin_user.id,
            event_payload={
                "workspace_status": workspace.status,
                "primary_lane": normalized_payload.get("primary_lane") or None,
            },
        )
        bind_partner_runtime_context(
            surface=PARTNER_PORTAL_SURFACE,
            realm_type="partner",
            principal_class=PARTNER_PRINCIPAL_CLASS,
            route_group="application_onboarding",
            workspace_status=workspace.status,
            lane=_primary_lane_from_payload(normalized_payload),
            result="success",
        )
        observe_partner_application_draft_created(
            lane=_primary_lane_from_payload(normalized_payload),
            workspace_status=workspace.status,
            result="success",
        )
        log_partner_runtime_event(
            "partner_application.draft_created",
            workspace_id=str(workspace.id),
            draft_id=str(draft.id),
            workspace_status=workspace.status,
            lane=_primary_lane_from_payload(normalized_payload),
        )
        await self._session.commit()
        await self._session.refresh(draft)
        return draft

    async def update_draft(
        self,
        *,
        draft_id: UUID,
        applicant_admin_user_id: UUID,
        patch_payload: dict[str, object],
        review_ready: bool | None = None,
    ) -> PartnerApplicationDraftModel:
        draft = await self._get_owned_draft(draft_id=draft_id, applicant_admin_user_id=applicant_admin_user_id)
        workspace = await self._partner_accounts.get_account_by_id(draft.partner_account_id)
        if workspace is None:
            raise ValueError("Partner workspace not found for application draft")

        merged_payload = merge_partner_application_payload(draft.draft_payload, patch_payload)
        draft.draft_payload = merged_payload
        if review_ready is not None:
            draft.review_ready = review_ready
        elif workspace.status in {
            PartnerAccountStatus.DRAFT.value,
            PartnerAccountStatus.EMAIL_VERIFIED.value,
            PartnerAccountStatus.NEEDS_INFO.value,
        }:
            draft.review_ready = False

        workspace_name = str(merged_payload.get("workspace_name") or "").strip()
        if workspace_name:
            workspace.display_name = workspace_name

        if (
            applicant_admin_user_id
            and workspace.status == PartnerAccountStatus.DRAFT.value
        ):
            applicant = await self._admin_users.get_by_id(applicant_admin_user_id)
            if applicant is not None and applicant.is_email_verified:
                workspace.status = PartnerAccountStatus.EMAIL_VERIFIED.value

        await self._sync_primary_lane_from_payload(draft=draft, payload=merged_payload)
        bind_partner_runtime_context(
            surface=PARTNER_PORTAL_SURFACE,
            realm_type="partner",
            principal_class=PARTNER_PRINCIPAL_CLASS,
            route_group="application_onboarding",
            workspace_status=workspace.status,
            lane=_primary_lane_from_payload(merged_payload),
            result="success",
        )
        observe_partner_application_draft_saved(
            lane=_primary_lane_from_payload(merged_payload),
            workspace_status=workspace.status,
            result="success",
        )
        log_partner_runtime_event(
            "partner_application.draft_saved",
            workspace_id=str(workspace.id),
            draft_id=str(draft.id),
            workspace_status=workspace.status,
            lane=_primary_lane_from_payload(merged_payload),
            review_ready=draft.review_ready,
        )
        await self._session.commit()
        await self._session.refresh(draft)
        return draft

    async def submit_draft(
        self,
        *,
        draft_id: UUID,
        applicant_admin_user_id: UUID,
        is_resubmission: bool = False,
    ) -> PartnerApplicationDraftModel:
        started_at = _utcnow()
        draft = await self._get_owned_draft(draft_id=draft_id, applicant_admin_user_id=applicant_admin_user_id)
        workspace = await self._partner_accounts.get_account_by_id(draft.partner_account_id)
        if workspace is None:
            raise ValueError("Partner workspace not found for application draft")

        normalized_payload = normalize_partner_application_payload(draft.draft_payload)
        validate_partner_application_submission(normalized_payload)
        workspace.status = PartnerAccountStatus.SUBMITTED.value
        draft.review_ready = True
        draft.submitted_at = _utcnow()
        draft.withdrawn_at = None
        await self._sync_primary_lane_from_payload(draft=draft, payload=normalized_payload)
        lane_applications = await self._applications.list_lane_applications(draft.partner_account_id)
        for lane_application in lane_applications:
            if lane_application.submitted_at is None:
                lane_application.submitted_at = _utcnow()
            if lane_application.status == "declined":
                lane_application.status = "pending"
                lane_application.decision_reason_code = None
                lane_application.decision_summary = None
                lane_application.decided_at = None

        await self._append_workflow_event(
            partner_account_id=workspace.id,
            subject_kind="application",
            subject_id=str(draft.id),
            action_kind="application_resubmitted" if is_resubmission else "application_submitted",
            message=(
                "Partner application resubmitted after requested information."
                if is_resubmission
                else "Partner application submitted for review."
            ),
            actor_admin_user_id=applicant_admin_user_id,
            event_payload={
                "workspace_status": workspace.status,
                "primary_lane": normalized_payload.get("primary_lane") or None,
            },
        )
        bind_partner_runtime_context(
            surface=PARTNER_PORTAL_SURFACE,
            realm_type="partner",
            principal_class=PARTNER_PRINCIPAL_CLASS,
            route_group="application_onboarding",
            workspace_status=workspace.status,
            lane=_primary_lane_from_payload(normalized_payload),
            result="success",
        )
        observe_partner_application_submission(
            surface=PARTNER_PORTAL_SURFACE,
            lane=_primary_lane_from_payload(normalized_payload),
            workspace_status=workspace.status,
            result="success",
            duration_seconds=max((_utcnow() - started_at).total_seconds(), 0.0),
            reason="resubmission" if is_resubmission else "initial_submission",
        )
        log_partner_runtime_event(
            "partner_application.resubmitted" if is_resubmission else "partner_application.submitted",
            workspace_id=str(workspace.id),
            draft_id=str(draft.id),
            workspace_status=workspace.status,
            lane=_primary_lane_from_payload(normalized_payload),
        )
        await self._session.commit()
        await self._session.refresh(draft)
        return draft

    async def withdraw_draft(
        self,
        *,
        draft_id: UUID,
        applicant_admin_user_id: UUID,
        applicant_is_email_verified: bool,
    ) -> PartnerApplicationDraftModel:
        draft = await self._get_owned_draft(draft_id=draft_id, applicant_admin_user_id=applicant_admin_user_id)
        workspace = await self._partner_accounts.get_account_by_id(draft.partner_account_id)
        if workspace is None:
            raise ValueError("Partner workspace not found for application draft")
        if workspace.status not in {
            PartnerAccountStatus.DRAFT.value,
            PartnerAccountStatus.EMAIL_VERIFIED.value,
            PartnerAccountStatus.SUBMITTED.value,
            PartnerAccountStatus.UNDER_REVIEW.value,
            PartnerAccountStatus.NEEDS_INFO.value,
            PartnerAccountStatus.WAITLISTED.value,
        }:
            raise ValueError("Application cannot be withdrawn from the current state")

        workspace.status = (
            PartnerAccountStatus.EMAIL_VERIFIED.value
            if applicant_is_email_verified
            else PartnerAccountStatus.DRAFT.value
        )
        draft.review_ready = False
        draft.withdrawn_at = _utcnow()
        await self._append_workflow_event(
            partner_account_id=workspace.id,
            subject_kind="application",
            subject_id=str(draft.id),
            action_kind="application_withdrawn",
            message="Partner application withdrawn back to draft state.",
            actor_admin_user_id=applicant_admin_user_id,
            event_payload={"workspace_status": workspace.status},
        )
        bind_partner_runtime_context(
            surface=PARTNER_PORTAL_SURFACE,
            realm_type="partner",
            principal_class=PARTNER_PRINCIPAL_CLASS,
            route_group="application_onboarding",
            workspace_status=workspace.status,
            lane=_primary_lane_from_payload(draft.draft_payload),
            result="success",
        )
        log_partner_runtime_event(
            "partner_application.withdrawn",
            workspace_id=str(workspace.id),
            draft_id=str(draft.id),
            workspace_status=workspace.status,
        )
        await self._session.commit()
        await self._session.refresh(draft)
        return draft

    async def create_attachment(
        self,
        *,
        draft_id: UUID,
        applicant_admin_user_id: UUID,
        attachment_type: str,
        storage_key: str,
        file_name: str | None,
        attachment_metadata: dict[str, object] | None,
        lane_application_id: UUID | None = None,
        review_request_id: UUID | None = None,
    ) -> PartnerApplicationAttachmentModel:
        draft = await self._get_owned_draft(draft_id=draft_id, applicant_admin_user_id=applicant_admin_user_id)
        attachment = await self._applications.create_attachment(
            PartnerApplicationAttachmentModel(
                partner_account_id=draft.partner_account_id,
                partner_application_draft_id=draft.id,
                lane_application_id=lane_application_id,
                review_request_id=review_request_id,
                attachment_type=attachment_type.strip(),
                storage_key=storage_key.strip(),
                file_name=file_name.strip() if file_name else None,
                attachment_metadata=dict(attachment_metadata or {}),
                uploaded_by_admin_user_id=applicant_admin_user_id,
            )
        )
        await self._append_workflow_event(
            partner_account_id=draft.partner_account_id,
            subject_kind="application_attachment",
            subject_id=str(attachment.id),
            action_kind="application_attachment_added",
            message="Application evidence attached.",
            actor_admin_user_id=applicant_admin_user_id,
            event_payload={
                "attachment_type": attachment.attachment_type,
                "review_request_id": str(review_request_id) if review_request_id else None,
            },
        )
        workspace = await self._require_workspace(draft.partner_account_id)
        bind_partner_runtime_context(
            surface=PARTNER_PORTAL_SURFACE,
            realm_type="partner",
            principal_class=PARTNER_PRINCIPAL_CLASS,
            route_group="application_onboarding",
            workspace_status=workspace.status,
            lane=_primary_lane_from_payload(draft.draft_payload),
            result="success",
        )
        observe_partner_application_evidence_upload(
            lane=_primary_lane_from_payload(draft.draft_payload),
            workspace_status=workspace.status,
            result="success",
        )
        log_partner_runtime_event(
            "partner_application.evidence_uploaded",
            workspace_id=str(draft.partner_account_id),
            draft_id=str(draft.id),
            attachment_id=str(attachment.id),
            attachment_type=attachment.attachment_type,
            review_request_id=str(review_request_id) if review_request_id else None,
        )
        await self._session.commit()
        await self._session.refresh(attachment)
        return attachment

    async def list_lane_applications(
        self,
        *,
        partner_account_id: UUID,
    ) -> list[PartnerLaneApplicationModel]:
        return await self._applications.list_lane_applications(partner_account_id)

    async def list_review_requests(
        self,
        *,
        partner_account_id: UUID,
    ) -> list[PartnerApplicationReviewRequestModel]:
        return await self._applications.list_review_requests(partner_account_id)

    async def list_attachments(
        self,
        *,
        partner_account_id: UUID,
    ) -> list[PartnerApplicationAttachmentModel]:
        return await self._applications.list_attachments(partner_account_id)

    async def create_lane_application(
        self,
        *,
        draft_id: UUID,
        applicant_admin_user_id: UUID,
        lane_key: str,
        payload: dict[str, object] | None = None,
    ) -> PartnerLaneApplicationModel:
        draft = await self._get_owned_draft(draft_id=draft_id, applicant_admin_user_id=applicant_admin_user_id)
        return await self._upsert_lane_application(
            draft=draft,
            lane_key=lane_key,
            payload=dict(payload or {}),
            submitted=False,
            commit=True,
        )

    async def update_lane_application(
        self,
        *,
        lane_application_id: UUID,
        partner_account_id: UUID,
        payload: dict[str, object] | None = None,
    ) -> PartnerLaneApplicationModel:
        lane_application = await self._applications.get_lane_application_by_id(lane_application_id)
        if lane_application is None or lane_application.partner_account_id != partner_account_id:
            raise ValueError("Lane application not found")
        lane_application.application_payload = dict(payload or {})
        await self._session.commit()
        await self._session.refresh(lane_application)
        return lane_application

    async def submit_lane_application(
        self,
        *,
        lane_application_id: UUID,
        partner_account_id: UUID,
        actor_admin_user_id: UUID,
    ) -> PartnerLaneApplicationModel:
        lane_application = await self._applications.get_lane_application_by_id(lane_application_id)
        if lane_application is None or lane_application.partner_account_id != partner_account_id:
            raise ValueError("Lane application not found")
        lane_application.status = "pending"
        lane_application.submitted_at = _utcnow()
        await self._append_workflow_event(
            partner_account_id=partner_account_id,
            subject_kind="lane_application",
            subject_id=str(lane_application.id),
            action_kind="lane_application_submitted",
            message=f"Lane application submitted for {lane_application.lane_key}.",
            actor_admin_user_id=actor_admin_user_id,
            event_payload={"lane_key": lane_application.lane_key},
        )
        await self._session.commit()
        await self._session.refresh(lane_application)
        return lane_application

    async def list_admin_application_drafts(
        self,
    ) -> list[PartnerApplicationDraftModel]:
        return await self._applications.list_drafts()

    async def request_info(
        self,
        *,
        partner_account_id: UUID,
        message: str,
        request_kind: str,
        required_fields: list[str],
        required_attachments: list[str],
        requested_by_admin_user_id: UUID,
        lane_application_id: UUID | None = None,
        response_due_at: datetime | None = None,
    ) -> PartnerApplicationReviewRequestModel:
        draft = await self._require_draft_by_partner_account(partner_account_id)
        workspace = await self._require_workspace(partner_account_id)
        workspace.status = PartnerAccountStatus.NEEDS_INFO.value
        draft.review_ready = False
        review_request = await self._applications.create_review_request(
            PartnerApplicationReviewRequestModel(
                partner_account_id=partner_account_id,
                partner_application_draft_id=draft.id,
                lane_application_id=lane_application_id,
                request_kind=request_kind.strip(),
                message=message.strip(),
                required_fields=list(required_fields),
                required_attachments=list(required_attachments),
                status="open",
                requested_by_admin_user_id=requested_by_admin_user_id,
                response_due_at=response_due_at,
            )
        )
        await self._append_workflow_event(
            partner_account_id=partner_account_id,
            subject_kind="review_request",
            subject_id=str(review_request.id),
            action_kind="info_requested",
            message=review_request.message,
            actor_admin_user_id=requested_by_admin_user_id,
            event_payload={
                "request_kind": review_request.request_kind,
                "required_fields": review_request.required_fields,
                "required_attachments": review_request.required_attachments,
            },
        )
        lane_value: str | None = None
        if lane_application_id is not None:
            lane_application = await self._applications.get_lane_application_by_id(lane_application_id)
            lane_value = lane_application.lane_key if lane_application is not None else None
        if lane_value is None:
            lane_value = _primary_lane_from_payload(draft.draft_payload)
        bind_partner_runtime_context(
            surface=PARTNER_ADMIN_SURFACE,
            realm_type="admin",
            principal_class="admin",
            route_group="application_onboarding",
            workspace_status=workspace.status,
            lane=lane_value,
            result="success",
            review_level="workspace",
        )
        observe_partner_application_requested_info(
            lane=lane_value,
            workspace_status=workspace.status,
            review_level="workspace",
            result="success",
        )
        log_partner_runtime_event(
            "partner_application.info_requested",
            workspace_id=str(partner_account_id),
            draft_id=str(draft.id),
            review_request_id=str(review_request.id),
            lane=lane_value,
            request_kind=review_request.request_kind,
        )
        await self._session.commit()
        await self._session.refresh(review_request)
        return review_request

    async def respond_to_review_request(
        self,
        *,
        review_request_id: UUID,
        applicant_admin_user_id: UUID,
    ) -> PartnerApplicationReviewRequestModel:
        review_request = await self._applications.get_review_request_by_id(review_request_id)
        if review_request is None:
            raise ValueError("Review request not found")
        draft = await self._require_draft_by_partner_account(review_request.partner_account_id)
        if draft.applicant_admin_user_id != applicant_admin_user_id:
            raise ValueError("Partner application review request access denied")

        review_request.status = "responded"
        review_request.responded_at = _utcnow()
        await self._session.flush()
        return review_request

    async def approve_probation(
        self,
        *,
        partner_account_id: UUID,
        reviewer_admin_user_id: UUID,
        reason_code: str,
        reason_summary: str,
    ) -> PartnerApplicationDraftModel:
        draft = await self._require_draft_by_partner_account(partner_account_id)
        workspace = await self._require_workspace(partner_account_id)
        workspace.status = PartnerAccountStatus.APPROVED_PROBATION.value
        draft.review_ready = True
        lane_applications = await self._applications.list_lane_applications(partner_account_id)
        for lane_application in lane_applications:
            if lane_application.status == "pending":
                lane_application.status = "approved_probation"
                lane_application.decision_reason_code = reason_code.strip()
                lane_application.decision_summary = reason_summary.strip()
                lane_application.decided_at = _utcnow()
        await self._resolve_open_review_requests(
            partner_account_id=partner_account_id,
            reviewer_admin_user_id=reviewer_admin_user_id,
        )
        await self._append_workflow_event(
            partner_account_id=partner_account_id,
            subject_kind="application",
            subject_id=str(draft.id),
            action_kind="application_approved_probation",
            message=reason_summary.strip(),
            actor_admin_user_id=reviewer_admin_user_id,
            event_payload={"reason_code": reason_code.strip()},
        )
        primary_lane = _primary_lane_from_payload(draft.draft_payload)
        bind_partner_runtime_context(
            surface=PARTNER_ADMIN_SURFACE,
            realm_type="admin",
            principal_class="admin",
            route_group="application_onboarding",
            workspace_status=workspace.status,
            lane=primary_lane,
            result="success",
            review_level="workspace",
            decision="approved_probation",
        )
        observe_partner_application_decision(
            decision="approved_probation",
            lane=primary_lane,
            workspace_status=workspace.status,
            review_level="workspace",
            result="success",
            reason=reason_code.strip(),
            submitted_at=draft.submitted_at,
            decided_at=_utcnow(),
        )
        log_partner_runtime_event(
            "partner_application.approved_probation",
            workspace_id=str(partner_account_id),
            draft_id=str(draft.id),
            reason_code=reason_code.strip(),
        )
        await self._session.commit()
        await self._session.refresh(draft)
        return draft

    async def waitlist(
        self,
        *,
        partner_account_id: UUID,
        reviewer_admin_user_id: UUID,
        reason_code: str,
        reason_summary: str,
    ) -> PartnerApplicationDraftModel:
        draft = await self._require_draft_by_partner_account(partner_account_id)
        workspace = await self._require_workspace(partner_account_id)
        workspace.status = PartnerAccountStatus.WAITLISTED.value
        await self._resolve_open_review_requests(
            partner_account_id=partner_account_id,
            reviewer_admin_user_id=reviewer_admin_user_id,
        )
        await self._append_workflow_event(
            partner_account_id=partner_account_id,
            subject_kind="application",
            subject_id=str(draft.id),
            action_kind="application_waitlisted",
            message=reason_summary.strip(),
            actor_admin_user_id=reviewer_admin_user_id,
            event_payload={"reason_code": reason_code.strip()},
        )
        primary_lane = _primary_lane_from_payload(draft.draft_payload)
        bind_partner_runtime_context(
            surface=PARTNER_ADMIN_SURFACE,
            realm_type="admin",
            principal_class="admin",
            route_group="application_onboarding",
            workspace_status=workspace.status,
            lane=primary_lane,
            result="success",
            review_level="workspace",
            decision="waitlisted",
        )
        observe_partner_application_decision(
            decision="waitlisted",
            lane=primary_lane,
            workspace_status=workspace.status,
            review_level="workspace",
            result="success",
            reason=reason_code.strip(),
            submitted_at=draft.submitted_at,
            decided_at=_utcnow(),
        )
        log_partner_runtime_event(
            "partner_application.waitlisted",
            workspace_id=str(partner_account_id),
            draft_id=str(draft.id),
            reason_code=reason_code.strip(),
        )
        await self._session.commit()
        await self._session.refresh(draft)
        return draft

    async def reject(
        self,
        *,
        partner_account_id: UUID,
        reviewer_admin_user_id: UUID,
        reason_code: str,
        reason_summary: str,
    ) -> PartnerApplicationDraftModel:
        draft = await self._require_draft_by_partner_account(partner_account_id)
        workspace = await self._require_workspace(partner_account_id)
        workspace.status = PartnerAccountStatus.REJECTED.value
        lane_applications = await self._applications.list_lane_applications(partner_account_id)
        for lane_application in lane_applications:
            if lane_application.status in {"pending", "approved_probation"}:
                lane_application.status = "declined"
                lane_application.decision_reason_code = reason_code.strip()
                lane_application.decision_summary = reason_summary.strip()
                lane_application.decided_at = _utcnow()
        await self._resolve_open_review_requests(
            partner_account_id=partner_account_id,
            reviewer_admin_user_id=reviewer_admin_user_id,
        )
        await self._append_workflow_event(
            partner_account_id=partner_account_id,
            subject_kind="application",
            subject_id=str(draft.id),
            action_kind="application_rejected",
            message=reason_summary.strip(),
            actor_admin_user_id=reviewer_admin_user_id,
            event_payload={"reason_code": reason_code.strip()},
        )
        primary_lane = _primary_lane_from_payload(draft.draft_payload)
        bind_partner_runtime_context(
            surface=PARTNER_ADMIN_SURFACE,
            realm_type="admin",
            principal_class="admin",
            route_group="application_onboarding",
            workspace_status=workspace.status,
            lane=primary_lane,
            result="success",
            review_level="workspace",
            decision="rejected",
        )
        observe_partner_application_decision(
            decision="rejected",
            lane=primary_lane,
            workspace_status=workspace.status,
            review_level="workspace",
            result="success",
            reason=reason_code.strip(),
            submitted_at=draft.submitted_at,
            decided_at=_utcnow(),
        )
        log_partner_runtime_event(
            "partner_application.rejected",
            workspace_id=str(partner_account_id),
            draft_id=str(draft.id),
            reason_code=reason_code.strip(),
        )
        await self._session.commit()
        await self._session.refresh(draft)
        return draft

    async def approve_lane(
        self,
        *,
        lane_application_id: UUID,
        reviewer_admin_user_id: UUID,
        target_status: str,
        reason_code: str,
        reason_summary: str,
    ) -> PartnerLaneApplicationModel:
        lane_application = await self._require_lane_application(lane_application_id)
        lane_application.status = target_status
        lane_application.decision_reason_code = reason_code.strip()
        lane_application.decision_summary = reason_summary.strip()
        lane_application.decided_at = _utcnow()
        await self._append_workflow_event(
            partner_account_id=lane_application.partner_account_id,
            subject_kind="lane_application",
            subject_id=str(lane_application.id),
            action_kind="lane_application_approved",
            message=reason_summary.strip(),
            actor_admin_user_id=reviewer_admin_user_id,
            event_payload={
                "lane_key": lane_application.lane_key,
                "target_status": target_status,
                "reason_code": reason_code.strip(),
            },
        )
        await self._session.commit()
        await self._session.refresh(lane_application)
        return lane_application

    async def decline_lane(
        self,
        *,
        lane_application_id: UUID,
        reviewer_admin_user_id: UUID,
        reason_code: str,
        reason_summary: str,
    ) -> PartnerLaneApplicationModel:
        lane_application = await self._require_lane_application(lane_application_id)
        lane_application.status = "declined"
        lane_application.decision_reason_code = reason_code.strip()
        lane_application.decision_summary = reason_summary.strip()
        lane_application.decided_at = _utcnow()
        await self._append_workflow_event(
            partner_account_id=lane_application.partner_account_id,
            subject_kind="lane_application",
            subject_id=str(lane_application.id),
            action_kind="lane_application_declined",
            message=reason_summary.strip(),
            actor_admin_user_id=reviewer_admin_user_id,
            event_payload={
                "lane_key": lane_application.lane_key,
                "reason_code": reason_code.strip(),
            },
        )
        await self._session.commit()
        await self._session.refresh(lane_application)
        return lane_application

    async def _sync_primary_lane_from_payload(
        self,
        *,
        draft: PartnerApplicationDraftModel,
        payload: dict[str, object],
    ) -> None:
        primary_lane = str(payload.get("primary_lane") or "").strip()
        if not primary_lane:
            await self._applications.delete_lane_applications_except(
                partner_account_id=draft.partner_account_id,
                keep_lane_keys=set(),
            )
            return

        await self._applications.delete_lane_applications_except(
            partner_account_id=draft.partner_account_id,
            keep_lane_keys={primary_lane},
        )
        await self._upsert_lane_application(
            draft=draft,
            lane_key=primary_lane,
            payload=payload,
            submitted=draft.submitted_at is not None,
            commit=False,
        )

    async def _upsert_lane_application(
        self,
        *,
        draft: PartnerApplicationDraftModel,
        lane_key: str,
        payload: dict[str, object],
        submitted: bool,
        commit: bool,
    ) -> PartnerLaneApplicationModel:
        normalized_lane_key = lane_key.strip()
        if normalized_lane_key not in PARTNER_PRIMARY_LANES:
            raise ValueError("Unsupported lane key")

        lane_application = await self._applications.get_lane_application_by_lane_key(
            partner_account_id=draft.partner_account_id,
            lane_key=normalized_lane_key,
        )
        application_payload = {
            "lane_key": normalized_lane_key,
            "workspace_snapshot": normalize_partner_application_payload(payload),
        }
        if lane_application is None:
            lane_application = await self._applications.create_lane_application(
                PartnerLaneApplicationModel(
                    partner_account_id=draft.partner_account_id,
                    partner_application_draft_id=draft.id,
                    lane_key=normalized_lane_key,
                    status="pending",
                    application_payload=application_payload,
                    submitted_at=_utcnow() if submitted else None,
                )
            )
        else:
            lane_application.application_payload = application_payload
            lane_application.status = lane_application.status or "pending"
            if submitted and lane_application.submitted_at is None:
                lane_application.submitted_at = _utcnow()
            await self._applications.update_lane_application(lane_application)

        if commit:
            await self._session.commit()
            await self._session.refresh(lane_application)
        return lane_application

    async def _resolve_open_review_requests(
        self,
        *,
        partner_account_id: UUID,
        reviewer_admin_user_id: UUID,
    ) -> None:
        review_requests = await self._applications.list_review_requests(partner_account_id)
        for review_request in review_requests:
            if review_request.status in APPLICATION_REVIEW_REQUEST_OPEN_STATUSES:
                review_request.status = "resolved"
                review_request.resolved_at = _utcnow()
                review_request.resolved_by_admin_user_id = reviewer_admin_user_id

    async def _append_workflow_event(
        self,
        *,
        partner_account_id: UUID,
        subject_kind: str,
        subject_id: str,
        action_kind: str,
        message: str,
        actor_admin_user_id: UUID | None,
        event_payload: dict[str, object] | None = None,
    ) -> PartnerWorkspaceWorkflowEventModel:
        event = PartnerWorkspaceWorkflowEventModel(
            partner_account_id=partner_account_id,
            subject_kind=subject_kind.strip(),
            subject_id=subject_id.strip(),
            action_kind=action_kind.strip(),
            message=message.strip(),
            event_payload=dict(event_payload or {}),
            created_by_admin_user_id=actor_admin_user_id,
        )
        created = await self._governance.create_workspace_workflow_event(event)
        notification_type = _application_notification_type_for_action(created.action_kind)
        if notification_type is not None:
            partner_portal_actions = {
                "workspace_draft_created",
                "application_submitted",
                "application_resubmitted",
            }
            observe_partner_notification_generated(
                surface=(
                    PARTNER_PORTAL_SURFACE
                    if created.action_kind in partner_portal_actions
                    else PARTNER_ADMIN_SURFACE
                ),
                notification_type=notification_type,
                result="success",
            )
        return created

    async def _get_owned_draft(
        self,
        *,
        draft_id: UUID,
        applicant_admin_user_id: UUID,
    ) -> PartnerApplicationDraftModel:
        draft = await self._applications.get_draft_by_id(draft_id)
        if draft is None:
            raise ValueError("Partner application draft not found")
        if draft.applicant_admin_user_id != applicant_admin_user_id:
            raise ValueError("Partner application draft access denied")
        return draft

    async def _require_draft_by_partner_account(
        self,
        partner_account_id: UUID,
    ) -> PartnerApplicationDraftModel:
        draft = await self._applications.get_draft_by_partner_account_id(partner_account_id)
        if draft is None:
            raise ValueError("Partner application draft not found")
        return draft

    async def _require_workspace(self, partner_account_id: UUID) -> PartnerAccountModel:
        workspace = await self._partner_accounts.get_account_by_id(partner_account_id)
        if workspace is None:
            raise ValueError("Partner workspace not found")
        return workspace

    async def _require_lane_application(
        self,
        lane_application_id: UUID,
    ) -> PartnerLaneApplicationModel:
        lane_application = await self._applications.get_lane_application_by_id(lane_application_id)
        if lane_application is None:
            raise ValueError("Lane application not found")
        return lane_application


def _application_notification_type_for_action(action_kind: str) -> str | None:
    if action_kind == "workspace_draft_created":
        return "workspace_draft"
    if action_kind in {"application_submitted", "application_resubmitted"}:
        return "application_submitted"
    if action_kind in {"application_approved_probation", "application_waitlisted", "application_rejected"}:
        return action_kind
    if action_kind in {"lane_application_approved", "lane_application_declined"}:
        return "lane_membership_changed"
    return None
