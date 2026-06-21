"""Partner API routes for mobile users and admin."""

import hashlib
import io
import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from time import perf_counter
from uuid import UUID, uuid4

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService
from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.gifts.service import IssueGiftCodeUseCase
from src.application.use_cases.governance import (
    CreateCreativeApprovalUseCase,
    CreatePartnerWorkspaceWorkflowEventUseCase,
    CreateTrafficDeclarationUseCase,
    ListCreativeApprovalsUseCase,
    ListDisputeCasesUseCase,
    ListPartnerWorkspaceWorkflowEventsUseCase,
    ListTrafficDeclarationsUseCase,
)
from src.application.use_cases.orders.explainability import GetOrderExplainabilityUseCase
from src.application.use_cases.partner_attribution.utils import (
    build_customer_public_url,
    build_public_token_for_code_id,
    build_share_url,
    generate_partner_code,
    generate_public_slug,
    hash_partner_attribution_token,
    mask_partner_code,
    normalize_partner_code,
)
from src.application.use_cases.partners.add_partner_workspace_member import AddPartnerWorkspaceMemberUseCase
from src.application.use_cases.partners.admin_promote_partner import AdminPromotePartnerUseCase
from src.application.use_cases.partners.bind_partner import BindPartnerUseCase
from src.application.use_cases.partners.create_partner_code import CreatePartnerCodeUseCase
from src.application.use_cases.partners.create_partner_workspace import CreatePartnerWorkspaceUseCase
from src.application.use_cases.partners.get_partner_workspace import GetPartnerWorkspaceUseCase
from src.application.use_cases.partners.partner_applications import (
    PartnerApplicationWorkflowUseCase,
)
from src.application.use_cases.partners.partner_dashboard import PartnerDashboardUseCase
from src.application.use_cases.reporting import (
    BuildPartnerWorkspaceIntegrationDeliveryLogsUseCase,
    BuildPartnerWorkspacePostbackReadinessUseCase,
    BuildPartnerWorkspaceProgramsUseCase,
    BuildPartnerWorkspaceReportingUseCase,
    ListPartnerWorkspaceIntegrationCredentialsUseCase,
    RotatePartnerWorkspaceIntegrationCredentialUseCase,
)
from src.application.use_cases.settlement import (
    CreatePartnerPayoutAccountUseCase,
    EvaluatePartnerPayoutAccountEligibilityUseCase,
    GetPartnerFinanceSummaryUseCase,
    ListPartnerPayoutAccountsUseCase,
    ListPartnerStatementsUseCase,
    ListPayoutExecutionsUseCase,
    ListPayoutInstructionsUseCase,
    MakeDefaultPartnerPayoutAccountUseCase,
)
from src.application.use_cases.settlement.commission_terms import build_commission_contract_model
from src.config.settings import settings
from src.domain.entities.partner_permission import PartnerPermission
from src.domain.enums import (
    AdminRole,
    CreativeApprovalKind,
    CreativeApprovalStatus,
    PartnerIntegrationCredentialKind,
    PartnerPayoutAccountApprovalStatus,
    PartnerPayoutAccountStatus,
    PartnerPayoutAccountVerificationStatus,
    PartnerStatementStatus,
    PayoutExecutionMode,
    PayoutExecutionStatus,
    PayoutInstructionStatus,
)
from src.domain.exceptions import (
    DomainError,
    MarkupExceedsLimitError,
    NotAPartnerError,
    PartnerCodeNotFoundError,
    UserAlreadyBoundToPartnerError,
)
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.commissionability_evaluation_model import (
    CommissionabilityEvaluationModel,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.order_attribution_result_model import (
    OrderAttributionResultModel,
)
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.partner_model import (
    ApiIdempotencyRecordModel,
    PartnerCodeEventModel,
    PartnerCodeLinkModel,
    PartnerCodeModel,
)
from src.infrastructure.database.models.partner_workspace_legal_acceptance_model import (
    PartnerWorkspaceLegalAcceptanceModel,
)
from src.infrastructure.database.models.payment_dispute_model import PaymentDisputeModel
from src.infrastructure.database.models.refund_model import RefundModel
from src.infrastructure.database.models.renewal_order_model import RenewalOrderModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.partner_account_repository import (
    PartnerAccountRepository,
)
from src.infrastructure.database.repositories.partner_notification_read_state_repository import (
    PartnerNotificationReadStateRepository,
)
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.infrastructure.database.repositories.partner_workspace_legal_acceptance_repository import (
    PartnerWorkspaceLegalAcceptanceRepository,
)
from src.infrastructure.database.repositories.partner_workspace_profile_repository import (
    PartnerWorkspaceProfileRepository,
)
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.monitoring.instrumentation.partner_runtime import (
    PARTNER_PORTAL_SURFACE,
    bind_partner_context_from_realm,
    bind_partner_runtime_context,
    log_partner_runtime_event,
    observe_partner_admin_ops_overview,
    observe_partner_bootstrap,
    observe_partner_notification_state_change,
)
from src.infrastructure.monitoring.instrumentation.routes import track_partner_operation
from src.presentation.api.v1.auth.realm_context import (
    get_principal_type_for_realm,
    get_scope_family_for_realm,
)
from src.presentation.api.v1.creative_approvals.schemas import CreativeApprovalResponse
from src.presentation.api.v1.orders.explainability.routes import (
    _serialize_evaluation as _serialize_order_explainability_evaluation,
)
from src.presentation.api.v1.orders.explainability.routes import (
    _serialize_order_summary as _serialize_order_explainability_summary,
)
from src.presentation.api.v1.orders.explainability.schemas import OrderExplainabilityResponse
from src.presentation.api.v1.partner_statements.schemas import PartnerStatementResponse
from src.presentation.api.v1.traffic_declarations.schemas import TrafficDeclarationResponse
from src.presentation.dependencies.auth import (
    get_current_active_user,
    get_current_active_web_user,
    get_current_mobile_user_id,
)
from src.presentation.dependencies.auth_realms import get_request_admin_realm, get_request_web_auth_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_workspace import (
    PartnerWorkspaceAccess,
    require_partner_workspace_permission,
    resolve_partner_workspace_access,
)
from src.presentation.dependencies.passkey_fresh_auth import enforce_passkey_fresh_auth
from src.presentation.dependencies.roles import require_role

from .schemas import (
    AddPartnerWorkspaceMemberRequest,
    BindPartnerRequest,
    CreatePartnerApplicationAttachmentRequest,
    CreatePartnerCodeRequest,
    CreatePartnerLaneApplicationRequest,
    CreatePartnerWorkspaceCodeRequest,
    CreatePartnerWorkspacePayoutAccountRequest,
    CreatePartnerWorkspaceRequest,
    MarkPartnerWorkspaceCaseReadyForOpsRequest,
    PartnerAdminOpsActionResponse,
    PartnerAdminOpsOverviewResponse,
    PartnerAdminPayoutReviewItemResponse,
    PartnerApplicationAdminDetailResponse,
    PartnerApplicationAdminSummaryResponse,
    PartnerApplicationApplicantSummaryResponse,
    PartnerApplicationAttachmentResponse,
    PartnerApplicationDraftDetailResponse,
    PartnerApplicationDraftResponse,
    PartnerApplicationPayloadResponse,
    PartnerApplicationReviewDecisionRequest,
    PartnerApplicationReviewRequestDetailResponse,
    PartnerApplicationWorkspaceSummaryResponse,
    PartnerCodeResponse,
    PartnerDashboardResponse,
    PartnerEarningResponse,
    PartnerLaneApplicationResponse,
    PartnerNotificationCountersResponse,
    PartnerNotificationFeedItemResponse,
    PartnerNotificationPreferencesResponse,
    PartnerNotificationPreferencesUpdateRequest,
    PartnerNotificationReadStateResponse,
    PartnerSessionBootstrapBlockedReasonResponse,
    PartnerSessionBootstrapCounterResponse,
    PartnerSessionBootstrapPendingTaskResponse,
    PartnerSessionBootstrapResponse,
    PartnerSessionPrincipalResponse,
    PartnerWorkspaceAnalyticsMetricResponse,
    PartnerWorkspaceCampaignAssetResponse,
    PartnerWorkspaceCaseResponse,
    PartnerWorkspaceCodeLifecycleRequest,
    PartnerWorkspaceCodeLinkRequest,
    PartnerWorkspaceCodeLinkResponse,
    PartnerWorkspaceCodeQrRequest,
    PartnerWorkspaceCodeQrResponse,
    PartnerWorkspaceCodeResponse,
    PartnerWorkspaceCommercialCapabilitiesResponse,
    PartnerWorkspaceConversionRecordResponse,
    PartnerWorkspaceFinanceCurrencySummaryResponse,
    PartnerWorkspaceFinanceSummaryResponse,
    PartnerWorkspaceIntegrationCredentialResponse,
    PartnerWorkspaceIntegrationDeliveryLogResponse,
    PartnerWorkspaceLegalDocumentResponse,
    PartnerWorkspaceMemberResponse,
    PartnerWorkspaceOrganizationProfileResponse,
    PartnerWorkspacePayoutAccountEligibilityResponse,
    PartnerWorkspacePayoutAccountResponse,
    PartnerWorkspacePayoutHistoryResponse,
    PartnerWorkspacePostbackReadinessResponse,
    PartnerWorkspaceProgramLaneResponse,
    PartnerWorkspaceProgramReadinessItemResponse,
    PartnerWorkspaceProgramsResponse,
    PartnerWorkspaceReportExportRedactionResponse,
    PartnerWorkspaceReportExportResponse,
    PartnerWorkspaceReportingReconciliationResponse,
    PartnerWorkspaceReportingSummaryMetricResponse,
    PartnerWorkspaceReportingSummaryResponse,
    PartnerWorkspaceResellerVoucherBatchResponse,
    PartnerWorkspaceResponse,
    PartnerWorkspaceReviewRequestResponse,
    PartnerWorkspaceRoleResponse,
    PartnerWorkspaceSettingsResponse,
    PartnerWorkspaceSettlementSandboxEligibilityResponse,
    PartnerWorkspaceSettlementSandboxMetricResponse,
    PartnerWorkspaceSettlementSandboxPolicyResponse,
    PartnerWorkspaceSettlementSandboxSimulationResponse,
    PartnerWorkspaceThreadEventResponse,
    PartnerWorkspaceTrafficDeclarationResponse,
    PromotePartnerRequest,
    PromotePartnerResponse,
    RequestPartnerApplicationInfoRequest,
    RequestPartnerWorkspaceResellerVoucherBatchRequest,
    RequestPartnerWorkspaceResellerVoucherBatchResponse,
    RotatePartnerWorkspaceIntegrationCredentialRequest,
    RotatePartnerWorkspaceIntegrationCredentialResponse,
    SchedulePartnerWorkspaceReportExportRequest,
    SubmitPartnerWorkspaceCaseResponseRequest,
    SubmitPartnerWorkspaceCreativeApprovalRequest,
    SubmitPartnerWorkspaceReviewRequestResponseRequest,
    SubmitPartnerWorkspaceTrafficDeclarationRequest,
    UpdateMarkupRequest,
    UpdatePartnerLaneApplicationRequest,
    UpdatePartnerWorkspaceCodeRequest,
    UpdatePartnerWorkspaceCodeStatusRequest,
    UpdatePartnerWorkspaceMemberRequest,
    UpdatePartnerWorkspaceOrganizationProfileRequest,
    UpdatePartnerWorkspaceSettingsRequest,
    UpdatePartnerWorkspaceStatusRequest,
    UpsertPartnerApplicationDraftRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["partners"])

_WORKSPACE_REVIEW_REQUEST_SUBJECT_KIND = "review_request"
_WORKSPACE_CASE_SUBJECT_KIND = "case"
_WORKSPACE_REPORT_EXPORT_SUBJECT_KIND = "report_export"
_WORKSPACE_ADMIN_OPS_SUBJECT_KIND = "admin_ops"
_WORKSPACE_PARTNER_CODE_SUBJECT_KIND = "partner_code"
_WORKSPACE_REVIEW_REQUEST_RESPONSE_ACTION = "partner_response_submitted"
_WORKSPACE_CASE_REPLY_ACTION = "partner_reply"
_WORKSPACE_CASE_READY_FOR_OPS_ACTION = "partner_ready_for_ops"

_WORKSPACE_REPORT_EXPORT_SCHEDULE_ACTION = "partner_export_requested"
_WORKSPACE_STATUS_CHANGED_ACTION = "workspace_status_changed"
_WORKSPACE_PARTNER_CODE_STATUS_CHANGED_ACTION = "partner_code_status_changed"
_WORKSPACE_MEMBER_STATUSES = {"active", "invited", "limited"}
_ADMIN_READ_PARTNER_PERMISSIONS = frozenset(
    {
        PartnerPermission.WORKSPACE_READ.value,
        PartnerPermission.MEMBERSHIP_READ.value,
        PartnerPermission.CODES_READ.value,
        PartnerPermission.EARNINGS_READ.value,
        PartnerPermission.PAYOUTS_READ.value,
        PartnerPermission.TRAFFIC_READ.value,
        PartnerPermission.INTEGRATIONS_READ.value,
    }
)
_WORKSPACE_OWNER_ROLE_KEY = "owner"
_WORKSPACE_ADMIN_STATUS_VALUES = {
    "draft",
    "email_verified",
    "submitted",
    "under_review",
    "needs_info",
    "approved_probation",
    "active",
    "restricted",
    "suspended",
    "rejected",
    "terminated",
}
_WORKSPACE_CAMPAIGN_CHANNELS = {
    "content",
    "telegram",
    "paid_social",
    "search",
    "storefront",
}
_WORKSPACE_NOTIFICATION_PREF_DEFAULTS = {
    "email_security": True,
    "email_marketing": False,
    "partner_payout_status_emails": True,
    "partner_application_updates": True,
    "partner_case_messages": True,
    "partner_compliance_alerts": True,
    "partner_integration_alerts": True,
}
_WORKSPACE_LEGAL_DOCUMENT_DEFINITIONS = (
    ("program_terms", "Program Terms", "2026.04"),
    ("payout_terms", "Payout Terms", "2026.04"),
    ("traffic_policy", "Traffic Policy", "2026.04"),
    ("disclosure_guidelines", "Disclosure Guidelines", "2026.04"),
)


def _serialize_workspace_member(
    *,
    membership,
    role,
    operator: AdminUserModel | None = None,
) -> PartnerWorkspaceMemberResponse:
    return PartnerWorkspaceMemberResponse(
        id=membership.id,
        admin_user_id=membership.admin_user_id,
        operator_login=operator.login if operator is not None else None,
        operator_email=operator.email if operator is not None else None,
        operator_display_name=(operator.display_name or operator.login if operator is not None else None),
        role_id=membership.role_id,
        role_key=role.role_key,
        role_display_name=role.display_name,
        membership_status=membership.membership_status,
        permission_keys=list(role.permission_keys),
        invited_by_admin_user_id=membership.invited_by_admin_user_id,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
    )


def _serialize_workspace_response(
    workspace_payload: dict,
    *,
    access: PartnerWorkspaceAccess | None = None,
) -> PartnerWorkspaceResponse:
    account = workspace_payload["account"]
    stats = workspace_payload["stats"]
    role_by_id = workspace_payload["role_by_id"]
    operator_by_id = workspace_payload.get("operator_by_id", {})
    members = [
        _serialize_workspace_member(
            membership=membership,
            role=role_by_id[membership.role_id],
            operator=operator_by_id.get(membership.admin_user_id),
        )
        for membership in workspace_payload["memberships"]
        if membership.role_id in role_by_id
    ]
    current_role_key = access.role.role_key if access and access.role else None
    current_permission_keys = sorted(access.permission_keys) if access else []
    return PartnerWorkspaceResponse(
        id=account.id,
        account_key=account.account_key,
        display_name=account.display_name,
        status=account.status,
        legacy_owner_user_id=account.legacy_owner_user_id,
        created_by_admin_user_id=account.created_by_admin_user_id,
        code_count=int(stats.get("code_count", 0) or 0),
        active_code_count=int(stats.get("active_code_count", 0) or 0),
        total_clients=int(stats.get("total_clients", 0) or 0),
        total_earned=float(stats.get("total_earned", 0) or 0),
        last_activity_at=stats.get("last_activity_at"),
        current_role_key=current_role_key,
        current_permission_keys=current_permission_keys,
        members=members,
    )


def _build_workspace_role_key_by_admin_user_id(workspace_payload: dict) -> dict[UUID, str]:
    role_by_id = workspace_payload["role_by_id"]
    return {
        membership.admin_user_id: role_by_id[membership.role_id].role_key
        for membership in workspace_payload["memberships"]
        if membership.role_id in role_by_id
    }


def _build_internal_admin_read_workspace_access(workspace) -> PartnerWorkspaceAccess:
    return PartnerWorkspaceAccess(
        workspace=workspace,
        membership=None,
        role=None,
        permission_keys=_ADMIN_READ_PARTNER_PERMISSIONS,
        is_internal_admin_override=True,
    )


async def _count_active_workspace_owners(
    repo: PartnerAccountRepository,
    *,
    workspace_id: UUID,
) -> int:
    memberships = await repo.list_memberships(workspace_id)
    owner_count = 0
    for item in memberships:
        if item.membership_status != "active":
            continue
        item_role = await repo.get_role_by_id(item.role_id)
        if item_role is not None and item_role.role_key == _WORKSPACE_OWNER_ROLE_KEY:
            owner_count += 1
    return owner_count


async def _enforce_workspace_owner_role_update_guard(
    repo: PartnerAccountRepository,
    *,
    access: PartnerWorkspaceAccess,
    membership,
    current_role_key: str,
    requested_role_key: str,
    requested_membership_status: str,
) -> None:
    touches_owner_role = (
        current_role_key == _WORKSPACE_OWNER_ROLE_KEY or requested_role_key == _WORKSPACE_OWNER_ROLE_KEY
    )
    if not touches_owner_role:
        return

    actor_role_key = access.role.role_key if access.role is not None else None
    if not access.is_internal_admin_override and actor_role_key != _WORKSPACE_OWNER_ROLE_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only partner workspace owners can change owner-role memberships",
        )

    keeps_target_as_active_owner = (
        requested_role_key == _WORKSPACE_OWNER_ROLE_KEY and requested_membership_status == "active"
    )
    if keeps_target_as_active_owner:
        return

    active_owner_count = await _count_active_workspace_owners(
        repo,
        workspace_id=access.workspace.id,
    )
    if (
        current_role_key == _WORKSPACE_OWNER_ROLE_KEY
        and membership.membership_status == "active"
        and active_owner_count <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Partner workspace must keep at least one active owner",
        )


def _build_workspace_notification_preferences(
    current_user: AdminUserModel,
) -> dict[str, bool]:
    prefs = dict(_WORKSPACE_NOTIFICATION_PREF_DEFAULTS)
    prefs.update(current_user.notification_prefs or {})
    return prefs


def _serialize_partner_notification_preferences(
    current_user: AdminUserModel,
) -> PartnerNotificationPreferencesResponse:
    prefs = _build_workspace_notification_preferences(current_user)
    return PartnerNotificationPreferencesResponse(
        email_security=bool(prefs.get("email_security", True)),
        email_marketing=bool(prefs.get("email_marketing", False)),
        partner_payout_status_emails=bool(prefs.get("partner_payout_status_emails", True)),
        partner_application_updates=bool(prefs.get("partner_application_updates", True)),
        partner_case_messages=bool(prefs.get("partner_case_messages", True)),
        partner_compliance_alerts=bool(prefs.get("partner_compliance_alerts", True)),
        partner_integration_alerts=bool(prefs.get("partner_integration_alerts", True)),
    )


def _pref_enabled(current_user: AdminUserModel, key: str) -> bool:
    return bool(_build_workspace_notification_preferences(current_user).get(key, True))


def _notification_state_by_key(
    read_states,
) -> dict[str, object]:
    return {item.notification_key: item for item in read_states}


def _coerce_notification_key(value: str) -> str:
    return value.strip()


def _append_partner_notification(
    *,
    items: list[PartnerNotificationFeedItemResponse],
    read_state_by_key: dict[str, object],
    notification_key: str,
    kind: str,
    tone: str,
    route_slug: str,
    message: str,
    notes: list[str] | None,
    action_required: bool,
    created_at: datetime,
    unread_by_default: bool,
    include_archived: bool,
    source_kind: str | None = None,
    source_id: str | None = None,
    source_event_id: str | None = None,
    source_event_kind: str | None = None,
) -> None:
    normalized_key = _coerce_notification_key(notification_key)
    state = read_state_by_key.get(normalized_key)
    archived_at = getattr(state, "archived_at", None)
    if archived_at is not None and not include_archived:
        return

    read_at = getattr(state, "read_at", None)
    unread = unread_by_default and read_at is None and archived_at is None
    items.append(
        PartnerNotificationFeedItemResponse(
            id=normalized_key,
            kind=kind,
            tone=tone,
            route_slug=route_slug,
            message=message.strip(),
            notes=list(notes or []),
            action_required=action_required,
            unread=unread,
            created_at=_normalize_utc(created_at),
            source_kind=source_kind,
            source_id=source_id,
            source_event_id=source_event_id,
            source_event_kind=source_event_kind,
        )
    )


def _latest_partner_thread_event(
    thread_events: list[PartnerWorkspaceThreadEventResponse] | None,
) -> PartnerWorkspaceThreadEventResponse | None:
    if not thread_events:
        return None
    return max(
        thread_events,
        key=lambda item: (_normalize_utc(item.created_at), item.id),
    )


async def _build_partner_notification_feed(
    *,
    access: PartnerWorkspaceAccess,
    current_user: AdminUserModel,
    db: AsyncSession,
    include_archived: bool = False,
) -> list[PartnerNotificationFeedItemResponse]:
    read_state_by_key = _notification_state_by_key(
        await PartnerNotificationReadStateRepository(db).list_for_workspace_and_actor(
            partner_account_id=access.workspace.id,
            admin_user_id=current_user.id,
        )
    )
    items: list[PartnerNotificationFeedItemResponse] = []

    workflow_events = await ListPartnerWorkspaceWorkflowEventsUseCase(db).execute(
        partner_account_id=access.workspace.id,
    )
    for event in workflow_events:
        if event.action_kind in {"workspace_draft_created", "application_submitted", "application_resubmitted"}:
            if not _pref_enabled(current_user, "partner_application_updates"):
                continue
            _append_partner_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=f"workflow-event:{event.id}",
                kind="workspace_draft" if event.action_kind == "workspace_draft_created" else "application_submitted",
                tone="info",
                route_slug="/application",
                message=event.message,
                notes=[],
                action_required=False,
                created_at=event.created_at,
                unread_by_default=event.created_by_admin_user_id != current_user.id,
                include_archived=include_archived,
                source_kind=event.subject_kind,
                source_id=event.subject_id,
                source_event_id=str(event.id),
                source_event_kind=event.action_kind,
            )
            continue

        if event.action_kind in {"application_approved_probation", "application_waitlisted", "application_rejected"}:
            if not _pref_enabled(current_user, "partner_application_updates"):
                continue
            kind = {
                "application_approved_probation": "application_approved_probation",
                "application_waitlisted": "application_waitlisted",
                "application_rejected": "application_rejected",
            }[event.action_kind]
            tone = (
                "success"
                if event.action_kind == "application_approved_probation"
                else "warning"
                if event.action_kind == "application_waitlisted"
                else "critical"
            )
            route_slug = "/programs" if event.action_kind == "application_approved_probation" else "/application"
            _append_partner_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=f"workflow-event:{event.id}",
                kind=kind,
                tone=tone,
                route_slug=route_slug,
                message=event.message,
                notes=[],
                action_required=event.action_kind == "application_approved_probation",
                created_at=event.created_at,
                unread_by_default=event.created_by_admin_user_id != current_user.id,
                include_archived=include_archived,
                source_kind=event.subject_kind,
                source_id=event.subject_id,
                source_event_id=str(event.id),
                source_event_kind=event.action_kind,
            )
            continue

        if event.action_kind in {"lane_application_approved", "lane_application_declined"}:
            if not _pref_enabled(current_user, "partner_application_updates"):
                continue
            _append_partner_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=f"workflow-event:{event.id}",
                kind="lane_membership_changed",
                tone="success" if event.action_kind == "lane_application_approved" else "warning",
                route_slug="/programs",
                message=event.message,
                notes=[],
                action_required=event.action_kind == "lane_application_approved",
                created_at=event.created_at,
                unread_by_default=event.created_by_admin_user_id != current_user.id,
                include_archived=include_archived,
                source_kind=event.subject_kind,
                source_id=event.subject_id,
                source_event_id=str(event.id),
                source_event_kind=event.action_kind,
            )

    if PartnerPermission.WORKSPACE_READ.value in access.permission_keys:
        review_requests = await _load_workspace_review_requests(access=access, db=db)
        for request in review_requests:
            if request.status != "open" or not _pref_enabled(current_user, "partner_application_updates"):
                continue
            latest_event = _latest_partner_thread_event(request.thread_events)
            _append_partner_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=(
                    f"review-request:{request.id}:{latest_event.id}"
                    if latest_event is not None
                    else f"review-request:{request.id}:open"
                ),
                kind="review_request_opened",
                tone="warning",
                route_slug="/cases",
                message=(
                    latest_event.message
                    if latest_event is not None
                    else f"Review request {request.kind.replace('_', ' ')} is waiting for a partner response."
                ),
                notes=[f"Due date: {request.due_date}"],
                action_required=True,
                created_at=latest_event.created_at if latest_event is not None else request.due_date,
                unread_by_default=latest_event is None or latest_event.created_by_admin_user_id != current_user.id,
                include_archived=include_archived,
                source_kind="review_request",
                source_id=request.id,
                source_event_id=str(latest_event.id) if latest_event is not None else None,
                source_event_kind=latest_event.action_kind if latest_event is not None else "review_request_open",
            )

        cases = await _load_workspace_cases(access=access, db=db)
        for item in cases:
            if (
                item.status == "resolved"
                or item.kind == "requested_info"
                or not _pref_enabled(current_user, "partner_case_messages")
            ):
                continue
            latest_event = _latest_partner_thread_event(item.thread_events)
            _append_partner_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=(
                    f"case:{item.id}:{latest_event.id}"
                    if latest_event is not None
                    else f"case:{item.id}:{item.updated_at}"
                ),
                kind="case_reply_received" if latest_event is not None else "case_created",
                tone="warning" if item.status == "waiting_on_partner" else "info",
                route_slug="/cases",
                message=(
                    latest_event.message
                    if latest_event is not None
                    else f"Case {item.kind.replace('_', ' ')} remains open in the governed partner workflow."
                ),
                notes=list(item.notes or []),
                action_required=item.status in {"open", "waiting_on_partner"},
                created_at=latest_event.created_at if latest_event is not None else item.updated_at,
                unread_by_default=latest_event is None or latest_event.created_by_admin_user_id != current_user.id,
                include_archived=include_archived,
                source_kind="case",
                source_id=item.id,
                source_event_id=str(latest_event.id) if latest_event is not None else None,
                source_event_kind=latest_event.action_kind if latest_event is not None else "case_open",
            )

        workspace_payload = await GetPartnerWorkspaceUseCase(
            PartnerAccountRepository(db),
            PartnerRepository(db),
        ).execute(access.workspace.id)
        role_by_admin_user_id = _build_workspace_role_key_by_admin_user_id(workspace_payload)
        programs = await BuildPartnerWorkspaceProgramsUseCase(db).execute(
            partner_account_id=access.workspace.id,
            workspace_status=access.workspace.status,
            workspace_label=access.workspace.display_name,
        )
        acceptances = await PartnerWorkspaceLegalAcceptanceRepository(db).list_for_workspace(
            access.workspace.id,
        )
        legal_documents = _serialize_workspace_legal_documents(
            workspace=access.workspace,
            programs=programs,
            role_by_admin_user_id=role_by_admin_user_id,
            acceptances=acceptances,
        )
        for document in legal_documents:
            if document.status != "pending_acceptance" or not _pref_enabled(current_user, "partner_compliance_alerts"):
                continue
            _append_partner_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=f"legal-document:{document.id}",
                kind="legal_acceptance_required",
                tone="warning",
                route_slug="/legal",
                message=(
                    f"{document.title} ({document.version}) requires acceptance before governed rollout can continue."
                ),
                notes=list(document.notes or []),
                action_required=True,
                created_at=access.workspace.updated_at,
                unread_by_default=True,
                include_archived=include_archived,
                source_kind="legal_document",
                source_id=document.id,
                source_event_kind="legal_acceptance_required",
            )

    programs = await BuildPartnerWorkspaceProgramsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        workspace_status=access.workspace.status,
        workspace_label=access.workspace.display_name,
    )
    finance_readiness = _get_workspace_program_readiness_status(
        PartnerWorkspaceProgramsResponse(
            canonical_source=programs.canonical_source,
            primary_lane_key=programs.primary_lane_key,
            lane_memberships=[_serialize_workspace_program_lane(item) for item in programs.lane_memberships],
            readiness_items=[_serialize_workspace_program_readiness_item(item) for item in programs.readiness_items],
            updated_at=_normalize_utc(programs.updated_at),
        ),
        "finance",
        default="not_started",
    )
    compliance_readiness = _get_workspace_program_readiness_status(
        PartnerWorkspaceProgramsResponse(
            canonical_source=programs.canonical_source,
            primary_lane_key=programs.primary_lane_key,
            lane_memberships=[_serialize_workspace_program_lane(item) for item in programs.lane_memberships],
            readiness_items=[_serialize_workspace_program_readiness_item(item) for item in programs.readiness_items],
            updated_at=_normalize_utc(programs.updated_at),
        ),
        "compliance",
        default="not_started",
    )
    technical_readiness = _get_workspace_program_readiness_status(
        PartnerWorkspaceProgramsResponse(
            canonical_source=programs.canonical_source,
            primary_lane_key=programs.primary_lane_key,
            lane_memberships=[_serialize_workspace_program_lane(item) for item in programs.lane_memberships],
            readiness_items=[_serialize_workspace_program_readiness_item(item) for item in programs.readiness_items],
            updated_at=_normalize_utc(programs.updated_at),
        ),
        "technical",
        default="not_required",
    )
    governance_state = _derive_partner_governance_state(
        workspace_status=access.workspace.status,
        programs=PartnerWorkspaceProgramsResponse(
            canonical_source=programs.canonical_source,
            primary_lane_key=programs.primary_lane_key,
            lane_memberships=[_serialize_workspace_program_lane(item) for item in programs.lane_memberships],
            readiness_items=[_serialize_workspace_program_readiness_item(item) for item in programs.readiness_items],
            updated_at=_normalize_utc(programs.updated_at),
        ),
    )
    blocked_reasons = _build_partner_session_blocked_reasons(
        workspace_status=access.workspace.status,
        programs=PartnerWorkspaceProgramsResponse(
            canonical_source=programs.canonical_source,
            primary_lane_key=programs.primary_lane_key,
            lane_memberships=[_serialize_workspace_program_lane(item) for item in programs.lane_memberships],
            readiness_items=[_serialize_workspace_program_readiness_item(item) for item in programs.readiness_items],
            updated_at=_normalize_utc(programs.updated_at),
        ),
        finance_readiness=finance_readiness,
        compliance_readiness=compliance_readiness,
        technical_readiness=technical_readiness,
        governance_state=governance_state,
    )

    for reason in blocked_reasons:
        if reason.code == "finance_blocked" and _pref_enabled(current_user, "partner_payout_status_emails"):
            _append_partner_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=f"blocked-reason:{reason.code}",
                kind="payout_blocked",
                tone="critical",
                route_slug="/finance",
                message="Payout execution remains blocked until finance readiness is restored.",
                notes=list(reason.notes or []),
                action_required=True,
                created_at=access.workspace.updated_at,
                unread_by_default=True,
                include_archived=include_archived,
                source_kind="blocked_reason",
                source_id=reason.code,
                source_event_kind=reason.code,
            )
        if (
            reason.code.startswith("workspace_status:") or reason.code.startswith("governance_state:")
        ) and _pref_enabled(current_user, "partner_compliance_alerts"):
            _append_partner_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=f"blocked-reason:{reason.code}",
                kind="governance_action_applied",
                tone="critical" if reason.severity == "critical" else "warning",
                route_slug="/compliance",
                message="Governance posture changed and the partner workspace surface is now constrained.",
                notes=list(reason.notes or []),
                action_required=True,
                created_at=access.workspace.updated_at,
                unread_by_default=True,
                include_archived=include_archived,
                source_kind="blocked_reason",
                source_id=reason.code,
                source_event_kind=reason.code,
            )

    if PartnerPermission.EARNINGS_READ.value in access.permission_keys:
        statements = await ListPartnerStatementsUseCase(db).execute(
            partner_account_id=access.workspace.id,
            limit=20,
            offset=0,
        )
        for statement in statements:
            if statement.statement_status != PartnerStatementStatus.CLOSED.value or not _pref_enabled(
                current_user, "partner_payout_status_emails"
            ):
                continue
            _append_partner_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=f"statement:{statement.id}:{statement.statement_status}",
                kind="statement_ready",
                tone="success",
                route_slug="/finance",
                message=f"Statement {statement.statement_key} is closed and ready for finance review.",
                notes=[],
                action_required=False,
                created_at=statement.closed_at or statement.updated_at,
                unread_by_default=True,
                include_archived=include_archived,
                source_kind="statement",
                source_id=str(statement.id),
                source_event_kind="statement_ready",
            )

    if PartnerPermission.INTEGRATIONS_READ.value in access.permission_keys:
        integration_logs = await BuildPartnerWorkspaceIntegrationDeliveryLogsUseCase(db).execute(
            partner_account_id=access.workspace.id,
            workspace_status=access.workspace.status,
            workspace_key=access.workspace.account_key,
            workspace_label=access.workspace.display_name,
        )
        for log in integration_logs:
            if log.status != "failed" or not _pref_enabled(current_user, "partner_integration_alerts"):
                continue
            _append_partner_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=f"integration-log:{log.id}:{log.status}",
                kind="integration_delivery_failed",
                tone="critical",
                route_slug="/integrations",
                message=f"Integration delivery to {log.destination} failed and requires follow-up.",
                notes=list(log.notes or []),
                action_required=True,
                created_at=log.last_attempt_at,
                unread_by_default=True,
                include_archived=include_archived,
                source_kind="integration_delivery_log",
                source_id=log.id,
                source_event_kind="integration_delivery_failed",
            )

    items.sort(
        key=lambda item: (_normalize_utc(item.created_at), item.id),
        reverse=True,
    )
    return items


async def _build_partner_notification_counters(
    *,
    access: PartnerWorkspaceAccess,
    current_user: AdminUserModel,
    db: AsyncSession,
) -> PartnerNotificationCountersResponse:
    items = await _build_partner_notification_feed(
        access=access,
        current_user=current_user,
        db=db,
        include_archived=False,
    )
    return PartnerNotificationCountersResponse(
        total_notifications=len(items),
        unread_notifications=sum(1 for item in items if item.unread),
        action_required_notifications=sum(1 for item in items if item.action_required),
    )


def _serialize_workspace_organization_profile_response(
    *,
    workspace,
    profile,
    primary_lane: str | None,
    current_user: AdminUserModel,
) -> PartnerWorkspaceOrganizationProfileResponse:
    return PartnerWorkspaceOrganizationProfileResponse(
        partner_account_id=workspace.id,
        workspace_name=workspace.display_name,
        website=profile.website or "",
        country=profile.country or "",
        operating_regions=profile.operating_regions or "",
        languages=profile.languages or "",
        primary_lane=primary_lane,
        contact_name=profile.contact_name or "",
        contact_email=profile.contact_email or current_user.email or "",
        support_contact=profile.support_contact or "",
        technical_contact=profile.technical_contact or "",
        finance_contact=profile.finance_contact or "",
        business_description=profile.business_description or "",
        acquisition_channels=profile.acquisition_channels or "",
        updated_at=_normalize_utc(profile.updated_at),
    )


def _serialize_workspace_settings_response(
    *,
    workspace,
    profile,
    current_user: AdminUserModel,
    access: PartnerWorkspaceAccess,
) -> PartnerWorkspaceSettingsResponse:
    prefs = _build_workspace_notification_preferences(current_user)
    return PartnerWorkspaceSettingsResponse(
        partner_account_id=workspace.id,
        operator_email=current_user.email,
        operator_display_name=current_user.display_name or current_user.login,
        operator_role=access.role.role_key if access.role is not None else None,
        is_email_verified=current_user.is_email_verified,
        preferred_language=current_user.language,
        preferred_currency=profile.preferred_currency,
        workspace_security_alerts=bool(prefs.get("email_security", True)),
        payout_status_emails=bool(prefs.get("partner_payout_status_emails", True)),
        product_announcements=bool(prefs.get("email_marketing", False)),
        require_mfa_for_workspace=profile.require_mfa_for_workspace,
        prefer_passkeys=profile.prefer_passkeys,
        reviewed_active_sessions=profile.reviewed_active_sessions,
        updated_at=_normalize_utc(profile.updated_at),
    )


def _can_accept_workspace_legal_document(access: PartnerWorkspaceAccess) -> bool:
    if access.is_internal_admin_override:
        return True
    if access.role is None:
        return False
    return access.role.role_key in {"owner", "manager"}


def _serialize_workspace_legal_documents(
    *,
    workspace,
    programs,
    role_by_admin_user_id: dict[UUID, str],
    acceptances: list[PartnerWorkspaceLegalAcceptanceModel],
) -> list[PartnerWorkspaceLegalDocumentResponse]:
    acceptance_by_document = {(item.document_kind, item.document_version): item for item in acceptances}

    requires_acceptance = workspace.status in {"approved_probation", "active", "restricted"}
    definitions = list(_WORKSPACE_LEGAL_DOCUMENT_DEFINITIONS)
    has_reseller_lane = any(item.lane_key == "reseller_api" for item in programs.lane_memberships)
    if has_reseller_lane:
        definitions.append(("reseller_annex", "Reseller Annex", "2026.04"))

    documents: list[PartnerWorkspaceLegalDocumentResponse] = []
    for kind, title, version in definitions:
        accepted = acceptance_by_document.get((kind, version))
        status_value = "read_only"
        if requires_acceptance:
            status_value = "accepted" if accepted is not None else "pending_acceptance"
        documents.append(
            PartnerWorkspaceLegalDocumentResponse(
                id=f"{kind}:{version}",
                kind=kind,
                title=title,
                version=version,
                status=status_value,
                accepted_at=_normalize_utc(accepted.accepted_at) if accepted is not None else None,
                accepted_by_role_key=(
                    role_by_admin_user_id.get(accepted.accepted_by_admin_user_id)
                    if accepted is not None and accepted.accepted_by_admin_user_id is not None
                    else None
                ),
                notes=[
                    f"Workspace status: {workspace.status}",
                    f"Primary lane: {programs.primary_lane_key or 'none'}",
                ],
            )
        )
    return documents


def _serialize_workspace_code(code_model) -> PartnerWorkspaceCodeResponse:
    public_token = _public_token_for_code(code_model)
    lifecycle_status = str(
        getattr(code_model, "lifecycle_status", None) or ("active" if code_model.is_active else "paused")
    )
    code_normalized = getattr(code_model, "code_normalized", None) or str(code_model.code).strip().upper()
    return PartnerWorkspaceCodeResponse(
        id=code_model.id,
        partner_account_id=code_model.partner_account_id,
        partner_user_id=code_model.partner_user_id,
        code=code_model.code,
        code_normalized=code_normalized,
        masked_code=mask_partner_code(code_model.code),
        markup_pct=float(code_model.markup_pct),
        is_active=bool(code_model.is_active),
        lifecycle_status=lifecycle_status,
        approval_status=str(getattr(code_model, "approval_status", None) or "approved"),
        owner_type=str(getattr(code_model, "owner_type", None) or "affiliate"),
        lane_key=str(getattr(code_model, "lane_key", None) or "creator_affiliate"),
        attribution_model=str(getattr(code_model, "attribution_model", None) or "last_eligible_touch"),
        attribution_window_seconds=int(getattr(code_model, "attribution_window_seconds", None) or 30 * 24 * 60 * 60),
        share_url=build_share_url(public_token),
        default_destination_url=build_customer_public_url(
            destination_path=getattr(code_model, "destination_path", None),
        ),
        destination_path=getattr(code_model, "destination_path", None),
        allowed_channels=_list_or_default(
            getattr(code_model, "allowed_channels", None),
            ["content", "telegram", "storefront"],
        ),
        allowed_storefront_ids=_list_or_default(getattr(code_model, "allowed_storefront_ids", None), ["*"]),
        allowed_geographies=_list_or_default(getattr(code_model, "allowed_geographies", None), ["*"]),
        sub_id_schema=dict(getattr(code_model, "sub_id_schema", None) or {}),
        policy_version_id=getattr(code_model, "policy_version_id", None),
        commission_contract_id=getattr(code_model, "commission_contract_id", None),
        active_from=getattr(code_model, "active_from", None),
        expires_at=getattr(code_model, "expires_at", None),
        paused_at=getattr(code_model, "paused_at", None),
        revoked_at=getattr(code_model, "revoked_at", None),
        version=int(getattr(code_model, "version", None) or 1),
        available_actions=_available_code_actions(lifecycle_status),
        created_at=code_model.created_at,
        updated_at=code_model.updated_at,
    )


def _public_token_for_code(code_model: PartnerCodeModel) -> str:
    return str(getattr(code_model, "public_slug", None) or build_public_token_for_code_id(code_model.id))


def _list_or_default(value, default: list[str]) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return list(default)


def _available_code_actions(lifecycle_status: str) -> list[str]:
    status_value = lifecycle_status.strip().lower()
    if status_value == "active":
        return ["create_link", "download_qr", "pause", "revoke", "archive"]
    if status_value == "paused":
        return ["create_link", "download_qr", "activate", "revoke", "archive"]
    if status_value == "revoked":
        return ["archive"]
    if status_value == "archived":
        return []
    return ["create_link", "download_qr"]


_LINK_DESTINATION_PATHS = {
    "register": "/register",
    "pricing": "/pricing",
    "checkout": "/checkout",
    "download": "/download",
}
_APPROVED_CAMPAIGN_PREFIXES = ("/campaigns/", "/campaign/", "/landing/", "/lp/")
_APPROVED_STOREFRONT_PREFIXES = ("/storefronts/", "/storefront/", "/checkout")


async def _allocate_public_slug(repo: PartnerRepository) -> str:
    for _ in range(32):
        candidate = generate_public_slug()
        code_exists = await repo.get_code_by_public_slug(candidate) is not None
        link_exists = await repo.get_code_link_by_public_slug(candidate) is not None
        if not code_exists and not link_exists:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Could not allocate unique partner public slug",
    )


async def _resolve_unique_partner_code(repo: PartnerRepository, requested_code: str | None) -> str:
    if requested_code:
        normalized = normalize_partner_code(requested_code)
        if await repo.get_code_by_code(normalized) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Partner code already exists")
        return normalized
    for _ in range(16):
        candidate = generate_partner_code()
        if await repo.get_code_by_code(candidate) is None:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Could not allocate unique partner code",
    )


_PARTNER_CODE_CREATE_BLOCKED_FIELDS = frozenset(
    {
        "markup_pct",
        "owner_type",
        "lane_key",
        "attribution_model",
        "attribution_window_seconds",
        "allowed_channels",
        "allowed_storefront_ids",
        "allowed_geographies",
    }
)
_PARTNER_CODE_UPDATE_BLOCKED_FIELDS = _PARTNER_CODE_CREATE_BLOCKED_FIELDS | frozenset({"lifecycle_status"})
_PARTNER_CODE_REVENUE_TERM_FIELDS = frozenset({"markup_pct"})


def _can_manage_partner_code_revenue_terms(access: PartnerWorkspaceAccess) -> bool:
    return access.is_internal_admin_override or PartnerPermission.PAYOUTS_WRITE.value in access.permission_keys


def _assert_no_sensitive_partner_code_fields(
    fields_set: set[str],
    *,
    operation: str,
    allow_revenue_terms: bool = False,
) -> None:
    blocked_fields = (
        _PARTNER_CODE_CREATE_BLOCKED_FIELDS if operation == "create" else _PARTNER_CODE_UPDATE_BLOCKED_FIELDS
    )
    if allow_revenue_terms:
        blocked_fields = blocked_fields - _PARTNER_CODE_REVENUE_TERM_FIELDS
    blocked = sorted(fields_set & blocked_fields)
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Partner code commercial fields require approval workflow: {', '.join(blocked)}",
        )


def _idempotency_request_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


async def _get_idempotency_record(
    db: AsyncSession,
    *,
    scope: str,
    idempotency_key: str,
) -> ApiIdempotencyRecordModel | None:
    result = await db.execute(
        select(ApiIdempotencyRecordModel).where(
            ApiIdempotencyRecordModel.scope == scope,
            ApiIdempotencyRecordModel.idempotency_key == idempotency_key,
        )
    )
    return result.scalars().first()


def _validated_owner_type(owner_type: str) -> str:
    value = owner_type.strip().lower()
    if value not in {"affiliate", "performance", "reseller"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported partner owner_type")
    return value


def _clean_string_list(value: list[str] | None, *, default: list[str]) -> list[str]:
    items = [str(item).strip() for item in list(value or []) if str(item).strip()]
    return items or list(default)


def _normalize_destination_path(destination_path: str | None) -> str | None:
    if destination_path is None:
        return None
    stripped = destination_path.strip()
    if not stripped:
        return None
    if stripped.startswith(("http://", "https://", "//")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="External destination URLs are not allowed")
    if not stripped.startswith("/"):
        stripped = f"/{stripped}"
    return stripped[:500]


def _resolve_base_commission_pct(tiers: list[dict]) -> Decimal:
    commission = Decimal("0")
    for tier in sorted(tiers or [], key=lambda item: int(item.get("min_clients", 0) or 0)):
        if int(tier.get("min_clients", 0) or 0) <= 0:
            commission = Decimal(str(tier.get("commission_pct", 0) or 0))
    return commission


def _resolve_link_destination(destination_key: str | None, destination_path: str | None) -> tuple[str, str]:
    normalized_path = _normalize_destination_path(destination_path)
    normalized_key = (destination_key or "").strip().lower()
    if not normalized_key:
        normalized_key = _infer_destination_key(normalized_path)
    if normalized_key in _LINK_DESTINATION_PATHS:
        expected_path = _LINK_DESTINATION_PATHS[normalized_key]
        if normalized_path is not None and normalized_path != expected_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"destination_path does not match destination_key={normalized_key}",
            )
        return normalized_key, expected_path
    if normalized_key == "approved_campaign_landing":
        if normalized_path is None or not normalized_path.startswith(_APPROVED_CAMPAIGN_PREFIXES):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="approved_campaign_landing requires an approved internal campaign path",
            )
        return normalized_key, normalized_path
    if normalized_key == "approved_storefront":
        if normalized_path is None or not normalized_path.startswith(_APPROVED_STOREFRONT_PREFIXES):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="approved_storefront requires an approved internal storefront path",
            )
        return normalized_key, normalized_path
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported destination_key")


def _infer_destination_key(destination_path: str | None) -> str:
    if not destination_path:
        return "register"
    for key, path in _LINK_DESTINATION_PATHS.items():
        if destination_path == path:
            return key
    if destination_path.startswith(_APPROVED_CAMPAIGN_PREFIXES):
        return "approved_campaign_landing"
    if destination_path.startswith(_APPROVED_STOREFRONT_PREFIXES):
        return "approved_storefront"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported partner link destination")


def _normalize_link_kind(link_kind: str | None) -> str:
    value = (link_kind or "deep_link").strip().lower()
    if value not in {"default", "deep_link", "campaign", "storefront", "qr"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported partner link_kind")
    return value


def _clean_link_string_mapping(value: dict[str, str] | None, *, max_value_length: int) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, raw_value in dict(value or {}).items():
        key_text = str(key).strip()
        value_text = str(raw_value).strip()
        if not key_text or not value_text or len(key_text) > 64:
            continue
        cleaned[key_text] = value_text[:max_value_length]
    return cleaned


async def _allocate_code_link_slug(repo: PartnerRepository) -> str:
    for _ in range(32):
        candidate = generate_public_slug()
        link_exists = await repo.get_code_link_by_public_slug(candidate) is not None
        code_exists = await repo.get_code_by_public_slug(candidate) is not None
        if not link_exists and not code_exists:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Could not allocate unique partner link slug",
    )


async def _ensure_default_code_link(db: AsyncSession, code_model: PartnerCodeModel) -> PartnerCodeLinkModel:
    repo = PartnerRepository(db)
    existing = await repo.get_default_code_link(code_model.id)
    if existing is not None:
        return existing
    if code_model.partner_account_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Partner code has no workspace owner")
    public_slug = _public_token_for_code(code_model)
    if await repo.get_code_link_by_public_slug(public_slug) is not None:
        public_slug = await _allocate_code_link_slug(repo)
    destination_key, destination_path = _resolve_link_destination(None, code_model.destination_path)
    now = datetime.now(UTC)
    link = PartnerCodeLinkModel(
        public_slug=public_slug,
        partner_code_id=code_model.id,
        partner_account_id=code_model.partner_account_id,
        link_kind="default",
        destination_key=destination_key,
        destination_path=destination_path,
        locale=None,
        sale_channel=None,
        campaign_params={},
        sub_ids={},
        status="active",
        active_from=code_model.active_from,
        expires_at=code_model.expires_at,
        created_at=now,
        updated_at=now,
    )
    return await repo.create_code_link(link)


async def _create_code_link(
    db: AsyncSession,
    *,
    code_model: PartnerCodeModel,
    destination_key: str | None,
    destination_path: str | None,
    link_kind: str | None,
    locale: str | None,
    sale_channel: str | None,
    campaign_params: dict[str, str] | None,
    sub_ids: dict[str, str] | None,
    active_from: datetime | None,
    expires_at: datetime | None,
) -> PartnerCodeLinkModel:
    if code_model.partner_account_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Partner code has no workspace owner")
    key, path = _resolve_link_destination(destination_key, destination_path)
    repo = PartnerRepository(db)
    now = datetime.now(UTC)
    link = PartnerCodeLinkModel(
        public_slug=await _allocate_code_link_slug(repo),
        partner_code_id=code_model.id,
        partner_account_id=code_model.partner_account_id,
        link_kind=_normalize_link_kind(link_kind),
        destination_key=key,
        destination_path=path,
        locale=locale.strip()[:16] if locale and locale.strip() else None,
        sale_channel=sale_channel.strip()[:40] if sale_channel and sale_channel.strip() else None,
        campaign_params=_clean_link_string_mapping(campaign_params, max_value_length=200),
        sub_ids=_clean_link_string_mapping(sub_ids, max_value_length=160),
        status="active",
        active_from=active_from,
        expires_at=expires_at,
        created_at=now,
        updated_at=now,
    )
    return await repo.create_code_link(link)


def _serialize_code_link(link: PartnerCodeLinkModel) -> PartnerWorkspaceCodeLinkResponse:
    return PartnerWorkspaceCodeLinkResponse(
        link_id=link.id,
        code_id=link.partner_code_id,
        public_slug=link.public_slug,
        share_url=build_share_url(link.public_slug),
        link_kind=link.link_kind,
        destination_key=link.destination_key,
        destination_path=link.destination_path,
        locale=link.locale,
        sale_channel=link.sale_channel,
        campaign_params={str(key): str(value) for key, value in dict(link.campaign_params or {}).items()},
        sub_ids={str(key): str(value) for key, value in dict(link.sub_ids or {}).items()},
        status=link.status,
        active_from=link.active_from,
        expires_at=link.expires_at,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


async def _get_workspace_code_or_404(
    db: AsyncSession,
    workspace_id: UUID,
    code_id: UUID,
) -> PartnerCodeModel:
    code_model = await PartnerRepository(db).get_code_by_id(code_id)
    if code_model is None or code_model.partner_account_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner code not found")
    return code_model


def _assert_code_version_matches(request: Request, code_model: PartnerCodeModel) -> None:
    raw_if_match = (request.headers.get("If-Match") or "").strip()
    if not raw_if_match:
        return
    current = str(int(code_model.version or 1))
    accepted = {current, f'"{current}"', f'W/"{current}"'}
    if raw_if_match not in accepted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Partner code version conflict")


_CODE_LIFECYCLE_TRANSITIONS = {
    "active": {"paused", "revoked", "archived"},
    "paused": {"active", "revoked", "archived"},
    "revoked": {"archived"},
    "archived": set(),
}


def _apply_code_lifecycle(
    code_model: PartnerCodeModel,
    lifecycle_status: str,
    *,
    reason: str | None,
) -> tuple[str, str]:
    value = lifecycle_status.strip().lower()
    now = datetime.now(UTC)
    if value not in {"active", "paused", "revoked", "archived"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported lifecycle_status")
    previous = str(getattr(code_model, "lifecycle_status", None) or ("active" if code_model.is_active else "paused"))
    if previous == value:
        return previous, value
    allowed_next = _CODE_LIFECYCLE_TRANSITIONS.get(previous, set())
    if value not in allowed_next:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Partner code cannot transition from {previous} to {value}",
        )
    code_model.lifecycle_status = value
    code_model.is_active = value == "active"
    if value == "active":
        code_model.paused_at = None
        code_model.active_from = code_model.active_from or now
    elif value == "paused":
        code_model.paused_at = now
    elif value == "revoked":
        code_model.revoked_at = now
    return previous, value


async def _append_code_event(
    db: AsyncSession,
    *,
    code_model: PartnerCodeModel,
    event_type: str,
    previous_status: str | None,
    next_status: str | None,
    reason: str | None,
    payload: dict[str, object] | None = None,
) -> None:
    db.add(
        PartnerCodeEventModel(
            partner_code_id=code_model.id,
            partner_account_id=code_model.partner_account_id,
            event_type=event_type,
            previous_status=previous_status,
            next_status=next_status,
            reason_code=reason[:120] if reason else None,
            event_payload=dict(payload or {}),
        )
    )
    await db.flush()


async def _change_workspace_code_lifecycle(
    *,
    db: AsyncSession,
    request: Request,
    workspace_id: UUID,
    code_id: UUID,
    lifecycle_status: str,
    reason: str | None,
    operation: str,
) -> PartnerWorkspaceCodeResponse:
    code_model = await _get_workspace_code_or_404(db, workspace_id, code_id)
    _assert_code_version_matches(request, code_model)
    previous_status, next_status = _apply_code_lifecycle(code_model, lifecycle_status, reason=reason)
    code_model.version = int(code_model.version or 1) + 1
    await _append_code_event(
        db,
        code_model=code_model,
        event_type=f"code.{lifecycle_status}",
        previous_status=previous_status,
        next_status=next_status,
        reason=reason,
        payload={"operation": operation},
    )
    updated = await PartnerRepository(db).update_code(code_model)
    await db.commit()
    await db.refresh(updated)
    track_partner_operation(operation=operation)
    return _serialize_workspace_code(updated)


def _build_code_qr_svg(share_url: str, size: int) -> str:
    try:
        import segno

        output = io.BytesIO()
        qr = segno.make(share_url, error="m")
        qr.save(
            output,
            kind="svg",
            xmldecl=False,
            svgclass="cybervpn-partner-qr",
            scale=max(size // 33, 1),
            border=2,
        )
        return output.getvalue().decode("utf-8")
    except Exception as exc:
        logger.exception("partner_workspace_code_qr_generation_failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Partner QR generation failed",
        ) from exc


def _serialize_workspace_program_lane(
    item,
) -> PartnerWorkspaceProgramLaneResponse:
    return PartnerWorkspaceProgramLaneResponse(
        lane_key=item.lane_key,
        membership_status=item.membership_status,
        owner_context_label=item.owner_context_label,
        pilot_cohort_id=item.pilot_cohort_id,
        pilot_cohort_status=item.pilot_cohort_status,
        runbook_gate_status=item.runbook_gate_status,
        blocking_reason_codes=list(item.blocking_reason_codes),
        warning_reason_codes=list(item.warning_reason_codes),
        restriction_notes=list(item.restriction_notes),
        readiness_notes=list(item.readiness_notes),
        updated_at=_normalize_utc(item.updated_at),
    )


def _serialize_workspace_program_readiness_item(
    item,
) -> PartnerWorkspaceProgramReadinessItemResponse:
    return PartnerWorkspaceProgramReadinessItemResponse(
        key=item.key,
        status=item.status,
        blocking_reason_codes=list(item.blocking_reason_codes),
        notes=list(item.notes),
    )


def _build_partner_session_principal_response(
    *,
    user: AdminUserModel,
    current_realm: RealmResolution,
) -> PartnerSessionPrincipalResponse:
    return PartnerSessionPrincipalResponse(
        id=user.id,
        login=user.login,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        auth_realm_id=current_realm.auth_realm.id,
        auth_realm_key=current_realm.realm_key,
        audience=current_realm.audience,
        principal_type=get_principal_type_for_realm(current_realm),
        scope_family=get_scope_family_for_realm(current_realm),
    )


def _require_partner_realm(current_realm: RealmResolution) -> None:
    if current_realm.realm_type != "partner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner realm session is required for this route",
        )


async def _enforce_partner_passkey_fresh_auth(
    *,
    request: Request,
    redis_client: redis.Redis,
    current_user: AdminUserModel,
    current_realm: RealmResolution,
    action: str,
) -> None:
    await enforce_passkey_fresh_auth(
        request=request,
        redis_client=redis_client,
        principal_subject=str(current_user.id),
        principal_class=get_principal_type_for_realm(current_realm),
        auth_realm_id=str(current_realm.auth_realm.id),
        realm_key=current_realm.realm_key,
        action=action,
    )


async def _resolve_partner_session_workspace_access(
    *,
    current_user: AdminUserModel,
    db: AsyncSession,
    workspace_id: UUID | None = None,
) -> PartnerWorkspaceAccess:
    partner_account_repo = PartnerAccountRepository(db)
    accounts = await partner_account_repo.list_accounts_for_admin_user(current_user.id)
    if not accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner workspace is not available for the current session",
        )

    selected_workspace = accounts[0]
    if workspace_id is not None:
        selected_workspace = next((item for item in accounts if item.id == workspace_id), None)
        if selected_workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Partner workspace is not available for the current session",
            )

    return await resolve_partner_workspace_access(
        workspace_id=selected_workspace.id,
        current_user=current_user,
        db=db,
    )


def _serialize_partner_application_payload(
    payload: dict[str, object] | None,
) -> PartnerApplicationPayloadResponse:
    payload = payload or {}
    return PartnerApplicationPayloadResponse(
        workspace_name=str(payload.get("workspace_name") or ""),
        contact_name=str(payload.get("contact_name") or ""),
        contact_email=str(payload.get("contact_email") or ""),
        country=str(payload.get("country") or ""),
        website=str(payload.get("website") or ""),
        primary_lane=str(payload.get("primary_lane") or ""),
        business_description=str(payload.get("business_description") or ""),
        acquisition_channels=str(payload.get("acquisition_channels") or ""),
        operating_regions=str(payload.get("operating_regions") or ""),
        languages=str(payload.get("languages") or ""),
        support_contact=str(payload.get("support_contact") or ""),
        technical_contact=str(payload.get("technical_contact") or ""),
        finance_contact=str(payload.get("finance_contact") or ""),
        compliance_accepted=payload.get("compliance_accepted") is True,
    )


def _serialize_partner_application_workspace_summary(
    workspace,
    *,
    access: PartnerWorkspaceAccess | None = None,
) -> PartnerApplicationWorkspaceSummaryResponse:
    return PartnerApplicationWorkspaceSummaryResponse(
        id=workspace.id,
        account_key=workspace.account_key,
        display_name=workspace.display_name,
        status=workspace.status,
        current_role_key=access.role.role_key if access and access.role else None,
        current_permission_keys=sorted(access.permission_keys) if access else [],
    )


def _serialize_partner_application_draft_response(
    draft,
    workspace,
    *,
    access: PartnerWorkspaceAccess | None = None,
) -> PartnerApplicationDraftResponse:
    return PartnerApplicationDraftResponse(
        id=draft.id,
        partner_account_id=draft.partner_account_id,
        applicant_admin_user_id=draft.applicant_admin_user_id,
        workspace=_serialize_partner_application_workspace_summary(workspace, access=access),
        draft_payload=_serialize_partner_application_payload(draft.draft_payload),
        review_ready=draft.review_ready,
        submitted_at=_normalize_utc(draft.submitted_at) if draft.submitted_at is not None else None,
        withdrawn_at=_normalize_utc(draft.withdrawn_at) if draft.withdrawn_at is not None else None,
        created_at=_normalize_utc(draft.created_at),
        updated_at=_normalize_utc(draft.updated_at),
    )


def _serialize_partner_lane_application_response(
    lane_application,
) -> PartnerLaneApplicationResponse:
    return PartnerLaneApplicationResponse(
        id=lane_application.id,
        partner_account_id=lane_application.partner_account_id,
        partner_application_draft_id=lane_application.partner_application_draft_id,
        lane_key=lane_application.lane_key,
        status=lane_application.status,
        application_payload=dict(lane_application.application_payload or {}),
        submitted_at=(
            _normalize_utc(lane_application.submitted_at) if lane_application.submitted_at is not None else None
        ),
        decided_at=(_normalize_utc(lane_application.decided_at) if lane_application.decided_at is not None else None),
        decision_reason_code=lane_application.decision_reason_code,
        decision_summary=lane_application.decision_summary,
        created_at=_normalize_utc(lane_application.created_at),
        updated_at=_normalize_utc(lane_application.updated_at),
    )


def _serialize_partner_application_attachment_response(
    attachment,
) -> PartnerApplicationAttachmentResponse:
    return PartnerApplicationAttachmentResponse(
        id=attachment.id,
        partner_account_id=attachment.partner_account_id,
        partner_application_draft_id=attachment.partner_application_draft_id,
        lane_application_id=attachment.lane_application_id,
        review_request_id=attachment.review_request_id,
        attachment_type=attachment.attachment_type,
        storage_key=attachment.storage_key,
        file_name=attachment.file_name,
        attachment_metadata=dict(attachment.attachment_metadata or {}),
        uploaded_by_admin_user_id=attachment.uploaded_by_admin_user_id,
        created_at=_normalize_utc(attachment.created_at),
    )


def _map_application_review_request_status(value: str) -> str:
    if value == "responded":
        return "submitted"
    if value == "resolved":
        return "resolved"
    return "open"


def _serialize_partner_application_review_request_detail(
    review_request,
    *,
    thread_events: list[PartnerWorkspaceThreadEventResponse] | None = None,
) -> PartnerApplicationReviewRequestDetailResponse:
    return PartnerApplicationReviewRequestDetailResponse(
        id=review_request.id,
        partner_account_id=review_request.partner_account_id,
        partner_application_draft_id=review_request.partner_application_draft_id,
        lane_application_id=review_request.lane_application_id,
        request_kind=review_request.request_kind,
        message=review_request.message,
        required_fields=list(review_request.required_fields or []),
        required_attachments=list(review_request.required_attachments or []),
        status=_map_application_review_request_status(review_request.status),
        requested_by_admin_user_id=review_request.requested_by_admin_user_id,
        resolved_by_admin_user_id=review_request.resolved_by_admin_user_id,
        requested_at=_normalize_utc(review_request.requested_at),
        response_due_at=(
            _normalize_utc(review_request.response_due_at) if review_request.response_due_at is not None else None
        ),
        responded_at=(_normalize_utc(review_request.responded_at) if review_request.responded_at is not None else None),
        resolved_at=(_normalize_utc(review_request.resolved_at) if review_request.resolved_at is not None else None),
        thread_events=list(thread_events or []),
    )


def _serialize_partner_application_applicant_summary(
    applicant: AdminUserModel | None,
) -> PartnerApplicationApplicantSummaryResponse | None:
    if applicant is None:
        return None
    return PartnerApplicationApplicantSummaryResponse(
        id=applicant.id,
        login=applicant.login,
        email=applicant.email,
        is_email_verified=applicant.is_email_verified,
    )


def _get_workspace_program_readiness_status(
    programs: PartnerWorkspaceProgramsResponse | None,
    key: str,
    *,
    default: str,
) -> str:
    if programs is None:
        return default
    item = next((entry for entry in programs.readiness_items if entry.key == key), None)
    return item.status if item is not None else default


def _derive_partner_governance_state(
    *,
    workspace_status: str,
    programs: PartnerWorkspaceProgramsResponse | None,
) -> str:
    if workspace_status == "suspended":
        return "frozen"
    if workspace_status == "restricted":
        return "limited"
    if programs is None:
        return "clear"

    lane_memberships = programs.lane_memberships or []
    blocking_codes = {code for lane in lane_memberships for code in list(lane.blocking_reason_codes or [])}
    warning_codes = {code for lane in lane_memberships for code in list(lane.warning_reason_codes or [])}

    if {
        "governance_action_blocking",
        "risk_review_blocking",
        "settlement_shadow_blocked",
        "attribution_shadow_blocked",
    } & blocking_codes:
        return "warning"
    if warning_codes:
        return "watch"
    return "clear"


def _derive_partner_release_ring(
    *,
    workspace_status: str,
    primary_lane_key: str | None,
    permission_keys: frozenset[str] | list[str],
) -> str:
    permissions = frozenset(permission_keys)
    activeish_statuses = {"approved_probation", "active", "restricted", "suspended"}
    if workspace_status not in activeish_statuses:
        return "R0"
    if primary_lane_key == "reseller_api" and "codes_read" in permissions:
        return "R4"
    if "integrations_read" in permissions:
        return "R3"
    if "earnings_read" in permissions:
        return "R2"
    return "R1"


def _build_partner_session_pending_tasks(
    *,
    review_requests: list[PartnerWorkspaceReviewRequestResponse],
    finance_readiness: str,
    compliance_readiness: str,
    technical_readiness: str,
) -> list[PartnerSessionBootstrapPendingTaskResponse]:
    tasks = [
        PartnerSessionBootstrapPendingTaskResponse(
            id=f"review-request:{item.id}",
            task_key=f"review_request.{item.kind}",
            tone="warning",
            route_slug="application",
            source_kind="review_request",
            source_id=item.id,
            notes=[f"status:{item.status}"],
        )
        for item in review_requests
        if item.status == "open"
    ]

    if finance_readiness == "blocked":
        tasks.append(
            PartnerSessionBootstrapPendingTaskResponse(
                id="readiness:finance:blocked",
                task_key="readiness.finance.blocked",
                tone="critical",
                route_slug="finance",
                source_kind="readiness",
                source_id="finance",
                notes=[],
            )
        )
    elif finance_readiness in {"not_started", "in_progress"}:
        tasks.append(
            PartnerSessionBootstrapPendingTaskResponse(
                id=f"readiness:finance:{finance_readiness}",
                task_key=f"readiness.finance.{finance_readiness}",
                tone="warning",
                route_slug="finance",
                source_kind="readiness",
                source_id="finance",
                notes=[],
            )
        )

    if compliance_readiness == "evidence_requested":
        tasks.append(
            PartnerSessionBootstrapPendingTaskResponse(
                id="readiness:compliance:evidence_requested",
                task_key="readiness.compliance.evidence_requested",
                tone="warning",
                route_slug="compliance",
                source_kind="readiness",
                source_id="compliance",
                notes=[],
            )
        )
    elif compliance_readiness == "blocked":
        tasks.append(
            PartnerSessionBootstrapPendingTaskResponse(
                id="readiness:compliance:blocked",
                task_key="readiness.compliance.blocked",
                tone="critical",
                route_slug="compliance",
                source_kind="readiness",
                source_id="compliance",
                notes=[],
            )
        )

    if technical_readiness in {"in_progress", "blocked"}:
        tasks.append(
            PartnerSessionBootstrapPendingTaskResponse(
                id=f"readiness:technical:{technical_readiness}",
                task_key=f"readiness.technical.{technical_readiness}",
                tone="critical" if technical_readiness == "blocked" else "warning",
                route_slug="integrations",
                source_kind="readiness",
                source_id="technical",
                notes=[],
            )
        )

    return tasks


def _build_partner_session_blocked_reasons(
    *,
    workspace_status: str,
    programs: PartnerWorkspaceProgramsResponse | None,
    finance_readiness: str,
    compliance_readiness: str,
    technical_readiness: str,
    governance_state: str,
) -> list[PartnerSessionBootstrapBlockedReasonResponse]:
    blocked_reasons: list[PartnerSessionBootstrapBlockedReasonResponse] = []

    if workspace_status in {"restricted", "suspended", "rejected", "terminated"}:
        blocked_reasons.append(
            PartnerSessionBootstrapBlockedReasonResponse(
                code=f"workspace_status:{workspace_status}",
                severity="critical" if workspace_status in {"suspended", "rejected", "terminated"} else "warning",
                route_slug="dashboard",
                notes=[
                    (
                        "Workspace remains visible for remediation, but operational expansion is constrained "
                        "until the workspace lifecycle state changes."
                    )
                ],
            )
        )

    if finance_readiness == "blocked":
        blocked_reasons.append(
            PartnerSessionBootstrapBlockedReasonResponse(
                code="finance_blocked",
                severity="critical",
                route_slug="finance",
                notes=[
                    "Payout-bearing actions remain blocked until finance readiness is restored.",
                    "Cases and finance surfaces stay visible so the workspace can finish remediation.",
                ],
            )
        )
    if compliance_readiness in {"evidence_requested", "blocked"}:
        blocked_reasons.append(
            PartnerSessionBootstrapBlockedReasonResponse(
                code=f"compliance_{compliance_readiness}",
                severity="critical" if compliance_readiness == "blocked" else "warning",
                route_slug="compliance",
                notes=[
                    (
                        "Additional declarations or evidence are still required before compliance-driven "
                        "actions can expand."
                    )
                    if compliance_readiness == "evidence_requested"
                    else (
                        "Compliance posture is currently blocked, so declarations and governed launch actions "
                        "stay limited."
                    )
                ],
            )
        )
    if technical_readiness == "blocked":
        blocked_reasons.append(
            PartnerSessionBootstrapBlockedReasonResponse(
                code="technical_blocked",
                severity="critical",
                route_slug="integrations",
                notes=[
                    "Technical launch tooling remains limited until integration readiness is restored.",
                ],
            )
        )
    if governance_state in {"warning", "limited", "frozen"}:
        blocked_reasons.append(
            PartnerSessionBootstrapBlockedReasonResponse(
                code=f"governance_state:{governance_state}",
                severity="critical" if governance_state == "frozen" else "warning",
                route_slug="compliance",
                notes=[
                    (
                        "Governance monitoring is active. Keep declarations and evidence current while the "
                        "workspace remains under observation."
                    )
                    if governance_state == "warning"
                    else ("Governance posture is limiting launch-sensitive actions while remediation continues.")
                    if governance_state == "limited"
                    else (
                        "Governance posture is frozen. Remediation and support cases remain visible, but "
                        "launch-sensitive actions are blocked."
                    )
                ],
            )
        )

    if programs is not None:
        for lane in programs.lane_memberships:
            for code in lane.blocking_reason_codes:
                blocked_reasons.append(
                    PartnerSessionBootstrapBlockedReasonResponse(
                        code=code,
                        severity="warning",
                        route_slug="programs",
                        notes=list(lane.restriction_notes or []),
                    )
                )

    seen: set[tuple[str, str | None]] = set()
    unique_reasons: list[PartnerSessionBootstrapBlockedReasonResponse] = []
    for item in blocked_reasons:
        key = (item.code, item.route_slug)
        if key in seen:
            continue
        seen.add(key)
        unique_reasons.append(item)
    return unique_reasons


def _serialize_partner_statement(model) -> PartnerStatementResponse:
    return PartnerStatementResponse(
        id=model.id,
        partner_account_id=model.partner_account_id,
        settlement_period_id=model.settlement_period_id,
        statement_key=model.statement_key,
        statement_version=model.statement_version,
        statement_status=model.statement_status,
        reopened_from_statement_id=model.reopened_from_statement_id,
        superseded_by_statement_id=model.superseded_by_statement_id,
        currency_code=model.currency_code,
        accrual_amount=float(model.accrual_amount or Decimal("0")),
        on_hold_amount=float(model.on_hold_amount or Decimal("0")),
        reserve_amount=float(model.reserve_amount or Decimal("0")),
        adjustment_net_amount=float(model.adjustment_net_amount or Decimal("0")),
        available_amount=float(model.available_amount or Decimal("0")),
        source_event_count=model.source_event_count,
        held_event_count=model.held_event_count,
        active_reserve_count=model.active_reserve_count,
        adjustment_count=model.adjustment_count,
        statement_snapshot=dict(model.statement_snapshot or {}),
        closed_at=model.closed_at,
        closed_by_admin_user_id=model.closed_by_admin_user_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_partner_workspace_payout_account(model) -> PartnerWorkspacePayoutAccountResponse:
    return PartnerWorkspacePayoutAccountResponse(
        id=model.id,
        settlement_profile_id=model.settlement_profile_id,
        payout_rail=model.payout_rail,
        display_label=model.display_label,
        masked_destination=model.masked_destination,
        destination_metadata=dict(model.destination_metadata or {}),
        verification_status=model.verification_status,
        approval_status=model.approval_status,
        account_status=model.account_status,
        is_default=bool(model.is_default),
        verified_at=model.verified_at,
        approved_at=model.approved_at,
        suspended_at=model.suspended_at,
        suspension_reason_code=model.suspension_reason_code,
        archived_at=model.archived_at,
        archive_reason_code=model.archive_reason_code,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_partner_workspace_payout_eligibility(
    result,
) -> PartnerWorkspacePayoutAccountEligibilityResponse:
    return PartnerWorkspacePayoutAccountEligibilityResponse(
        partner_payout_account_id=result.partner_payout_account_id,
        partner_account_id=result.partner_account_id,
        eligible=result.eligible,
        reason_codes=list(result.reason_codes or []),
        blocking_risk_review_ids=list(result.blocking_risk_review_ids or []),
        active_reserve_ids=list(result.active_reserve_ids or []),
        checked_at=result.checked_at,
    )


def _build_partner_workspace_payout_account_notes(account) -> list[str]:
    notes = [account.masked_destination]

    if account.verification_status != PartnerPayoutAccountVerificationStatus.VERIFIED.value:
        notes.append("Verification is still pending finance review.")
    if account.approval_status != PartnerPayoutAccountApprovalStatus.APPROVED.value:
        notes.append("Approval is still pending finance sign-off.")
    if account.account_status == PartnerPayoutAccountStatus.SUSPENDED.value:
        notes.append(
            f"Suspended{f' ({account.suspension_reason_code})' if account.suspension_reason_code else ''}.",
        )
    if account.account_status == PartnerPayoutAccountStatus.ARCHIVED.value:
        notes.append(
            f"Archived{f' ({account.archive_reason_code})' if account.archive_reason_code else ''}.",
        )
    if account.is_default:
        notes.append("This payout account is currently selected as default.")

    return notes


def _derive_partner_workspace_payout_lifecycle_status(*, instruction, execution) -> str:
    if execution is not None:
        if execution.execution_status in {
            PayoutExecutionStatus.SUCCEEDED.value,
            PayoutExecutionStatus.RECONCILED.value,
        }:
            return "paid"
        if execution.execution_status == PayoutExecutionStatus.FAILED.value:
            return "failed"
        if execution.execution_status in {
            PayoutExecutionStatus.REQUESTED.value,
            PayoutExecutionStatus.SUBMITTED.value,
        }:
            return "in_flight"

    if instruction.instruction_status == PayoutInstructionStatus.REJECTED.value:
        return "blocked"
    if instruction.instruction_status == PayoutInstructionStatus.APPROVED.value:
        return "queued"
    if instruction.instruction_status == PayoutInstructionStatus.COMPLETED.value:
        return "paid"
    return "pending_review"


def _build_partner_workspace_payout_history(
    *,
    instructions: list,
    executions: list,
    statements: list,
    payout_accounts: list,
) -> list[PartnerWorkspacePayoutHistoryResponse]:
    statement_by_id = {item.id: item for item in statements}
    payout_account_by_id = {item.id: item for item in payout_accounts}
    executions_by_instruction_id: dict[UUID, list] = {}
    for execution in executions:
        executions_by_instruction_id.setdefault(execution.payout_instruction_id, []).append(execution)

    history: list[PartnerWorkspacePayoutHistoryResponse] = []
    for instruction in instructions:
        statement = statement_by_id.get(instruction.partner_statement_id)
        payout_account = payout_account_by_id.get(instruction.partner_payout_account_id)
        linked_executions = sorted(
            executions_by_instruction_id.get(instruction.id, []),
            key=lambda item: item.created_at,
            reverse=True,
        )

        if linked_executions:
            for execution in linked_executions:
                notes = _build_partner_workspace_payout_account_notes(payout_account) if payout_account else []
                if execution.execution_status == PayoutExecutionStatus.FAILED.value and execution.failure_reason_code:
                    notes.append(f"Execution failed: {execution.failure_reason_code}.")
                elif execution.execution_status == PayoutExecutionStatus.SUBMITTED.value:
                    notes.append("Execution has been submitted to the payout rail.")
                elif execution.execution_status in {
                    PayoutExecutionStatus.SUCCEEDED.value,
                    PayoutExecutionStatus.RECONCILED.value,
                }:
                    notes.append("Execution completed successfully.")

                history.append(
                    PartnerWorkspacePayoutHistoryResponse(
                        id=f"execution:{execution.id}",
                        instruction_id=instruction.id,
                        execution_id=execution.id,
                        partner_statement_id=instruction.partner_statement_id,
                        partner_payout_account_id=instruction.partner_payout_account_id,
                        statement_key=statement.statement_key if statement else instruction.instruction_key,
                        payout_account_label=payout_account.display_label if payout_account else None,
                        amount=float(instruction.payout_amount),
                        currency_code=instruction.currency_code,
                        lifecycle_status=_derive_partner_workspace_payout_lifecycle_status(
                            instruction=instruction,
                            execution=execution,
                        ),
                        instruction_status=instruction.instruction_status,
                        execution_status=execution.execution_status,
                        execution_mode=execution.execution_mode,
                        external_reference=execution.external_reference,
                        created_at=execution.created_at,
                        updated_at=execution.updated_at,
                        notes=notes,
                    )
                )
            continue

        notes = _build_partner_workspace_payout_account_notes(payout_account) if payout_account else []
        if instruction.instruction_status == PayoutInstructionStatus.PENDING_APPROVAL.value:
            notes.append("Instruction is waiting for finance maker-checker approval.")
        elif instruction.instruction_status == PayoutInstructionStatus.APPROVED.value:
            notes.append("Instruction is approved and waiting for execution.")
        elif (
            instruction.instruction_status == PayoutInstructionStatus.REJECTED.value
            and instruction.rejection_reason_code
        ):
            notes.append(f"Instruction was rejected: {instruction.rejection_reason_code}.")
        elif instruction.instruction_status == PayoutInstructionStatus.COMPLETED.value:
            notes.append("Instruction was completed without an exposed execution row.")

        history.append(
            PartnerWorkspacePayoutHistoryResponse(
                id=f"instruction:{instruction.id}",
                instruction_id=instruction.id,
                execution_id=None,
                partner_statement_id=instruction.partner_statement_id,
                partner_payout_account_id=instruction.partner_payout_account_id,
                statement_key=statement.statement_key if statement else instruction.instruction_key,
                payout_account_label=payout_account.display_label if payout_account else None,
                amount=float(instruction.payout_amount),
                currency_code=instruction.currency_code,
                lifecycle_status=_derive_partner_workspace_payout_lifecycle_status(
                    instruction=instruction,
                    execution=None,
                ),
                instruction_status=instruction.instruction_status,
                execution_status=None,
                execution_mode=None,
                external_reference=None,
                created_at=instruction.created_at,
                updated_at=instruction.updated_at,
                notes=notes,
            )
        )

    history.sort(key=lambda item: (item.updated_at, item.created_at), reverse=True)
    return history


def _mask_customer_label(user_id: UUID) -> str:
    value = str(user_id).replace("-", "")
    return f"CUST-{value[-6:].upper()}"


def _format_order_label(order_id: UUID) -> str:
    return f"ORDER-{str(order_id).replace('-', '')[:8].upper()}"


def _format_money(amount: float | Decimal, currency_code: str) -> str:
    numeric = float(amount or 0)
    currency = (currency_code or "USD").upper()
    return f"{numeric:.2f} {currency}"


def _derive_customer_scope(*, owner_type: str, owner_source: str | None) -> str:
    if owner_type == "reseller":
        return "workspace_scoped"
    if owner_source == "storefront_default":
        return "storefront_scoped"
    return "masked"


def _derive_conversion_kind(
    *,
    has_open_dispute: bool,
    has_closed_dispute: bool,
    has_succeeded_refund: bool,
    renewal_order: RenewalOrderModel | None,
) -> str:
    if has_open_dispute or has_closed_dispute:
        return "chargeback"
    if has_succeeded_refund:
        return "refund"
    if renewal_order is not None:
        return "repeat_paid"
    return "first_paid"


def _derive_conversion_status(
    *,
    has_open_dispute: bool,
    has_closed_dispute: bool,
    has_succeeded_refund: bool,
    commissionability_status: str | None,
) -> str:
    if has_succeeded_refund or has_closed_dispute:
        return "reversed"
    if commissionability_status == "ineligible":
        return "rejected"
    if has_open_dispute or commissionability_status in {None, "pending"}:
        return "on_hold"
    return "commissionable"


def _serialize_workspace_conversion_record(item: dict) -> PartnerWorkspaceConversionRecordResponse:
    order: OrderModel = item["order"]
    attribution_result: OrderAttributionResultModel = item["attribution_result"]
    evaluation: CommissionabilityEvaluationModel | None = item["evaluation"]
    renewal_order: RenewalOrderModel | None = item["renewal_order"]
    partner_code: PartnerCodeModel | None = item["partner_code"]
    disputes: list[PaymentDisputeModel] = item["disputes"]
    refunds: list[RefundModel] = item["refunds"]
    report_row: dict = item.get("report_row") or {}

    has_open_dispute = any(dispute.outcome_class == "open" for dispute in disputes)
    has_closed_dispute = any(dispute.outcome_class in {"lost", "reversed"} for dispute in disputes)
    has_succeeded_refund = any(refund.refund_status == "succeeded" for refund in refunds)
    commissionability_status = evaluation.commissionability_status if evaluation is not None else None
    owner_source = attribution_result.owner_source
    owner_type = attribution_result.owner_type

    reason_codes = []
    if has_open_dispute:
        reason_codes.append("Open payment dispute keeps the conversion on hold for reporting and payout review.")
    elif has_closed_dispute:
        reason_codes.append("Chargeback or dispute reversal is recorded against this conversion.")
    elif has_succeeded_refund:
        reason_codes.append("Succeeded refund reversed the conversion for workspace reporting.")
    elif report_row.get("is_qualifying_first_payment"):
        reason_codes.append("Qualifying first payment under canonical reporting rules.")
    elif report_row.get("is_renewal"):
        reason_codes.append("Renewal lineage keeps this paid conversion under the active workspace owner.")
    else:
        reason_codes.append(f"Owner source: {owner_source or 'unresolved'}")
    if commissionability_status is not None:
        reason_codes.append(f"Commissionability: {commissionability_status}.")
    if evaluation is not None:
        reason_codes.extend(
            [str(reason_code) for reason_code in list(evaluation.reason_codes or []) if reason_code not in reason_codes]
        )
    if disputes:
        reason_codes.append(f"{len(disputes)} dispute record(s)")
    if refunds:
        reason_codes.append(f"{len(refunds)} refund record(s)")
    if report_row.get("owner_source") and report_row.get("owner_source") != owner_source:
        reason_codes.append(f"Reporting owner source: {report_row['owner_source']}")

    return PartnerWorkspaceConversionRecordResponse(
        id=str(order.id),
        kind=_derive_conversion_kind(
            has_open_dispute=has_open_dispute,
            has_closed_dispute=has_closed_dispute,
            has_succeeded_refund=has_succeeded_refund,
            renewal_order=renewal_order,
        ),
        status=_derive_conversion_status(
            has_open_dispute=has_open_dispute,
            has_closed_dispute=has_closed_dispute,
            has_succeeded_refund=has_succeeded_refund,
            commissionability_status=commissionability_status,
        ),
        order_label=_format_order_label(order.id),
        customer_label=_mask_customer_label(order.user_id),
        code_label=partner_code.code if partner_code is not None else owner_source or "direct",
        geo="masked",
        amount=_format_money(order.commission_base_amount or order.displayed_price, order.currency_code),
        customer_scope=_derive_customer_scope(owner_type=owner_type, owner_source=owner_source),
        updated_at=order.updated_at,
        notes=reason_codes,
    )


def _get_workspace_partner_reporting_row(
    *,
    report_pack: dict,
    partner_account_id: UUID,
) -> dict:
    workspace_id = str(partner_account_id)
    for item in report_pack.get("partner_reporting_mart", []):
        if item.get("partner_account_id") == workspace_id:
            return item
    return {}


def _get_reporting_health_summary(report_pack: dict) -> tuple[dict[str, dict], str | None]:
    consumer_views = report_pack.get("reporting_health_views", {}).get("consumer_health_views", [])
    consumer_health = {
        str(item.get("consumer_key")): dict(item) for item in consumer_views if item.get("consumer_key") is not None
    }
    failed = sum(int(item.get("failed_count", 0) or 0) for item in consumer_health.values())
    backlog = sum(int(item.get("backlog_count", 0) or 0) for item in consumer_health.values())
    if failed > 0:
        return consumer_health, f"Reporting publication failures detected: {failed}."
    if backlog > 0:
        return consumer_health, f"Reporting publication backlog detected: {backlog}."
    if consumer_health:
        return consumer_health, "Reporting publication consumers are green."
    return consumer_health, None


def _build_workspace_analytics_metrics(
    *,
    partner_account_id: UUID,
    report_pack: dict,
) -> list[PartnerWorkspaceAnalyticsMetricResponse]:
    workspace_id = str(partner_account_id)
    partner_row = _get_workspace_partner_reporting_row(
        report_pack=report_pack,
        partner_account_id=partner_account_id,
    )
    workspace_orders = [
        item for item in report_pack.get("order_reporting_mart", []) if item.get("partner_account_id") == workspace_id
    ]
    first_paid = sum(
        1
        for item in workspace_orders
        if item.get("is_paid_conversion")
        and not item.get("is_renewal")
        and not item.get("has_open_dispute")
        and not item.get("has_chargeback")
        and not item.get("has_refund")
    )
    repeat_paid = sum(
        1
        for item in workspace_orders
        if item.get("is_paid_conversion")
        and item.get("is_renewal")
        and not item.get("has_open_dispute")
        and not item.get("has_chargeback")
        and not item.get("has_refund")
    )
    qualifying_first = sum(1 for item in workspace_orders if item.get("is_qualifying_first_payment"))
    refund_rate = float(partner_row.get("refund_rate", 0) or 0)
    chargeback_rate = float(partner_row.get("chargeback_rate", 0) or 0)
    available_earnings = float(partner_row.get("available_earnings_amount", 0) or 0)
    statement_liability_amount = float(partner_row.get("statement_liability_amount", 0) or 0)
    if available_earnings <= 0 and statement_liability_amount > 0:
        available_earnings = statement_liability_amount
    currency_codes = list(partner_row.get("currency_codes") or [])
    currency_code = str(currency_codes[0]) if currency_codes else "USD"
    _consumer_health, reporting_health_note = _get_reporting_health_summary(report_pack)

    return [
        PartnerWorkspaceAnalyticsMetricResponse(
            id="first_paid",
            key="first_paid",
            value=str(first_paid),
            trend="steady",
            notes=[
                "Canonical paid first-order count from workspace-scoped reporting mart rows.",
                f"Qualifying first payment count: {qualifying_first}.",
                *([reporting_health_note] if reporting_health_note else []),
            ],
        ),
        PartnerWorkspaceAnalyticsMetricResponse(
            id="repeat_paid",
            key="repeat_paid",
            value=str(repeat_paid),
            trend="steady",
            notes=[
                "Canonical renewal paid count for orders that retain workspace ownership lineage.",
                (
                    "Total paid conversions visible to the workspace: "
                    f"{int(partner_row.get('paid_conversion_count', 0) or 0)}."
                ),
                *([reporting_health_note] if reporting_health_note else []),
            ],
        ),
        PartnerWorkspaceAnalyticsMetricResponse(
            id="refund_rate",
            key="refund_rate",
            value=f"{refund_rate:.2f}%",
            trend="steady",
            notes=[
                "Computed from canonical refund rows over paid workspace conversions.",
                f"Refund count in mart scope: {int(partner_row.get('refund_count', 0) or 0)}.",
                *([reporting_health_note] if reporting_health_note else []),
            ],
        ),
        PartnerWorkspaceAnalyticsMetricResponse(
            id="chargeback_rate",
            key="chargeback_rate",
            value=f"{chargeback_rate:.2f}%",
            trend="steady",
            notes=[
                "Computed from canonical dispute rows over paid workspace conversions.",
                f"Chargeback count in mart scope: {int(partner_row.get('chargeback_count', 0) or 0)}.",
                *([reporting_health_note] if reporting_health_note else []),
            ],
        ),
        PartnerWorkspaceAnalyticsMetricResponse(
            id="earnings_available",
            key="earnings_available",
            value=_format_money(available_earnings, currency_code),
            trend="steady",
            notes=[
                "Summed from canonical earning events and current workspace statement liability views.",
                f"Statement liability in mart scope: {_format_money(statement_liability_amount, currency_code)}.",
                *([reporting_health_note] if reporting_health_note else []),
            ],
        ),
    ]


def _build_workspace_reporting_summary(
    *,
    partner_account_id: UUID,
    report_pack: dict,
) -> PartnerWorkspaceReportingSummaryResponse:
    workspace_id = str(partner_account_id)
    metadata = dict(report_pack.get("metadata") or {})
    reconciliation = dict(report_pack.get("reconciliation") or {})
    partner_row = _get_workspace_partner_reporting_row(
        report_pack=report_pack,
        partner_account_id=partner_account_id,
    )
    workspace_orders = [
        item for item in report_pack.get("order_reporting_mart", []) if item.get("partner_account_id") == workspace_id
    ]
    paid_rows = [
        item
        for item in workspace_orders
        if item.get("is_paid_conversion")
        and not item.get("has_refund")
        and not item.get("has_open_dispute")
        and not item.get("has_chargeback")
    ]
    paid_user_ids = {str(item.get("user_id")) for item in paid_rows if item.get("user_id")}
    all_user_ids = {str(item.get("user_id")) for item in workspace_orders if item.get("user_id")}
    currency_codes = list(partner_row.get("currency_codes") or [])
    currency_code = str(currency_codes[0]) if currency_codes else "USD"
    mismatch_counts = {str(key): int(value) for key, value in dict(reconciliation.get("mismatch_counts") or {}).items()}
    blocking_mismatches = list(reconciliation.get("blocking_mismatches") or [])

    metrics = [
        PartnerWorkspaceReportingSummaryMetricResponse(
            key="active_users",
            value=str(len(paid_user_ids)),
            source_of_truth="order_reporting_mart",
            notes=[
                "Workspace-scoped unique paid users after refund and chargeback exclusions.",
                "This is a paid-user activity proxy until subscription-state mart is approved.",
            ],
        ),
        PartnerWorkspaceReportingSummaryMetricResponse(
            key="trial_users",
            value="not_available",
            source_of_truth="not_available_in_s3_stage_10",
            notes=[
                "Partner trial attribution is not present in the current backend reporting mart.",
                "Do not expose trial-user totals as a source-of-truth metric yet.",
            ],
        ),
        PartnerWorkspaceReportingSummaryMetricResponse(
            key="paid_users",
            value=str(len(paid_user_ids)),
            source_of_truth="order_reporting_mart",
            notes=["Unique customer labels are counted without exposing raw customer PII."],
        ),
        PartnerWorkspaceReportingSummaryMetricResponse(
            key="paid_conversions",
            value=str(int(partner_row.get("paid_conversion_count", 0) or 0)),
            source_of_truth="partner_reporting_mart",
            notes=["Canonical paid conversion count for this partner workspace."],
        ),
        PartnerWorkspaceReportingSummaryMetricResponse(
            key="refunds",
            value=str(int(partner_row.get("refund_count", 0) or 0)),
            source_of_truth="partner_reporting_mart",
            notes=["Refund impact from canonical refund rows joined to workspace orders."],
        ),
        PartnerWorkspaceReportingSummaryMetricResponse(
            key="chargebacks",
            value=str(int(partner_row.get("chargeback_count", 0) or 0)),
            source_of_truth="partner_reporting_mart",
            notes=["Chargeback impact from payment dispute rows joined to workspace orders."],
        ),
        PartnerWorkspaceReportingSummaryMetricResponse(
            key="available_earnings",
            value=_format_money(
                float(partner_row.get("available_earnings_amount", 0) or 0),
                currency_code,
            ),
            source_of_truth="earning_events",
            notes=["Source-of-truth amount remains settlement/earning events, not dashboard math."],
        ),
        PartnerWorkspaceReportingSummaryMetricResponse(
            key="visible_customer_count",
            value=str(len(all_user_ids)),
            source_of_truth="order_reporting_mart",
            notes=["Count only; exports must keep customer identity redacted."],
        ),
    ]

    reconciliation_notes = [
        "Green means no reporting mart mismatch was detected for this workspace snapshot.",
        "Yellow requires operator review before treating reports as final.",
        "Red blocks partner pilot expansion until the listed mismatches are resolved.",
    ]
    return PartnerWorkspaceReportingSummaryResponse(
        workspace_id=partner_account_id,
        generated_at=datetime.now(UTC),
        report_version=str(metadata.get("report_version") or "phase7-reporting-marts-v1"),
        metrics=metrics,
        reconciliation=PartnerWorkspaceReportingReconciliationResponse(
            status=str(reconciliation.get("status") or "green"),
            mismatch_counts=mismatch_counts,
            blocking_mismatch_count=len(blocking_mismatches),
            notes=reconciliation_notes,
        ),
        export_redaction=PartnerWorkspaceReportExportRedactionResponse(
            policy="redacted_partner_export",
            pii_fields_excluded=[
                "email",
                "telegram_id",
                "phone",
                "raw_user_id",
                "ip_address",
                "payment_provider_payload",
                "provider_customer_id",
                "vpn_subscription_url",
            ],
            masked_fields=[
                "customer_label",
                "geo",
                "source",
            ],
            notes=[
                "Partner exports must use masked customer labels and aggregated geography only.",
                "Raw payment provider payloads and VPN subscription links are never export fields.",
            ],
        ),
        source_of_truth_notes=[
            "Conversions are sourced from orders, attribution results, renewal lineage, refunds and disputes.",
            "Earnings are sourced from earning events and partner statement snapshots.",
            "Outbox consumer health is used only to qualify report freshness and replay risk.",
            "Trial attribution is intentionally marked not available until a canonical trial mart exists.",
        ],
    )


def _build_workspace_settlement_sandbox_simulation(
    *,
    partner_account_id: UUID,
    report_pack: dict,
    statements: list,
    payout_accounts: list,
    payout_instructions: list,
    payout_executions: list,
) -> PartnerWorkspaceSettlementSandboxSimulationResponse:
    partner_row = _get_workspace_partner_reporting_row(
        report_pack=report_pack,
        partner_account_id=partner_account_id,
    )
    currency_codes = list(partner_row.get("currency_codes") or [])
    if currency_codes:
        currency_code = str(currency_codes[0]).upper()
    elif statements:
        currency_code = str(getattr(statements[0], "currency_code", "USD") or "USD").upper()
    else:
        currency_code = "USD"

    closed_positive_statements = [
        statement
        for statement in statements
        if getattr(statement, "statement_status", None) == PartnerStatementStatus.CLOSED.value
        and getattr(statement, "superseded_by_statement_id", None) is None
        and float(getattr(statement, "available_amount", 0) or 0) > 0
    ]
    eligible_payout_accounts = [
        account
        for account in payout_accounts
        if getattr(account, "account_status", None) == PartnerPayoutAccountStatus.ACTIVE.value
        and getattr(account, "verification_status", None) == PartnerPayoutAccountVerificationStatus.VERIFIED.value
        and getattr(account, "approval_status", None) == PartnerPayoutAccountApprovalStatus.APPROVED.value
    ]
    pending_instructions = [
        instruction
        for instruction in payout_instructions
        if getattr(instruction, "instruction_status", None) == PayoutInstructionStatus.PENDING_APPROVAL.value
    ]
    approved_instructions = [
        instruction
        for instruction in payout_instructions
        if getattr(instruction, "instruction_status", None) == PayoutInstructionStatus.APPROVED.value
    ]
    active_executions = [
        execution
        for execution in payout_executions
        if getattr(execution, "execution_status", None)
        in {
            PayoutExecutionStatus.REQUESTED.value,
            PayoutExecutionStatus.SUBMITTED.value,
        }
    ]
    dry_run_executions = [
        execution
        for execution in payout_executions
        if getattr(execution, "execution_mode", None) == PayoutExecutionMode.DRY_RUN.value
    ]
    live_executions = [
        execution
        for execution in payout_executions
        if getattr(execution, "execution_mode", None) == PayoutExecutionMode.LIVE.value
    ]

    blocked_reasons = ["stage_blocks_live_payout"]
    if not closed_positive_statements:
        blocked_reasons.append("no_closed_positive_statement")
    if not eligible_payout_accounts:
        blocked_reasons.append("payout_account_not_approved")
    if pending_instructions:
        blocked_reasons.append("payout_instruction_awaiting_maker_checker")
    if not approved_instructions:
        blocked_reasons.append("no_approved_instruction_for_dry_run")
    if active_executions:
        blocked_reasons.append("active_payout_execution_exists")

    payout_instruction_allowed = bool(closed_positive_statements and eligible_payout_accounts and not active_executions)
    dry_run_execution_allowed = bool(approved_instructions and not active_executions)
    available_statement_amount = sum(
        float(getattr(item, "available_amount", 0) or 0) for item in closed_positive_statements
    )
    on_hold_amount = sum(float(getattr(item, "on_hold_amount", 0) or 0) for item in statements)
    reserve_amount = sum(float(getattr(item, "reserve_amount", 0) or 0) for item in statements)
    adjustment_net_amount = sum(float(getattr(item, "adjustment_net_amount", 0) or 0) for item in statements)

    metrics = [
        PartnerWorkspaceSettlementSandboxMetricResponse(
            key="available_statement_amount",
            value=_format_money(available_statement_amount, currency_code),
            source_of_truth="partner_statements.available_amount",
            notes=["Only latest closed positive statements are counted as payout candidates."],
        ),
        PartnerWorkspaceSettlementSandboxMetricResponse(
            key="on_hold_amount",
            value=_format_money(on_hold_amount, currency_code),
            source_of_truth="partner_statements.on_hold_amount",
            notes=["Held earnings remain excluded from payout readiness."],
        ),
        PartnerWorkspaceSettlementSandboxMetricResponse(
            key="reserve_amount",
            value=_format_money(reserve_amount, currency_code),
            source_of_truth="partner_statements.reserve_amount",
            notes=["Reserve impact is visible before any payout action is allowed."],
        ),
        PartnerWorkspaceSettlementSandboxMetricResponse(
            key="adjustment_net_amount",
            value=_format_money(adjustment_net_amount, currency_code),
            source_of_truth="partner_statements.adjustment_net_amount",
            notes=["Refund and chargeback adjustments must remain explainable from statement data."],
        ),
        PartnerWorkspaceSettlementSandboxMetricResponse(
            key="paid_conversion_count",
            value=str(int(partner_row.get("paid_conversion_count", 0) or 0)),
            source_of_truth="partner_reporting_mart",
            notes=["Used for finance review only; payouts are sourced from statements."],
        ),
        PartnerWorkspaceSettlementSandboxMetricResponse(
            key="refund_count",
            value=str(int(partner_row.get("refund_count", 0) or 0)),
            source_of_truth="partner_reporting_mart",
            notes=["Refund impact must be reviewed before statement approval."],
        ),
        PartnerWorkspaceSettlementSandboxMetricResponse(
            key="chargeback_count",
            value=str(int(partner_row.get("chargeback_count", 0) or 0)),
            source_of_truth="partner_reporting_mart",
            notes=["Chargeback impact blocks careless payout expansion."],
        ),
        PartnerWorkspaceSettlementSandboxMetricResponse(
            key="payout_export_status",
            value="disabled_by_default",
            source_of_truth="S3-STAGE-11 policy",
            notes=["No partner self-serve payout export is enabled in this stage."],
        ),
    ]

    return PartnerWorkspaceSettlementSandboxSimulationResponse(
        workspace_id=partner_account_id,
        generated_at=datetime.now(UTC),
        currency_code=currency_code,
        metrics=metrics,
        eligibility=PartnerWorkspaceSettlementSandboxEligibilityResponse(
            settlement_simulation_reproducible=bool(partner_row or statements),
            payout_instruction_allowed=payout_instruction_allowed,
            dry_run_execution_allowed=dry_run_execution_allowed,
            live_payout_allowed=False,
            manual_approval_required=True,
            maker_checker_required=True,
            blocked_reasons=blocked_reasons,
            eligible_statement_count=len(closed_positive_statements),
            eligible_payout_account_count=len(eligible_payout_accounts),
            pending_instruction_count=len(pending_instructions),
            approved_instruction_count=len(approved_instructions),
            dry_run_execution_count=len(dry_run_executions),
            live_execution_count=len(live_executions),
        ),
        policy=PartnerWorkspaceSettlementSandboxPolicyResponse(
            required_next_stages=[
                "S3-STAGE-12",
                "S3-STAGE-14",
                "S3-STAGE-15",
                "S3-STAGE-17",
            ],
            notes=[
                "S3-STAGE-11 is sandbox-only and does not permit live payouts.",
                "Finance approval must use maker-checker; maker and checker cannot be the same admin.",
                "Partner self-serve withdrawal and mass payout remain out of scope.",
            ],
        ),
        calculation_notes=[
            "Payout readiness is derived from closed positive statements, approved payout accounts and payout "
            "workflow state.",
            "Live payout remains blocked regardless of eligibility until later S3 finance, legal, staging and "
            "pilot gates pass.",
            "Refunds, chargebacks, holds and reserves are surfaced for review before any payout expansion.",
        ],
    )


async def _load_workspace_payout_history(
    *,
    access: PartnerWorkspaceAccess,
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0,
) -> list[PartnerWorkspacePayoutHistoryResponse]:
    statements = await ListPartnerStatementsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        settlement_period_id=None,
        statement_status=None,
        limit=500,
        offset=0,
    )
    payout_accounts = await ListPartnerPayoutAccountsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        limit=500,
        offset=0,
    )
    instructions = await ListPayoutInstructionsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        limit=limit,
        offset=offset,
    )
    executions = await ListPayoutExecutionsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        limit=500,
        offset=0,
    )
    return _build_partner_workspace_payout_history(
        instructions=instructions,
        executions=executions,
        statements=statements,
        payout_accounts=payout_accounts,
    )


async def _load_workspace_settlement_sandbox(
    *,
    access: PartnerWorkspaceAccess,
    db: AsyncSession,
) -> PartnerWorkspaceSettlementSandboxSimulationResponse:
    reporting_context = await BuildPartnerWorkspaceReportingUseCase(db).execute(
        partner_account_id=access.workspace.id,
        order_limit=500,
        order_offset=0,
        statement_limit=200,
        statement_offset=0,
        payout_limit=100,
        payout_offset=0,
    )
    payout_instructions = await ListPayoutInstructionsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        limit=200,
        offset=0,
    )
    payout_executions = await ListPayoutExecutionsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        limit=200,
        offset=0,
    )
    return _build_workspace_settlement_sandbox_simulation(
        partner_account_id=access.workspace.id,
        report_pack=reporting_context.report_pack,
        statements=reporting_context.statements,
        payout_accounts=reporting_context.payout_accounts,
        payout_instructions=payout_instructions,
        payout_executions=payout_executions,
    )


def _build_partner_admin_payout_review_queue(
    *,
    workspace_id: UUID,
    cases: list[PartnerWorkspaceCaseResponse],
    payout_history: list[PartnerWorkspacePayoutHistoryResponse],
    settlement_sandbox: PartnerWorkspaceSettlementSandboxSimulationResponse,
) -> list[PartnerAdminPayoutReviewItemResponse]:
    review_items: list[PartnerAdminPayoutReviewItemResponse] = []
    finance_case_kinds = {"finance_onboarding", "payout_dispute", "statement_question"}
    for item in cases:
        if item.kind not in finance_case_kinds or item.status == "resolved":
            continue
        review_items.append(
            PartnerAdminPayoutReviewItemResponse(
                id=f"case:{item.id}",
                kind=item.kind,
                status=item.status,
                source="workspace_case",
                required_role=AdminRole.FINANCE.value,
                updated_at=item.updated_at,
                notes=list(item.notes or []),
            )
        )

    for item in payout_history:
        if item.lifecycle_status not in {"pending_review", "queued", "in_flight", "failed", "blocked"}:
            continue
        review_items.append(
            PartnerAdminPayoutReviewItemResponse(
                id=item.id,
                kind="payout_instruction",
                status=item.lifecycle_status,
                source="payout_workflow",
                required_role=AdminRole.FINANCE.value,
                updated_at=item.updated_at,
                amount=_format_money(item.amount, item.currency_code),
                notes=list(item.notes or []),
            )
        )

    if not settlement_sandbox.eligibility.live_payout_allowed:
        review_items.append(
            PartnerAdminPayoutReviewItemResponse(
                id=f"settlement-sandbox:{workspace_id}",
                kind="settlement_policy",
                status="blocked",
                source="settlement_sandbox",
                required_role=AdminRole.FINANCE.value,
                updated_at=settlement_sandbox.generated_at,
                notes=[
                    "Live payouts are blocked by S3 policy.",
                    *settlement_sandbox.eligibility.blocked_reasons,
                ],
            )
        )

    review_items.sort(key=lambda item: _normalize_utc(item.updated_at), reverse=True)
    return review_items


def _build_partner_admin_ops_actions(
    *,
    workspace: PartnerWorkspaceResponse,
    active_code_count: int,
    payout_review_count: int,
) -> list[PartnerAdminOpsActionResponse]:
    frozen = workspace.status in {"suspended", "rejected", "terminated"}
    return [
        PartnerAdminOpsActionResponse(
            key="freeze_workspace",
            status="blocked" if frozen else "available",
            required_role=AdminRole.ADMIN.value,
            notes=["Use `/admin/partner-workspaces/{workspace_id}/status` with a reason."],
        ),
        PartnerAdminOpsActionResponse(
            key="unfreeze_workspace",
            status="available" if workspace.status in {"restricted", "suspended"} else "blocked",
            required_role=AdminRole.ADMIN.value,
            notes=["Restore only after open support/finance blockers are classified."],
        ),
        PartnerAdminOpsActionResponse(
            key="disable_partner_code",
            status="available" if active_code_count > 0 else "blocked",
            required_role=AdminRole.ADMIN.value,
            notes=["Use the admin code status route; every change writes a workspace workflow event."],
        ),
        PartnerAdminOpsActionResponse(
            key="review_payout_queue",
            status="available" if payout_review_count > 0 else "not_required",
            required_role=AdminRole.FINANCE.value,
            notes=["Read-only queue; live payout remains controlled by the payout gates."],
        ),
        PartnerAdminOpsActionResponse(
            key="manual_grant_revoke",
            status="deferred_to_customer_support_flow",
            required_role=AdminRole.OPERATOR.value,
            notes=[
                "S3 partner ops can reference existing S1/S2 support grants; no partner self-service grant is opened."
            ],
        ),
    ]


async def _load_partner_admin_ops_overview(
    *,
    workspace_id: UUID,
    db: AsyncSession,
) -> PartnerAdminOpsOverviewResponse:
    partner_account_repo = PartnerAccountRepository(db)
    workspace = await partner_account_repo.get_account_by_id(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner workspace not found")

    access = _build_internal_admin_read_workspace_access(workspace)
    workspace_payload = await GetPartnerWorkspaceUseCase(partner_account_repo, PartnerRepository(db)).execute(
        workspace.id
    )
    serialized_workspace = _serialize_workspace_response(workspace_payload)
    review_requests = await _load_workspace_review_requests(access=access, db=db)
    cases = await _load_workspace_cases(access=access, db=db)
    payout_history = await _load_workspace_payout_history(access=access, db=db)
    settlement_sandbox = await _load_workspace_settlement_sandbox(access=access, db=db)
    payout_review_queue = _build_partner_admin_payout_review_queue(
        workspace_id=workspace.id,
        cases=cases,
        payout_history=payout_history,
        settlement_sandbox=settlement_sandbox,
    )
    workflow_events = await ListPartnerWorkspaceWorkflowEventsUseCase(db).execute(
        partner_account_id=workspace.id,
        limit=50,
        offset=0,
    )
    recent_audit_events = [
        _serialize_workspace_thread_event(item)
        for item in sorted(workflow_events, key=lambda event: event.created_at, reverse=True)
    ]

    overview = PartnerAdminOpsOverviewResponse(
        workspace=serialized_workspace,
        generated_at=datetime.now(UTC),
        open_cases=sum(1 for item in cases if item.status != "resolved"),
        waiting_on_ops_cases=sum(1 for item in cases if item.status == "waiting_on_ops"),
        open_review_requests=sum(1 for item in review_requests if item.status == "open"),
        payout_review_items=len(payout_review_queue),
        frozen=workspace.status in {"suspended", "rejected", "terminated"},
        cases=cases,
        review_requests=review_requests,
        payout_review_queue=payout_review_queue,
        recent_audit_events=recent_audit_events,
        available_admin_actions=_build_partner_admin_ops_actions(
            workspace=serialized_workspace,
            active_code_count=serialized_workspace.active_code_count,
            payout_review_count=len(payout_review_queue),
        ),
        escalation_path=[
            "support_triage",
            "finance_review",
            "admin_decision",
            "owner_escalation_if_payout_or_abuse_risk",
        ],
        redaction_notes=[
            "Customer identifiers remain masked in partner workspace records.",
            "Raw payment provider payloads and VPN subscription links are not exposed in this overview.",
            "Use customer support/admin customer operations for customer-specific manual grants.",
        ],
    )
    observe_partner_admin_ops_overview(
        workspace_status=workspace.status,
        open_cases=overview.open_cases,
        waiting_on_ops_cases=overview.waiting_on_ops_cases,
        payout_review_queue=overview.payout_review_queue,
        recent_audit_events=overview.recent_audit_events,
    )
    return overview


def _build_workspace_report_exports(
    *,
    access: PartnerWorkspaceAccess,
    report_pack: dict,
    statements: list,
    payout_accounts: list,
    workflow_events_by_subject: dict[tuple[str, str], list[PartnerWorkspaceThreadEventResponse]] | None = None,
) -> list[PartnerWorkspaceReportExportResponse]:
    earnings_read = PartnerPermission.EARNINGS_READ.value in access.permission_keys
    payouts_read = PartnerPermission.PAYOUTS_READ.value in access.permission_keys
    codes_read = PartnerPermission.CODES_READ.value in access.permission_keys
    can_operate_exports = PartnerPermission.OPERATIONS_WRITE.value in access.permission_keys
    workspace_id = str(access.workspace.id)
    workspace_orders = [
        item for item in report_pack.get("order_reporting_mart", []) if item.get("partner_account_id") == workspace_id
    ]
    consumer_health, reporting_health_note = _get_reporting_health_summary(report_pack)
    analytics_consumer = consumer_health.get("analytics_mart")
    replay_consumer = consumer_health.get("operational_replay")

    def _resolve_reporting_status(
        *,
        allowed: bool,
        has_material: bool,
        replay_sensitive: bool = False,
    ) -> str:
        if not allowed or not has_material:
            return "blocked"
        relevant_consumers = [analytics_consumer]
        if replay_sensitive:
            relevant_consumers.append(replay_consumer)
        if any(item and int(item.get("failed_count", 0) or 0) > 0 for item in relevant_consumers):
            return "blocked"
        if any(item and int(item.get("backlog_count", 0) or 0) > 0 for item in relevant_consumers):
            return "scheduled"
        return "available"

    export_definitions = [
        {
            "id": "code-report",
            "kind": "code_report",
            "status": "available" if codes_read else "blocked",
            "cadence": "on_demand",
            "notes": ["Workspace-scoped code inventory export."],
        },
        {
            "id": "geo-report",
            "kind": "geo_report",
            "status": _resolve_reporting_status(
                allowed=earnings_read,
                has_material=bool(workspace_orders),
            ),
            "cadence": "on_demand",
            "notes": [
                "Masked geo/source visibility over canonical workspace reporting rows.",
                *([reporting_health_note] if reporting_health_note else []),
            ],
        },
        {
            "id": "statement-export",
            "kind": "statement_export",
            "status": _resolve_reporting_status(
                allowed=earnings_read,
                has_material=bool(statements),
            ),
            "cadence": "per_statement_close",
            "notes": [
                "Frozen statement snapshots only, sourced from canonical settlement statements.",
                *([reporting_health_note] if reporting_health_note else []),
            ],
        },
        {
            "id": "payout-status-export",
            "kind": "payout_status_export",
            "status": "available" if payouts_read and payout_accounts else "blocked",
            "cadence": "on_demand",
            "notes": ["Payout-account and settlement-readiness status export."],
        },
        {
            "id": "explainability-report",
            "kind": "explainability_report",
            "status": _resolve_reporting_status(
                allowed=earnings_read,
                has_material=bool(workspace_orders),
                replay_sensitive=True,
            ),
            "cadence": "on_demand",
            "notes": [
                "Commercial ownership, commissionability, refund, dispute, and renewal explainability summary only.",
                *([reporting_health_note] if reporting_health_note else []),
            ],
        },
    ]

    exports: list[PartnerWorkspaceReportExportResponse] = []
    excluded_pii_fields = [
        "email",
        "telegram_id",
        "phone",
        "raw_user_id",
        "ip_address",
        "payment_provider_payload",
        "provider_customer_id",
        "vpn_subscription_url",
    ]
    for item in export_definitions:
        thread_events = _get_subject_thread_events(
            grouped_events=workflow_events_by_subject,
            subject_kind=_WORKSPACE_REPORT_EXPORT_SUBJECT_KIND,
            subject_id=str(item["id"]),
        )
        status = str(item["status"])
        exports.append(
            PartnerWorkspaceReportExportResponse(
                id=str(item["id"]),
                kind=str(item["kind"]),
                status=status,
                cadence=str(item["cadence"]),
                source_of_truth="workspace_scoped_backend_reporting_marts",
                redaction_policy="redacted_partner_export",
                pii_fields_excluded=list(excluded_pii_fields),
                notes=list(item["notes"]),
                available_actions=(["schedule_export"] if can_operate_exports and status != "blocked" else []),
                thread_events=thread_events,
                last_requested_at=(max(event.created_at for event in thread_events) if thread_events else None),
            )
        )
    return exports


def _resolve_workspace_integration_credential_status(
    *,
    workspace_status: str,
    credential_status: str,
    last_rotated_at: datetime | None,
) -> str:
    if workspace_status in {"restricted", "suspended", "rejected", "terminated"}:
        return "blocked"
    if credential_status == "blocked":
        return "blocked"
    if workspace_status in {
        "draft",
        "email_verified",
        "submitted",
        "under_review",
        "waitlisted",
        "approved_probation",
        "needs_info",
    }:
        return "pending_rotation"
    if last_rotated_at is None:
        return "pending_rotation"
    return "ready"


def _serialize_workspace_integration_credential(
    *,
    workspace_status: str,
    model,
) -> PartnerWorkspaceIntegrationCredentialResponse:
    effective_status = _resolve_workspace_integration_credential_status(
        workspace_status=workspace_status,
        credential_status=model.credential_status,
        last_rotated_at=model.last_rotated_at,
    )
    notes = [
        (
            "Workspace-scoped reporting token for canonical marts and export reads."
            if model.credential_kind == PartnerIntegrationCredentialKind.REPORTING_API_TOKEN.value
            else "Scoped postback credential for signed click-tracking and postback delivery."
        ),
        (
            "Credential visibility remains backend-owned and row-level scoped."
            if effective_status == "ready"
            else "Credential exists but still requires workspace readiness or a fresh rotation."
            if effective_status == "pending_rotation"
            else "Credential is blocked while workspace restrictions remain active."
        ),
    ]
    return PartnerWorkspaceIntegrationCredentialResponse(
        id=model.id,
        kind=model.credential_kind,
        status=effective_status,
        scope_key=model.scope_key,
        token_hint=model.token_hint,
        destination_ref=model.destination_ref,
        last_rotated_at=model.last_rotated_at,
        notes=notes,
    )


def _serialize_workspace_integration_delivery_log(
    item,
) -> PartnerWorkspaceIntegrationDeliveryLogResponse:
    return PartnerWorkspaceIntegrationDeliveryLogResponse(
        id=item.id,
        channel=item.channel,
        status=item.status,
        destination=item.destination,
        last_attempt_at=item.last_attempt_at,
        notes=list(item.notes),
    )


def _serialize_workspace_postback_readiness(
    item,
) -> PartnerWorkspacePostbackReadinessResponse:
    return PartnerWorkspacePostbackReadinessResponse(
        status=item.status,
        delivery_status=item.delivery_status,
        scope_label=item.scope_label,
        credential_id=item.credential.id if item.credential is not None else None,
        credential_status=(item.credential.credential_status if item.credential is not None else None),
        notes=list(item.notes),
    )


def _serialize_workspace_thread_event(
    model,
) -> PartnerWorkspaceThreadEventResponse:
    return PartnerWorkspaceThreadEventResponse(
        id=model.id,
        action_kind=model.action_kind,
        message=model.message,
        created_by_admin_user_id=model.created_by_admin_user_id,
        created_at=_normalize_utc(model.created_at),
    )


def _group_workspace_thread_events(
    events: list,
) -> dict[tuple[str, str], list[PartnerWorkspaceThreadEventResponse]]:
    grouped: dict[tuple[str, str], list[PartnerWorkspaceThreadEventResponse]] = {}
    for event in events:
        grouped.setdefault((event.subject_kind, event.subject_id), []).append(_serialize_workspace_thread_event(event))
    return grouped


def _get_subject_thread_events(
    *,
    grouped_events: dict[tuple[str, str], list[PartnerWorkspaceThreadEventResponse]] | None,
    subject_kind: str,
    subject_id: str,
) -> list[PartnerWorkspaceThreadEventResponse]:
    if not grouped_events:
        return []
    return list(grouped_events.get((subject_kind, subject_id), []))


async def _load_workspace_report_exports(
    *,
    access: PartnerWorkspaceAccess,
    db: AsyncSession,
) -> list[PartnerWorkspaceReportExportResponse]:
    reporting_context = await BuildPartnerWorkspaceReportingUseCase(db).execute(
        partner_account_id=access.workspace.id,
        order_limit=200,
        order_offset=0,
        statement_limit=100,
        statement_offset=0,
        payout_limit=100,
        payout_offset=0,
    )
    workflow_events = await ListPartnerWorkspaceWorkflowEventsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        subject_kind=_WORKSPACE_REPORT_EXPORT_SUBJECT_KIND,
        limit=200,
        offset=0,
    )
    return _build_workspace_report_exports(
        access=access,
        report_pack=reporting_context.report_pack,
        statements=reporting_context.statements,
        payout_accounts=reporting_context.payout_accounts,
        workflow_events_by_subject=_group_workspace_thread_events(workflow_events),
    )


def _build_workspace_review_requests(
    *,
    access: PartnerWorkspaceAccess,
    payout_accounts: list,
    application_review_requests: list | None = None,
    workflow_events_by_subject: dict[tuple[str, str], list[PartnerWorkspaceThreadEventResponse]] | None = None,
) -> list[PartnerWorkspaceReviewRequestResponse]:
    requests: list[PartnerWorkspaceReviewRequestResponse] = []
    now = datetime.now(UTC)
    can_operate_cases = PartnerPermission.OPERATIONS_WRITE.value in access.permission_keys

    if access.workspace.status == "needs_info":
        request_id = f"requested-info:{access.workspace.id}"
        thread_events = _get_subject_thread_events(
            grouped_events=workflow_events_by_subject,
            subject_kind=_WORKSPACE_REVIEW_REQUEST_SUBJECT_KIND,
            subject_id=request_id,
        )
        requests.append(
            PartnerWorkspaceReviewRequestResponse(
                id=request_id,
                kind="business_profile",
                due_date=now + timedelta(days=7),
                status="submitted" if thread_events else "open",
                available_actions=["submit_response"] if can_operate_cases else [],
                thread_events=thread_events,
            )
        )

    for review_request in application_review_requests or []:
        request_id = str(review_request.id)
        thread_events = _get_subject_thread_events(
            grouped_events=workflow_events_by_subject,
            subject_kind=_WORKSPACE_REVIEW_REQUEST_SUBJECT_KIND,
            subject_id=request_id,
        )
        due_date = (
            _normalize_utc(review_request.response_due_at)
            if review_request.response_due_at is not None
            else _normalize_utc(review_request.requested_at) + timedelta(days=7)
        )
        mapped_status = _map_application_review_request_status(review_request.status)
        requests.append(
            PartnerWorkspaceReviewRequestResponse(
                id=request_id,
                kind=review_request.request_kind,
                due_date=due_date,
                status=mapped_status,
                available_actions=["submit_response"] if can_operate_cases and mapped_status == "open" else [],
                thread_events=thread_events,
            )
        )

    has_ready_payout_account = any(
        account.account_status == "active"
        and account.verification_status == "verified"
        and account.approval_status == "approved"
        for account in payout_accounts
    )
    if not has_ready_payout_account:
        request_id = f"finance-profile:{access.workspace.id}"
        thread_events = _get_subject_thread_events(
            grouped_events=workflow_events_by_subject,
            subject_kind=_WORKSPACE_REVIEW_REQUEST_SUBJECT_KIND,
            subject_id=request_id,
        )
        requests.append(
            PartnerWorkspaceReviewRequestResponse(
                id=request_id,
                kind="finance_profile",
                due_date=now + timedelta(days=5),
                status="submitted" if thread_events else "open",
                available_actions=["submit_response"] if can_operate_cases else [],
                thread_events=thread_events,
            )
        )

    return requests


def _map_workspace_traffic_status(
    *,
    workspace_status: str,
    probation_sensitive: bool = False,
) -> str:
    if workspace_status in {"restricted", "suspended", "rejected", "terminated"}:
        return "blocked"
    if workspace_status == "needs_info":
        return "action_required"
    if workspace_status in {"draft", "email_verified", "submitted", "under_review", "waitlisted"}:
        return "under_review"
    if probation_sensitive and workspace_status == "approved_probation":
        return "under_review"
    return "complete"


def _build_workspace_traffic_declarations(
    *,
    traffic_declarations: list,
    creative_approvals: list,
) -> list[PartnerWorkspaceTrafficDeclarationResponse]:
    latest_declarations_by_kind: dict[str, object] = {}
    for item in sorted(
        traffic_declarations,
        key=lambda declaration: _normalize_utc(declaration.updated_at),
        reverse=True,
    ):
        latest_declarations_by_kind.setdefault(item.declaration_kind, item)

    latest_approvals_by_kind: dict[str, object] = {}
    for item in sorted(
        creative_approvals,
        key=lambda approval: _normalize_utc(approval.updated_at),
        reverse=True,
    ):
        latest_approvals_by_kind.setdefault(item.approval_kind, item)

    items: list[PartnerWorkspaceTrafficDeclarationResponse] = []
    for declaration in latest_declarations_by_kind.values():
        items.append(
            PartnerWorkspaceTrafficDeclarationResponse(
                id=str(declaration.id),
                kind=declaration.declaration_kind,
                status=declaration.declaration_status,
                scope_label=declaration.scope_label,
                updated_at=_normalize_utc(declaration.updated_at),
                notes=list(declaration.notes_payload or []),
            )
        )
    for approval in latest_approvals_by_kind.values():
        items.append(
            PartnerWorkspaceTrafficDeclarationResponse(
                id=str(approval.id),
                kind=approval.approval_kind,
                status=approval.approval_status,
                scope_label=approval.scope_label,
                updated_at=_normalize_utc(approval.updated_at),
                notes=list(approval.notes_payload or []),
            )
        )
    items.sort(key=lambda item: _normalize_utc(item.updated_at), reverse=True)
    return items


def _derive_workspace_campaign_channel(*, scope_label: str, approval_payload: dict | None) -> str:
    payload = approval_payload or {}
    candidate_values = [
        payload.get("channel"),
        payload.get("campaign_channel"),
        payload.get("placement_channel"),
    ]
    normalized_scope = scope_label.lower()

    for candidate in candidate_values:
        if isinstance(candidate, str) and candidate in _WORKSPACE_CAMPAIGN_CHANNELS:
            return candidate

    if "telegram" in normalized_scope:
        return "telegram"
    if "search" in normalized_scope or "seo" in normalized_scope:
        return "search"
    if "social" in normalized_scope or "meta" in normalized_scope or "tiktok" in normalized_scope:
        return "paid_social"
    if "storefront" in normalized_scope or "reseller" in normalized_scope:
        return "storefront"
    return "content"


def _payload_string_list(payload: dict, *keys: str) -> list[str]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
    return []


def _payload_string(payload: dict, *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _payload_datetime(payload: dict, *keys: str) -> datetime | None:
    value = _payload_string(payload, *keys)
    if value is None:
        return None
    try:
        return _normalize_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None


def _map_workspace_campaign_status(approval_status: str) -> str:
    if approval_status == CreativeApprovalStatus.COMPLETE.value:
        return "approved"
    if approval_status == CreativeApprovalStatus.UNDER_REVIEW.value:
        return "in_review"
    if approval_status in {
        CreativeApprovalStatus.SUBMITTED.value,
        CreativeApprovalStatus.ACTION_REQUIRED.value,
    }:
        return "approval_required"
    if approval_status == CreativeApprovalStatus.BLOCKED.value:
        return "restricted"
    return "available"


def _build_workspace_campaign_assets(
    *,
    creative_approvals: list,
) -> list[PartnerWorkspaceCampaignAssetResponse]:
    items: list[PartnerWorkspaceCampaignAssetResponse] = []

    for approval in sorted(
        creative_approvals,
        key=lambda approval: _normalize_utc(approval.updated_at),
        reverse=True,
    ):
        approval_payload = dict(approval.approval_payload or {})
        notes = list(approval.notes_payload or [])
        if approval.creative_ref:
            notes = [f"Creative ref: {approval.creative_ref}", *notes]

        items.append(
            PartnerWorkspaceCampaignAssetResponse(
                id=str(approval.id),
                name=approval.creative_ref or approval.scope_label,
                channel=_derive_workspace_campaign_channel(
                    scope_label=approval.scope_label,
                    approval_payload=approval_payload,
                ),
                status=_map_workspace_campaign_status(approval.approval_status),
                approval_owner=str(approval_payload.get("approval_owner") or "Partner Ops"),
                updated_at=_normalize_utc(approval.updated_at),
                promo_reference=_payload_string(
                    approval_payload,
                    "promo_reference",
                    "promo_code",
                    "campaign_key",
                ),
                disclosure_text=_payload_string(
                    approval_payload,
                    "disclosure_text",
                    "disclosure_copy",
                    "required_disclosure",
                ),
                allowed_claims=_payload_string_list(
                    approval_payload,
                    "allowed_claims",
                    "approved_claims",
                ),
                banned_claims=_payload_string_list(
                    approval_payload,
                    "banned_claims",
                    "prohibited_claims",
                ),
                allowed_geographies=_payload_string_list(
                    approval_payload,
                    "allowed_geographies",
                    "allowed_geos",
                ),
                destination_urls=_payload_string_list(
                    approval_payload,
                    "destination_urls",
                    "landing_page_urls",
                ),
                valid_from=_payload_datetime(
                    approval_payload,
                    "valid_from",
                    "starts_at",
                ),
                valid_until=_payload_datetime(
                    approval_payload,
                    "valid_until",
                    "expires_at",
                ),
                notes=notes,
            )
        )

    return items


def _workspace_has_reseller_voucher_capability(programs: PartnerWorkspaceProgramsResponse) -> bool:
    lane = next(
        (item for item in programs.lane_memberships if item.lane_key == "reseller_api"),
        None,
    )
    if lane is None:
        return False
    return lane.membership_status != "not_applied"


async def _workspace_reseller_voucher_capability_enabled(
    *,
    access: PartnerWorkspaceAccess,
    db: AsyncSession,
) -> bool:
    programs = await BuildPartnerWorkspaceProgramsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        workspace_status=access.workspace.status,
        workspace_label=access.workspace.display_name,
    )
    programs_response = PartnerWorkspaceProgramsResponse(
        canonical_source=programs.canonical_source,
        primary_lane_key=programs.primary_lane_key,
        lane_memberships=[_serialize_workspace_program_lane(item) for item in programs.lane_memberships],
        readiness_items=[_serialize_workspace_program_readiness_item(item) for item in programs.readiness_items],
        updated_at=_normalize_utc(programs.updated_at),
    )
    return _workspace_has_reseller_voucher_capability(programs_response)


async def _ensure_workspace_reseller_voucher_capability(
    *,
    access: PartnerWorkspaceAccess,
    db: AsyncSession,
) -> None:
    if not await _workspace_reseller_voucher_capability_enabled(access=access, db=db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reseller voucher batches are not enabled for this workspace",
        )


def _derive_reseller_voucher_batch_status(*, codes: list, redemption_counts: dict[UUID, int]) -> str:
    now = datetime.now(UTC)
    if codes and all((code.revoked_at is not None or code.status == "revoked") for code in codes):
        return "revoked"
    if codes and all(code.expires_at is not None and _normalize_utc(code.expires_at) <= now for code in codes):
        return "expired"

    issued_count = len(codes)
    redeemed_count = sum(1 for code in codes if redemption_counts.get(code.id, 0) > 0)
    if issued_count > 0 and redeemed_count >= issued_count:
        return "redeemed_out"
    if redeemed_count > 0:
        return "partially_redeemed"
    return "active"


def _build_reseller_voucher_batch_summary(
    *,
    batch_id: UUID,
    codes: list,
    policies_by_code_id: dict[UUID, object],
    redemption_counts: dict[UUID, int],
) -> PartnerWorkspaceResellerVoucherBatchResponse:
    first_code = codes[0]
    first_policy = policies_by_code_id.get(first_code.id)
    redeemed_count = sum(1 for code in codes if redemption_counts.get(code.id, 0) > 0)
    available_count = sum(
        1
        for code in codes
        if redemption_counts.get(code.id, 0) == 0
        and code.revoked_at is None
        and code.status != "revoked"
        and (code.expires_at is None or _normalize_utc(code.expires_at) > datetime.now(UTC))
    )
    policy_snapshot = dict(getattr(first_policy, "policy_snapshot", {}) or {})
    notes: list[str] = []
    plan_display_name = policy_snapshot.get("plan_display_name")
    if isinstance(plan_display_name, str) and plan_display_name.strip():
        notes.append(f"Plan: {plan_display_name.strip()}")
    recipient_hint = policy_snapshot.get("recipient_hint")
    if isinstance(recipient_hint, str) and recipient_hint.strip():
        notes.append(f"Recipient hint: {recipient_hint.strip()}")

    created_at = min(_normalize_utc(code.created_at) for code in codes)
    updated_at = max(_normalize_utc(code.updated_at) for code in codes)
    expires_at = max(
        (_normalize_utc(code.expires_at) for code in codes if code.expires_at is not None),
        default=None,
    )

    return PartnerWorkspaceResellerVoucherBatchResponse(
        batch_id=batch_id,
        gift_type=str(getattr(first_policy, "grant_type", "subscription_entitlement")),
        plan_family=str(getattr(first_policy, "plan_family", "unknown")),
        duration_days=int(getattr(first_policy, "duration_days", 0)),
        status=_derive_reseller_voucher_batch_status(
            codes=codes,
            redemption_counts=redemption_counts,
        ),
        issued_count=len(codes),
        redeemed_count=redeemed_count,
        available_count=available_count,
        expires_at=expires_at,
        created_at=created_at,
        updated_at=updated_at,
        notes=notes,
    )


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _build_workspace_cases(
    *,
    access: PartnerWorkspaceAccess,
    review_requests: list[PartnerWorkspaceReviewRequestResponse],
    conversion_records: list[PartnerWorkspaceConversionRecordResponse],
    statements: list,
    payout_accounts: list,
    dispute_cases: list,
    workflow_events_by_subject: dict[tuple[str, str], list[PartnerWorkspaceThreadEventResponse]] | None = None,
) -> list[PartnerWorkspaceCaseResponse]:
    cases: list[PartnerWorkspaceCaseResponse] = []
    now = datetime.now(UTC)
    can_operate_cases = PartnerPermission.OPERATIONS_WRITE.value in access.permission_keys

    def _derive_case_status(
        *,
        base_status: str,
        thread_events: list[PartnerWorkspaceThreadEventResponse],
    ) -> str:
        if base_status == "resolved":
            return base_status
        if any(
            event.action_kind in {_WORKSPACE_CASE_REPLY_ACTION, _WORKSPACE_CASE_READY_FOR_OPS_ACTION}
            for event in thread_events
        ):
            return "waiting_on_ops"
        return base_status

    def _derive_case_actions(base_status: str) -> list[str]:
        if not can_operate_cases or base_status == "resolved":
            return []
        actions = ["reply"]
        if base_status in {"open", "waiting_on_partner"}:
            actions.append("mark_ready_for_ops")
        return actions

    for request in review_requests:
        case_id = f"case:{request.id}"
        thread_events = _get_subject_thread_events(
            grouped_events=workflow_events_by_subject,
            subject_kind=_WORKSPACE_CASE_SUBJECT_KIND,
            subject_id=case_id,
        )
        base_status = "waiting_on_ops" if request.status == "submitted" else "waiting_on_partner"
        updated_at = request.due_date
        if thread_events:
            updated_at = max(updated_at, max(event.created_at for event in thread_events))
        cases.append(
            PartnerWorkspaceCaseResponse(
                id=case_id,
                kind="requested_info" if request.kind != "finance_profile" else "finance_onboarding",
                status=_derive_case_status(base_status=base_status, thread_events=thread_events),
                updated_at=_normalize_utc(updated_at),
                notes=[f"Review request kind: {request.kind}"],
                available_actions=_derive_case_actions(base_status),
                thread_events=thread_events,
            )
        )

    if access.workspace.status in {"restricted", "suspended"}:
        case_id = f"restriction:{access.workspace.id}"
        thread_events = _get_subject_thread_events(
            grouped_events=workflow_events_by_subject,
            subject_kind=_WORKSPACE_CASE_SUBJECT_KIND,
            subject_id=case_id,
        )
        updated_at = now
        if thread_events:
            updated_at = max(updated_at, max(event.created_at for event in thread_events))
        cases.append(
            PartnerWorkspaceCaseResponse(
                id=case_id,
                kind="restriction_notice",
                status=_derive_case_status(base_status="open", thread_events=thread_events),
                updated_at=_normalize_utc(updated_at),
                notes=["Workspace is running in a restricted operating posture."],
                available_actions=_derive_case_actions("open"),
                thread_events=thread_events,
            )
        )

    if any(
        statement.statement_status == "closed"
        and (float(statement.on_hold_amount or 0) > 0 or float(statement.reserve_amount or 0) > 0)
        for statement in statements
    ):
        latest_statement = max(statements, key=lambda statement: statement.updated_at)
        case_id = f"statement:{latest_statement.id}"
        thread_events = _get_subject_thread_events(
            grouped_events=workflow_events_by_subject,
            subject_kind=_WORKSPACE_CASE_SUBJECT_KIND,
            subject_id=case_id,
        )
        updated_at = _normalize_utc(latest_statement.updated_at)
        if thread_events:
            updated_at = max(updated_at, max(event.created_at for event in thread_events))
        cases.append(
            PartnerWorkspaceCaseResponse(
                id=case_id,
                kind="statement_question",
                status=_derive_case_status(base_status="waiting_on_ops", thread_events=thread_events),
                updated_at=_normalize_utc(updated_at),
                notes=["Statement still contains held or reserved amounts."],
                available_actions=_derive_case_actions("waiting_on_ops"),
                thread_events=thread_events,
            )
        )

    if payout_accounts and any(
        account.account_status in {"suspended", "archived"}
        or account.approval_status != "approved"
        or account.verification_status != "verified"
        for account in payout_accounts
    ):
        newest_account = max(payout_accounts, key=lambda account: account.updated_at)
        case_id = f"payout-account:{newest_account.id}"
        thread_events = _get_subject_thread_events(
            grouped_events=workflow_events_by_subject,
            subject_kind=_WORKSPACE_CASE_SUBJECT_KIND,
            subject_id=case_id,
        )
        updated_at = _normalize_utc(newest_account.updated_at)
        if thread_events:
            updated_at = max(updated_at, max(event.created_at for event in thread_events))
        cases.append(
            PartnerWorkspaceCaseResponse(
                id=case_id,
                kind="finance_onboarding",
                status=_derive_case_status(base_status="waiting_on_partner", thread_events=thread_events),
                updated_at=updated_at,
                notes=["Payout account requires review or verification before settlement can proceed."],
                available_actions=_derive_case_actions("waiting_on_partner"),
                thread_events=thread_events,
            )
        )

    dispute_case_order_ids = {str(item.order_id) for item in dispute_cases if item.order_id is not None}
    for item in dispute_cases:
        notes = [item.summary, *list(item.notes_payload or [])]
        case_id = str(item.id)
        thread_events = _get_subject_thread_events(
            grouped_events=workflow_events_by_subject,
            subject_kind=_WORKSPACE_CASE_SUBJECT_KIND,
            subject_id=case_id,
        )
        updated_at = _normalize_utc(item.updated_at)
        if thread_events:
            updated_at = max(updated_at, max(event.created_at for event in thread_events))
        cases.append(
            PartnerWorkspaceCaseResponse(
                id=case_id,
                kind=item.case_kind,
                status=_derive_case_status(base_status=item.case_status, thread_events=thread_events),
                updated_at=updated_at,
                notes=notes,
                available_actions=_derive_case_actions(item.case_status),
                thread_events=thread_events,
            )
        )

    for record in conversion_records:
        if record.kind == "chargeback" and record.id not in dispute_case_order_ids:
            case_id = f"dispute:{record.id}"
            thread_events = _get_subject_thread_events(
                grouped_events=workflow_events_by_subject,
                subject_kind=_WORKSPACE_CASE_SUBJECT_KIND,
                subject_id=case_id,
            )
            base_status = "waiting_on_ops" if record.status == "on_hold" else "resolved"
            updated_at = _normalize_utc(record.updated_at)
            if thread_events:
                updated_at = max(updated_at, max(event.created_at for event in thread_events))
            cases.append(
                PartnerWorkspaceCaseResponse(
                    id=case_id,
                    kind="payout_dispute",
                    status=_derive_case_status(base_status=base_status, thread_events=thread_events),
                    updated_at=updated_at,
                    notes=list(record.notes),
                    available_actions=_derive_case_actions(base_status),
                    thread_events=thread_events,
                )
            )

    cases.sort(key=lambda item: _normalize_utc(item.updated_at), reverse=True)
    deduped: list[PartnerWorkspaceCaseResponse] = []
    seen_ids: set[str] = set()
    for item in cases:
        if item.id in seen_ids:
            continue
        seen_ids.add(item.id)
        deduped.append(item)
    return deduped


async def _load_workspace_review_requests(
    *,
    access: PartnerWorkspaceAccess,
    db: AsyncSession,
) -> list[PartnerWorkspaceReviewRequestResponse]:
    application_workflow = PartnerApplicationWorkflowUseCase(db)
    payout_accounts = await ListPartnerPayoutAccountsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        limit=100,
        offset=0,
    )
    application_review_requests = await application_workflow.list_review_requests(
        partner_account_id=access.workspace.id,
    )
    review_request_events = await ListPartnerWorkspaceWorkflowEventsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        subject_kind=_WORKSPACE_REVIEW_REQUEST_SUBJECT_KIND,
        limit=500,
        offset=0,
    )
    return _build_workspace_review_requests(
        access=access,
        payout_accounts=payout_accounts,
        application_review_requests=application_review_requests,
        workflow_events_by_subject=_group_workspace_thread_events(review_request_events),
    )


async def _load_workspace_cases(
    *,
    access: PartnerWorkspaceAccess,
    db: AsyncSession,
) -> list[PartnerWorkspaceCaseResponse]:
    reporting_context = await BuildPartnerWorkspaceReportingUseCase(db).execute(
        partner_account_id=access.workspace.id,
        order_limit=200,
        order_offset=0,
        statement_limit=100,
        statement_offset=0,
        payout_limit=100,
        payout_offset=0,
    )
    review_requests = await _load_workspace_review_requests(access=access, db=db)
    dispute_cases = await ListDisputeCasesUseCase(db).execute(
        partner_account_id=access.workspace.id,
        limit=100,
        offset=0,
    )
    case_events = await ListPartnerWorkspaceWorkflowEventsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        subject_kind=_WORKSPACE_CASE_SUBJECT_KIND,
        limit=500,
        offset=0,
    )
    return _build_workspace_cases(
        access=access,
        review_requests=review_requests,
        conversion_records=[_serialize_workspace_conversion_record(item) for item in reporting_context.order_items],
        statements=reporting_context.statements,
        payout_accounts=reporting_context.payout_accounts,
        dispute_cases=dispute_cases,
        workflow_events_by_subject=_group_workspace_thread_events(case_events),
    )


async def _build_partner_application_detail_response(
    *,
    draft,
    workspace,
    db: AsyncSession,
    access: PartnerWorkspaceAccess | None = None,
) -> PartnerApplicationDraftDetailResponse:
    workflow = PartnerApplicationWorkflowUseCase(db)
    workflow_events = await ListPartnerWorkspaceWorkflowEventsUseCase(db).execute(
        partner_account_id=workspace.id,
        subject_kind=_WORKSPACE_REVIEW_REQUEST_SUBJECT_KIND,
        limit=500,
        offset=0,
    )
    thread_events = _group_workspace_thread_events(workflow_events)
    lane_applications = await workflow.list_lane_applications(partner_account_id=workspace.id)
    review_requests = await workflow.list_review_requests(partner_account_id=workspace.id)
    attachments = await workflow.list_attachments(partner_account_id=workspace.id)
    return PartnerApplicationDraftDetailResponse(
        draft=_serialize_partner_application_draft_response(
            draft,
            workspace,
            access=access,
        ),
        lane_applications=[_serialize_partner_lane_application_response(item) for item in lane_applications],
        review_requests=[
            _serialize_partner_application_review_request_detail(
                item,
                thread_events=_get_subject_thread_events(
                    grouped_events=thread_events,
                    subject_kind=_WORKSPACE_REVIEW_REQUEST_SUBJECT_KIND,
                    subject_id=str(item.id),
                ),
            )
            for item in review_requests
        ],
        attachments=[_serialize_partner_application_attachment_response(item) for item in attachments],
    )


# ---------------------------------------------------------------------------
# Partner (mobile-user) endpoints
# ---------------------------------------------------------------------------


async def _require_active_mobile_partner_user(
    db: AsyncSession,
    partner_repo: PartnerRepository,
    user_id: UUID,
) -> MobileUserModel:
    mobile_user = await db.get(MobileUserModel, user_id)
    if mobile_user is None or not mobile_user.is_partner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Partner account is required")
    if mobile_user.partner_account_id is not None:
        partner_account = await partner_repo.get_account_by_id(mobile_user.partner_account_id)
        if partner_account is None or partner_account.status != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Partner account is not active")
    return mobile_user


@router.post("/partner/codes", response_model=PartnerCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_partner_code(
    body: CreatePartnerCodeRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> PartnerCodeResponse:
    """Create a new partner referral code with an optional markup percentage."""
    config_repo = SystemConfigRepository(db)
    config_service = ConfigService(config_repo)
    partner_repo = PartnerRepository(db)
    mobile_user = await db.get(MobileUserModel, user_id)

    use_case = CreatePartnerCodeUseCase(partner_repo, config_service)
    try:
        code_model = await use_case.execute(
            user_id,
            body.code,
            body.markup_pct,
            partner_account_id=mobile_user.partner_account_id if mobile_user else None,
            is_partner_user=bool(mobile_user and mobile_user.is_partner),
        )
    except NotAPartnerError as exc:
        track_partner_operation(operation="create_code")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message) from exc
    except MarkupExceedsLimitError as exc:
        track_partner_operation(operation="create_code")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.message) from exc
    except DomainError as exc:
        track_partner_operation(operation="create_code")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    track_partner_operation(operation="create_code")
    return PartnerCodeResponse.model_validate(code_model)


@router.get("/partner/codes", response_model=list[PartnerCodeResponse])
async def list_partner_codes(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerCodeResponse]:
    """List all partner codes owned by the authenticated user."""
    partner_repo = PartnerRepository(db)
    mobile_user = await _require_active_mobile_partner_user(db, partner_repo, user_id)
    if mobile_user.partner_account_id is not None:
        codes = await partner_repo.get_codes_by_account(mobile_user.partner_account_id)
    else:
        codes = await partner_repo.get_codes_by_partner(user_id)
    track_partner_operation(operation="list_codes")
    return [PartnerCodeResponse.model_validate(code) for code in codes]


@router.put("/partner/codes/{code_id}", response_model=PartnerCodeResponse)
async def update_partner_code_markup(
    code_id: UUID,
    body: UpdateMarkupRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> PartnerCodeResponse:
    """Update the markup percentage on a partner code owned by the authenticated user."""
    partner_repo = PartnerRepository(db)
    config_repo = SystemConfigRepository(db)
    config_service = ConfigService(config_repo)

    code_model = await partner_repo.get_code_by_id(code_id)
    if code_model is None or code_model.partner_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner code not found")
    mobile_user = await db.get(MobileUserModel, user_id)
    if mobile_user is None or not mobile_user.is_partner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Partner account is required")
    if code_model.partner_account_id is not None:
        partner_account = await partner_repo.get_account_by_id(code_model.partner_account_id)
        if partner_account is None or partner_account.status != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Partner account is not active")
    if not code_model.is_active or code_model.lifecycle_status != "active" or code_model.approval_status != "approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Partner code is not eligible for updates")
    if body.markup_pct < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Partner code markup cannot be negative",
        )

    max_markup = await config_service.get_partner_max_markup_pct()
    if body.markup_pct > max_markup:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Markup {body.markup_pct}% exceeds maximum {max_markup}%",
        )

    code_model.markup_pct = Decimal(str(body.markup_pct))
    code_model.version = int(code_model.version or 1) + 1
    commission_contract = build_commission_contract_model(
        code_model=code_model,
        commission_pct=_resolve_base_commission_pct(await config_service.get_partner_tiers()),
        payout_hold_days=await config_service.get_partner_payout_hold_days(owner_type=code_model.owner_type),
        source="partner_code_markup_update",
        contract_id=uuid4(),
    )
    await partner_repo.attach_commission_contract_to_code(code_model, commission_contract)
    updated = await partner_repo.update_code(code_model)
    track_partner_operation(operation="update_code")
    return PartnerCodeResponse.model_validate(updated)


@router.get("/partner/dashboard", response_model=PartnerDashboardResponse)
async def get_partner_dashboard(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> PartnerDashboardResponse:
    """Return aggregated partner dashboard data."""
    config_repo = SystemConfigRepository(db)
    config_service = ConfigService(config_repo)
    partner_repo = PartnerRepository(db)
    mobile_user = await _require_active_mobile_partner_user(db, partner_repo, user_id)

    use_case = PartnerDashboardUseCase(partner_repo, config_service)
    try:
        result = await use_case.execute(
            user_id,
            partner_account_id=mobile_user.partner_account_id if mobile_user else None,
        )
    except DomainError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    track_partner_operation(operation="dashboard")

    return PartnerDashboardResponse(
        total_clients=result["total_clients"],
        total_earned=result["total_earned"],
        current_tier=result["current_tier"],
        codes=[
            {
                "id": str(c.id),
                "code": c.code,
                "markup_pct": float(c.markup_pct),
                "is_active": c.is_active,
                "created_at": c.created_at.isoformat(),
            }
            for c in result["codes"]
        ],
    )


@router.get("/partner/earnings", response_model=list[PartnerEarningResponse])
async def list_partner_earnings(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerEarningResponse]:
    """List recent earnings for the authenticated partner."""
    partner_repo = PartnerRepository(db)
    mobile_user = await _require_active_mobile_partner_user(db, partner_repo, user_id)
    if mobile_user.partner_account_id is not None:
        earnings = await partner_repo.get_earnings_by_account(mobile_user.partner_account_id)
    else:
        earnings = await partner_repo.get_earnings_by_partner(user_id)
    track_partner_operation(operation="list_earnings")
    return [PartnerEarningResponse.model_validate(earning) for earning in earnings]


@router.post("/partner/bind", status_code=status.HTTP_200_OK)
async def bind_to_partner(
    body: BindPartnerRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bind the authenticated user to a partner via a partner code."""
    partner_repo = PartnerRepository(db)
    use_case = BindPartnerUseCase(db, partner_repo)
    try:
        await use_case.execute(user_id, body.partner_code)
    except PartnerCodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except UserAlreadyBoundToPartnerError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    track_partner_operation(operation="bind")
    return {"status": "bound"}


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------


@router.post("/admin/partners/promote", response_model=PromotePartnerResponse, status_code=status.HTTP_200_OK)
async def admin_promote_partner(
    body: PromotePartnerRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PromotePartnerResponse:
    """Admin action to promote a mobile user to partner status."""
    use_case = AdminPromotePartnerUseCase(db)
    try:
        user, partner_account_id = await use_case.execute(body.user_id, created_by_admin_user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    track_partner_operation(operation="promote")
    return PromotePartnerResponse(status="promoted", user_id=user.id, partner_account_id=partner_account_id)


@router.post(
    "/admin/partner-workspaces",
    response_model=PartnerWorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_partner_workspace(
    body: CreatePartnerWorkspaceRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceResponse:
    partner_account_repo = PartnerAccountRepository(db)
    use_case = CreatePartnerWorkspaceUseCase(db, partner_account_repo)
    try:
        workspace, _membership = await use_case.execute(
            display_name=body.display_name,
            account_key=body.account_key,
            legacy_owner_user_id=body.legacy_owner_user_id,
            owner_admin_user_id=body.owner_admin_user_id,
            created_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    payload = await GetPartnerWorkspaceUseCase(partner_account_repo, PartnerRepository(db)).execute(workspace.id)
    track_partner_operation(operation="create_workspace")
    return _serialize_workspace_response(payload)


@router.get(
    "/admin/partner-workspaces",
    response_model=list[PartnerWorkspaceResponse],
)
async def list_admin_partner_workspaces(
    search: str | None = Query(None),
    workspace_status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceResponse]:
    partner_account_repo = PartnerAccountRepository(db)
    accounts = await partner_account_repo.list_accounts(
        search=search,
        status=workspace_status,
        limit=limit,
        offset=offset,
    )
    workspace_reader = GetPartnerWorkspaceUseCase(partner_account_repo, PartnerRepository(db))
    payloads = [await workspace_reader.execute(account.id) for account in accounts]
    track_partner_operation(operation="list_admin_workspaces")
    return [_serialize_workspace_response(payload) for payload in payloads]


@router.get(
    "/admin/partner-workspaces/{workspace_id}",
    response_model=PartnerWorkspaceResponse,
)
async def get_admin_partner_workspace(
    workspace_id: UUID,
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceResponse:
    partner_account_repo = PartnerAccountRepository(db)
    try:
        payload = await GetPartnerWorkspaceUseCase(partner_account_repo, PartnerRepository(db)).execute(workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    track_partner_operation(operation="get_workspace_admin")
    return _serialize_workspace_response(payload)


@router.get(
    "/admin/partner-workspaces/{workspace_id}/ops-overview",
    response_model=PartnerAdminOpsOverviewResponse,
)
async def get_admin_partner_workspace_ops_overview(
    workspace_id: UUID,
    _current_user: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> PartnerAdminOpsOverviewResponse:
    overview = await _load_partner_admin_ops_overview(workspace_id=workspace_id, db=db)
    track_partner_operation(operation="get_admin_workspace_ops_overview")
    return overview


@router.get(
    "/admin/partner-workspaces/{workspace_id}/payout-review-queue",
    response_model=list[PartnerAdminPayoutReviewItemResponse],
)
async def list_admin_partner_workspace_payout_review_queue(
    workspace_id: UUID,
    _current_user: AdminUserModel = Depends(require_role(AdminRole.FINANCE)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerAdminPayoutReviewItemResponse]:
    overview = await _load_partner_admin_ops_overview(workspace_id=workspace_id, db=db)
    track_partner_operation(operation="list_admin_workspace_payout_review_queue")
    return overview.payout_review_queue


@router.patch(
    "/admin/partner-workspaces/{workspace_id}/status",
    response_model=PartnerWorkspaceResponse,
)
async def update_admin_partner_workspace_status(
    workspace_id: UUID,
    body: UpdatePartnerWorkspaceStatusRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceResponse:
    if body.workspace_status not in _WORKSPACE_ADMIN_STATUS_VALUES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid partner workspace status")

    partner_account_repo = PartnerAccountRepository(db)
    workspace = await partner_account_repo.get_account_by_id(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner workspace not found")

    previous_status = workspace.status
    workspace.status = body.workspace_status
    await partner_account_repo.update_account(workspace)
    reason = body.reason or "No reason provided"
    try:
        await CreatePartnerWorkspaceWorkflowEventUseCase(db).execute(
            partner_account_id=workspace.id,
            subject_kind=_WORKSPACE_ADMIN_OPS_SUBJECT_KIND,
            subject_id=f"workspace:{workspace.id}",
            action_kind=_WORKSPACE_STATUS_CHANGED_ACTION,
            message=f"Workspace status changed from {previous_status} to {body.workspace_status}: {reason}",
            event_payload={
                "old_status": previous_status,
                "new_status": body.workspace_status,
                "reason": reason,
                "stage": "S3-STAGE-12",
            },
            created_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    payload = await GetPartnerWorkspaceUseCase(partner_account_repo, PartnerRepository(db)).execute(workspace.id)
    track_partner_operation(operation=f"update_workspace_status:{body.workspace_status}")
    return _serialize_workspace_response(payload)


@router.patch(
    "/admin/partner-workspaces/{workspace_id}/codes/{code_id}/status",
    response_model=PartnerWorkspaceCodeResponse,
)
async def update_admin_partner_workspace_code_status(
    workspace_id: UUID,
    code_id: UUID,
    body: UpdatePartnerWorkspaceCodeStatusRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceCodeResponse:
    partner_account_repo = PartnerAccountRepository(db)
    workspace = await partner_account_repo.get_account_by_id(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner workspace not found")

    partner_repo = PartnerRepository(db)
    code_model = await partner_repo.get_code_by_id(code_id)
    if code_model is None or code_model.partner_account_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner code not found")

    previous_active = bool(code_model.is_active)
    code_model.is_active = body.is_active
    code_model.lifecycle_status = "active" if body.is_active else "paused"
    code_model.version = int(code_model.version or 1) + 1
    updated = await partner_repo.update_code(code_model)
    try:
        await CreatePartnerWorkspaceWorkflowEventUseCase(db).execute(
            partner_account_id=workspace.id,
            subject_kind=_WORKSPACE_PARTNER_CODE_SUBJECT_KIND,
            subject_id=str(updated.id),
            action_kind=_WORKSPACE_PARTNER_CODE_STATUS_CHANGED_ACTION,
            message=(
                f"Partner code {updated.code} active status changed from "
                f"{previous_active} to {body.is_active}: {body.reason}"
            ),
            event_payload={
                "code_id": str(updated.id),
                "code": updated.code,
                "old_is_active": previous_active,
                "new_is_active": body.is_active,
                "reason": body.reason,
                "stage": "S3-STAGE-12",
            },
            created_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    track_partner_operation(operation=f"admin_workspace_code_status:{body.is_active}")
    return _serialize_workspace_code(updated)


@router.get(
    "/admin/partner-applications",
    response_model=list[PartnerApplicationAdminSummaryResponse],
)
async def list_admin_partner_applications(
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerApplicationAdminSummaryResponse]:
    workflow = PartnerApplicationWorkflowUseCase(db)
    partner_account_repo = PartnerAccountRepository(db)
    admin_users = AdminUserRepository(db)
    drafts = await workflow.list_admin_application_drafts()
    applicants = await admin_users.list_by_ids(
        [draft.applicant_admin_user_id for draft in drafts if draft.applicant_admin_user_id is not None],
    )
    applicant_by_id = {item.id: item for item in applicants}
    responses: list[PartnerApplicationAdminSummaryResponse] = []
    for draft in drafts:
        workspace = await partner_account_repo.get_account_by_id(draft.partner_account_id)
        if workspace is None:
            continue
        lane_applications = await workflow.list_lane_applications(partner_account_id=workspace.id)
        review_requests = await workflow.list_review_requests(partner_account_id=workspace.id)
        responses.append(
            PartnerApplicationAdminSummaryResponse(
                workspace=_serialize_partner_application_workspace_summary(workspace),
                applicant=_serialize_partner_application_applicant_summary(
                    applicant_by_id.get(draft.applicant_admin_user_id)
                    if draft.applicant_admin_user_id is not None
                    else None
                ),
                primary_lane=(str((draft.draft_payload or {}).get("primary_lane") or "") or None),
                review_ready=draft.review_ready,
                submitted_at=_normalize_utc(draft.submitted_at) if draft.submitted_at is not None else None,
                updated_at=_normalize_utc(draft.updated_at),
                open_review_request_count=sum(1 for item in review_requests if item.status == "open"),
                lane_statuses=sorted({item.status for item in lane_applications}),
            )
        )
    track_partner_operation(operation="list_admin_partner_applications")
    return responses


@router.get(
    "/admin/partner-applications/{workspace_id}",
    response_model=PartnerApplicationAdminDetailResponse,
)
async def get_admin_partner_application(
    workspace_id: UUID,
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PartnerApplicationAdminDetailResponse:
    workflow = PartnerApplicationWorkflowUseCase(db)
    partner_account_repo = PartnerAccountRepository(db)
    admin_users = AdminUserRepository(db)
    draft = await workflow.get_draft_by_partner_account(partner_account_id=workspace_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner application draft not found")
    workspace = await partner_account_repo.get_account_by_id(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner workspace not found")
    detail = await _build_partner_application_detail_response(
        draft=draft,
        workspace=workspace,
        db=db,
    )
    applicant = (
        await admin_users.get_by_id(draft.applicant_admin_user_id)
        if draft.applicant_admin_user_id is not None
        else None
    )
    track_partner_operation(operation="get_admin_partner_application")
    return PartnerApplicationAdminDetailResponse(
        workspace=_serialize_partner_application_workspace_summary(workspace),
        applicant=_serialize_partner_application_applicant_summary(applicant),
        draft=detail.draft,
        lane_applications=detail.lane_applications,
        review_requests=detail.review_requests,
        attachments=detail.attachments,
    )


@router.post(
    "/admin/partner-applications/{workspace_id}/request-info",
    response_model=PartnerApplicationReviewRequestDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_admin_partner_application_info(
    workspace_id: UUID,
    body: RequestPartnerApplicationInfoRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PartnerApplicationReviewRequestDetailResponse:
    workflow = PartnerApplicationWorkflowUseCase(db)
    try:
        review_request = await workflow.request_info(
            partner_account_id=workspace_id,
            message=body.message,
            request_kind=body.request_kind,
            required_fields=body.required_fields,
            required_attachments=body.required_attachments,
            requested_by_admin_user_id=current_user.id,
            lane_application_id=body.lane_application_id,
            response_due_at=body.response_due_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    workflow_events = await ListPartnerWorkspaceWorkflowEventsUseCase(db).execute(
        partner_account_id=workspace_id,
        subject_kind=_WORKSPACE_REVIEW_REQUEST_SUBJECT_KIND,
        limit=500,
        offset=0,
    )
    grouped_events = _group_workspace_thread_events(workflow_events)
    track_partner_operation(operation="request_admin_partner_application_info")
    return _serialize_partner_application_review_request_detail(
        review_request,
        thread_events=_get_subject_thread_events(
            grouped_events=grouped_events,
            subject_kind=_WORKSPACE_REVIEW_REQUEST_SUBJECT_KIND,
            subject_id=str(review_request.id),
        ),
    )


@router.post(
    "/admin/partner-applications/{workspace_id}/approve-probation",
    response_model=PartnerApplicationAdminDetailResponse,
)
async def approve_admin_partner_application_probation(
    workspace_id: UUID,
    body: PartnerApplicationReviewDecisionRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PartnerApplicationAdminDetailResponse:
    workflow = PartnerApplicationWorkflowUseCase(db)
    try:
        await workflow.approve_probation(
            partner_account_id=workspace_id,
            reviewer_admin_user_id=current_user.id,
            reason_code=body.reason_code,
            reason_summary=body.reason_summary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return await get_admin_partner_application(workspace_id=workspace_id, _current_user=current_user, db=db)


@router.post(
    "/admin/partner-applications/{workspace_id}/waitlist",
    response_model=PartnerApplicationAdminDetailResponse,
)
async def waitlist_admin_partner_application(
    workspace_id: UUID,
    body: PartnerApplicationReviewDecisionRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PartnerApplicationAdminDetailResponse:
    workflow = PartnerApplicationWorkflowUseCase(db)
    try:
        await workflow.waitlist(
            partner_account_id=workspace_id,
            reviewer_admin_user_id=current_user.id,
            reason_code=body.reason_code,
            reason_summary=body.reason_summary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return await get_admin_partner_application(workspace_id=workspace_id, _current_user=current_user, db=db)


@router.post(
    "/admin/partner-applications/{workspace_id}/reject",
    response_model=PartnerApplicationAdminDetailResponse,
)
async def reject_admin_partner_application(
    workspace_id: UUID,
    body: PartnerApplicationReviewDecisionRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PartnerApplicationAdminDetailResponse:
    workflow = PartnerApplicationWorkflowUseCase(db)
    try:
        await workflow.reject(
            partner_account_id=workspace_id,
            reviewer_admin_user_id=current_user.id,
            reason_code=body.reason_code,
            reason_summary=body.reason_summary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return await get_admin_partner_application(workspace_id=workspace_id, _current_user=current_user, db=db)


@router.post(
    "/admin/partner-applications/{workspace_id}/lane-applications/{lane_application_id}/approve",
    response_model=PartnerLaneApplicationResponse,
)
async def approve_admin_partner_lane_application(
    workspace_id: UUID,
    lane_application_id: UUID,
    body: PartnerApplicationReviewDecisionRequest,
    target_status: str = Query("approved_probation"),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PartnerLaneApplicationResponse:
    if target_status not in {"approved_probation", "approved_active"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported lane approval target status",
        )
    try:
        item = await PartnerApplicationWorkflowUseCase(db).approve_lane(
            lane_application_id=lane_application_id,
            reviewer_admin_user_id=current_user.id,
            target_status=target_status,
            reason_code=body.reason_code,
            reason_summary=body.reason_summary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if item.partner_account_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lane application not found")
    track_partner_operation(operation="approve_admin_partner_lane_application")
    return _serialize_partner_lane_application_response(item)


@router.post(
    "/admin/partner-applications/{workspace_id}/lane-applications/{lane_application_id}/decline",
    response_model=PartnerLaneApplicationResponse,
)
async def decline_admin_partner_lane_application(
    workspace_id: UUID,
    lane_application_id: UUID,
    body: PartnerApplicationReviewDecisionRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PartnerLaneApplicationResponse:
    try:
        item = await PartnerApplicationWorkflowUseCase(db).decline_lane(
            lane_application_id=lane_application_id,
            reviewer_admin_user_id=current_user.id,
            reason_code=body.reason_code,
            reason_summary=body.reason_summary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if item.partner_account_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lane application not found")
    track_partner_operation(operation="decline_admin_partner_lane_application")
    return _serialize_partner_lane_application_response(item)


@router.get("/partner-workspaces/me", response_model=list[PartnerWorkspaceResponse])
async def list_my_partner_workspaces(
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceResponse]:
    partner_account_repo = PartnerAccountRepository(db)
    accounts = await partner_account_repo.list_accounts_for_admin_user(current_user.id)
    workspace_reader = GetPartnerWorkspaceUseCase(partner_account_repo, PartnerRepository(db))
    payloads = [await workspace_reader.execute(account.id) for account in accounts]
    track_partner_operation(operation="list_my_workspaces")
    return [_serialize_workspace_response(payload) for payload in payloads]


@router.get(
    "/partner-session/bootstrap",
    response_model=PartnerSessionBootstrapResponse,
)
async def get_partner_session_bootstrap(
    workspace_id: UUID | None = Query(None),
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerSessionBootstrapResponse:
    started_at = perf_counter()
    bind_partner_context_from_realm(
        current_realm=current_realm,
        route_group="bootstrap",
        principal_class=get_principal_type_for_realm(current_realm),
    )
    if current_realm.realm_type != "partner":
        bind_partner_runtime_context(
            surface=PARTNER_PORTAL_SURFACE,
            realm_type=current_realm.realm_type,
            principal_class=get_principal_type_for_realm(current_realm),
            route_group="bootstrap",
            workspace_status="none",
            result="failure",
            error_code="partner_realm_required",
        )
        observe_partner_bootstrap(
            duration_seconds=max(perf_counter() - started_at, 0.0),
            workspace_status="none",
            result="failure",
            reason="partner_realm_required",
        )
        log_partner_runtime_event(
            "partner_session.bootstrap_failed",
            level="warning",
            reason="partner_realm_required",
            realm_type=current_realm.realm_type,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner realm session is required for partner bootstrap",
        )

    partner_account_repo = PartnerAccountRepository(db)
    partner_repo = PartnerRepository(db)
    workspace_reader = GetPartnerWorkspaceUseCase(partner_account_repo, partner_repo)
    accounts = await partner_account_repo.list_accounts_for_admin_user(current_user.id)

    serialized_workspaces: list[PartnerWorkspaceResponse] = []
    access_by_workspace_id: dict[UUID, PartnerWorkspaceAccess] = {}
    for account in accounts:
        access = await resolve_partner_workspace_access(
            workspace_id=account.id,
            current_user=current_user,
            db=db,
        )
        access_by_workspace_id[account.id] = access
        payload = await workspace_reader.execute(account.id)
        serialized_workspaces.append(_serialize_workspace_response(payload, access=access))

    active_workspace = None
    active_access = None
    if serialized_workspaces:
        if workspace_id is not None:
            active_workspace = next(
                (item for item in serialized_workspaces if item.id == workspace_id),
                None,
            )
            if active_workspace is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Partner workspace is not available for the current session",
                )
        else:
            active_workspace = serialized_workspaces[0]

        active_access = access_by_workspace_id.get(active_workspace.id)

    programs_response = None
    current_permission_keys: list[str] = []
    review_requests: list[PartnerWorkspaceReviewRequestResponse] = []
    cases: list[PartnerWorkspaceCaseResponse] = []
    workspace_resolution = "none"
    updated_at = datetime.now(UTC)

    if active_workspace is not None and active_access is not None:
        workspace_resolution = "requested" if workspace_id is not None else "default"
        current_permission_keys = sorted(active_access.permission_keys)
        programs = await BuildPartnerWorkspaceProgramsUseCase(db).execute(
            partner_account_id=active_access.workspace.id,
            workspace_status=active_access.workspace.status,
            workspace_label=active_access.workspace.display_name,
        )
        programs_response = PartnerWorkspaceProgramsResponse(
            canonical_source=programs.canonical_source,
            primary_lane_key=programs.primary_lane_key,
            lane_memberships=[_serialize_workspace_program_lane(item) for item in programs.lane_memberships],
            readiness_items=[_serialize_workspace_program_readiness_item(item) for item in programs.readiness_items],
            updated_at=_normalize_utc(programs.updated_at),
        )
        if PartnerPermission.WORKSPACE_READ.value in active_access.permission_keys:
            review_requests = await _load_workspace_review_requests(access=active_access, db=db)
            cases = await _load_workspace_cases(access=active_access, db=db)
        updated_at_candidates = [
            active_workspace.last_activity_at,
            programs_response.updated_at if programs_response is not None else None,
            *(item.due_date for item in review_requests),
            *(item.updated_at for item in cases),
        ]
        normalized_candidates = [_normalize_utc(item) for item in updated_at_candidates if item is not None]
        if normalized_candidates:
            updated_at = max(normalized_candidates)

    finance_readiness = _get_workspace_program_readiness_status(
        programs_response,
        "finance",
        default="not_started",
    )
    compliance_readiness = _get_workspace_program_readiness_status(
        programs_response,
        "compliance",
        default="not_started",
    )
    technical_readiness = _get_workspace_program_readiness_status(
        programs_response,
        "technical",
        default="not_required",
    )
    governance_state = _derive_partner_governance_state(
        workspace_status=active_workspace.status if active_workspace is not None else "draft",
        programs=programs_response,
    )
    release_ring = _derive_partner_release_ring(
        workspace_status=active_workspace.status if active_workspace is not None else "draft",
        primary_lane_key=programs_response.primary_lane_key if programs_response is not None else None,
        permission_keys=current_permission_keys,
    )
    pending_tasks = _build_partner_session_pending_tasks(
        review_requests=review_requests,
        finance_readiness=finance_readiness,
        compliance_readiness=compliance_readiness,
        technical_readiness=technical_readiness,
    )
    blocked_reasons = _build_partner_session_blocked_reasons(
        workspace_status=active_workspace.status if active_workspace is not None else "draft",
        programs=programs_response,
        finance_readiness=finance_readiness,
        compliance_readiness=compliance_readiness,
        technical_readiness=technical_readiness,
        governance_state=governance_state,
    )
    notification_counters = PartnerNotificationCountersResponse()
    if active_access is not None:
        notification_counters = await _build_partner_notification_counters(
            access=active_access,
            current_user=current_user,
            db=db,
        )

    track_partner_operation(operation="get_session_bootstrap")
    active_workspace_status = active_workspace.status if active_workspace is not None else "none"
    primary_blocked_reason = blocked_reasons[0].code if blocked_reasons else None
    bind_partner_context_from_realm(
        current_realm=current_realm,
        route_group="bootstrap",
        principal_class=get_principal_type_for_realm(current_realm),
        workspace_status=active_workspace_status,
        blocked_reason=primary_blocked_reason,
        result="success",
    )
    observe_partner_bootstrap(
        duration_seconds=max(perf_counter() - started_at, 0.0),
        workspace_status=active_workspace_status,
        result="success",
    )
    log_partner_runtime_event(
        "partner_session.bootstrap_loaded",
        workspace_id=str(active_workspace.id) if active_workspace is not None else None,
        workspace_status=active_workspace_status,
        release_ring=release_ring,
        pending_task_count=len(pending_tasks),
        blocked_reason_codes=[item.code for item in blocked_reasons],
        unread_notifications=notification_counters.unread_notifications,
    )
    return PartnerSessionBootstrapResponse(
        principal=_build_partner_session_principal_response(
            user=current_user,
            current_realm=current_realm,
        ),
        workspaces=serialized_workspaces,
        active_workspace_id=active_workspace.id if active_workspace is not None else None,
        active_workspace=active_workspace,
        workspace_resolution=workspace_resolution,
        programs=programs_response,
        release_ring=release_ring,
        finance_readiness=finance_readiness,
        compliance_readiness=compliance_readiness,
        technical_readiness=technical_readiness,
        governance_state=governance_state,
        current_permission_keys=current_permission_keys,
        counters=PartnerSessionBootstrapCounterResponse(
            open_review_requests=sum(1 for item in review_requests if item.status == "open"),
            open_cases=sum(1 for item in cases if item.status != "resolved"),
            unread_notifications=notification_counters.unread_notifications,
            pending_tasks=len(pending_tasks),
        ),
        pending_tasks=pending_tasks,
        blocked_reasons=blocked_reasons,
        updated_at=_normalize_utc(updated_at),
    )


@router.get(
    "/partner-notifications",
    response_model=list[PartnerNotificationFeedItemResponse],
)
async def list_partner_notifications(
    workspace_id: UUID | None = Query(None),
    include_archived: bool = Query(False),
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerNotificationFeedItemResponse]:
    _require_partner_realm(current_realm)
    access = await _resolve_partner_session_workspace_access(
        current_user=current_user,
        db=db,
        workspace_id=workspace_id,
    )
    track_partner_operation(operation="list_partner_notifications")
    return await _build_partner_notification_feed(
        access=access,
        current_user=current_user,
        db=db,
        include_archived=include_archived,
    )


@router.get(
    "/partner-notifications/counters",
    response_model=PartnerNotificationCountersResponse,
)
async def get_partner_notification_counters(
    workspace_id: UUID | None = Query(None),
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerNotificationCountersResponse:
    _require_partner_realm(current_realm)
    access = await _resolve_partner_session_workspace_access(
        current_user=current_user,
        db=db,
        workspace_id=workspace_id,
    )
    track_partner_operation(operation="get_partner_notification_counters")
    return await _build_partner_notification_counters(
        access=access,
        current_user=current_user,
        db=db,
    )


@router.post(
    "/partner-notifications/{notification_id}/read",
    response_model=PartnerNotificationReadStateResponse,
)
async def mark_partner_notification_read(
    notification_id: str,
    workspace_id: UUID | None = Query(None),
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerNotificationReadStateResponse:
    _require_partner_realm(current_realm)
    access = await _resolve_partner_session_workspace_access(
        current_user=current_user,
        db=db,
        workspace_id=workspace_id,
    )
    items = await _build_partner_notification_feed(
        access=access,
        current_user=current_user,
        db=db,
        include_archived=True,
    )
    target = next((item for item in items if item.id == notification_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner notification not found")

    state = await PartnerNotificationReadStateRepository(db).upsert_read_state(
        partner_account_id=access.workspace.id,
        admin_user_id=current_user.id,
        notification_key=notification_id,
        read_at=datetime.now(UTC),
    )
    await db.commit()
    track_partner_operation(operation="mark_partner_notification_read")
    observe_partner_notification_state_change(
        surface=PARTNER_PORTAL_SURFACE,
        notification_type=target.kind,
        action="read",
        result="success",
    )
    log_partner_runtime_event(
        "partner_notification.marked_read",
        surface=PARTNER_PORTAL_SURFACE,
        route_group="notifications",
        notification_type=target.kind,
        workspace_status=access.workspace.status,
        source_kind=target.source_kind,
        source_event_kind=target.source_event_kind,
        result="success",
    )
    return PartnerNotificationReadStateResponse(
        notification_id=notification_id,
        unread=False,
        archived=state.archived_at is not None,
        read_at=_normalize_utc(state.read_at),
        archived_at=_normalize_utc(state.archived_at) if state.archived_at is not None else None,
    )


@router.post(
    "/partner-notifications/{notification_id}/archive",
    response_model=PartnerNotificationReadStateResponse,
)
async def archive_partner_notification(
    notification_id: str,
    workspace_id: UUID | None = Query(None),
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerNotificationReadStateResponse:
    _require_partner_realm(current_realm)
    access = await _resolve_partner_session_workspace_access(
        current_user=current_user,
        db=db,
        workspace_id=workspace_id,
    )
    items = await _build_partner_notification_feed(
        access=access,
        current_user=current_user,
        db=db,
        include_archived=True,
    )
    target = next((item for item in items if item.id == notification_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner notification not found")

    state = await PartnerNotificationReadStateRepository(db).upsert_read_state(
        partner_account_id=access.workspace.id,
        admin_user_id=current_user.id,
        notification_key=notification_id,
        read_at=datetime.now(UTC),
        archived_at=datetime.now(UTC),
    )
    await db.commit()
    track_partner_operation(operation="archive_partner_notification")
    observe_partner_notification_state_change(
        surface=PARTNER_PORTAL_SURFACE,
        notification_type=target.kind,
        action="archive",
        result="success",
    )
    log_partner_runtime_event(
        "partner_notification.archived",
        surface=PARTNER_PORTAL_SURFACE,
        route_group="notifications",
        notification_type=target.kind,
        workspace_status=access.workspace.status,
        source_kind=target.source_kind,
        source_event_kind=target.source_event_kind,
        result="success",
    )
    return PartnerNotificationReadStateResponse(
        notification_id=notification_id,
        unread=False,
        archived=True,
        read_at=_normalize_utc(state.read_at),
        archived_at=_normalize_utc(state.archived_at) if state.archived_at is not None else None,
    )


@router.get(
    "/partner-notifications/preferences",
    response_model=PartnerNotificationPreferencesResponse,
)
async def get_partner_notification_preferences(
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
) -> PartnerNotificationPreferencesResponse:
    _require_partner_realm(current_realm)
    track_partner_operation(operation="get_partner_notification_preferences")
    return _serialize_partner_notification_preferences(current_user)


@router.patch(
    "/partner-notifications/preferences",
    response_model=PartnerNotificationPreferencesResponse,
)
async def update_partner_notification_preferences(
    body: PartnerNotificationPreferencesUpdateRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerNotificationPreferencesResponse:
    _require_partner_realm(current_realm)
    updates = body.model_dump(exclude_unset=True)
    current_user.notification_prefs = {
        **_build_workspace_notification_preferences(current_user),
        **updates,
    }
    updated_user = await AdminUserRepository(db).update(current_user)
    await db.commit()
    await db.refresh(updated_user)
    track_partner_operation(operation="update_partner_notification_preferences")
    return _serialize_partner_notification_preferences(updated_user)


@router.get(
    "/partner-application-drafts/current",
    response_model=PartnerApplicationDraftDetailResponse,
)
async def get_current_partner_application_draft(
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerApplicationDraftDetailResponse:
    _require_partner_realm(current_realm)
    workflow = PartnerApplicationWorkflowUseCase(db)
    draft = await workflow.get_current_draft(applicant_admin_user_id=current_user.id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner application draft not found")
    workspace = await PartnerAccountRepository(db).get_account_by_id(draft.partner_account_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner workspace not found")
    access = await resolve_partner_workspace_access(
        workspace_id=workspace.id,
        current_user=current_user,
        db=db,
    )
    track_partner_operation(operation="get_current_partner_application_draft")
    return await _build_partner_application_detail_response(
        draft=draft,
        workspace=workspace,
        access=access,
        db=db,
    )


@router.post(
    "/partner-application-drafts",
    response_model=PartnerApplicationDraftDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_partner_application_draft(
    body: UpsertPartnerApplicationDraftRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerApplicationDraftDetailResponse:
    _require_partner_realm(current_realm)
    workflow = PartnerApplicationWorkflowUseCase(db)
    draft = await workflow.create_draft(
        applicant_admin_user=current_user,
        payload=body.draft_payload,
    )
    if body.draft_payload:
        draft = await workflow.update_draft(
            draft_id=draft.id,
            applicant_admin_user_id=current_user.id,
            patch_payload=body.draft_payload,
            review_ready=body.review_ready,
        )
    workspace = await PartnerAccountRepository(db).get_account_by_id(draft.partner_account_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner workspace not found")
    access = await resolve_partner_workspace_access(
        workspace_id=workspace.id,
        current_user=current_user,
        db=db,
    )
    track_partner_operation(operation="create_partner_application_draft")
    return await _build_partner_application_detail_response(
        draft=draft,
        workspace=workspace,
        access=access,
        db=db,
    )


@router.patch(
    "/partner-application-drafts/{draft_id}",
    response_model=PartnerApplicationDraftDetailResponse,
)
async def update_partner_application_draft(
    draft_id: UUID,
    body: UpsertPartnerApplicationDraftRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerApplicationDraftDetailResponse:
    _require_partner_realm(current_realm)
    workflow = PartnerApplicationWorkflowUseCase(db)
    try:
        draft = await workflow.update_draft(
            draft_id=draft_id,
            applicant_admin_user_id=current_user.id,
            patch_payload=body.draft_payload,
            review_ready=body.review_ready,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    workspace = await PartnerAccountRepository(db).get_account_by_id(draft.partner_account_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner workspace not found")
    access = await resolve_partner_workspace_access(
        workspace_id=workspace.id,
        current_user=current_user,
        db=db,
    )
    track_partner_operation(operation="update_partner_application_draft")
    return await _build_partner_application_detail_response(
        draft=draft,
        workspace=workspace,
        access=access,
        db=db,
    )


@router.post(
    "/partner-application-drafts/{draft_id}/attachments",
    response_model=PartnerApplicationAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_partner_application_attachment(
    draft_id: UUID,
    body: CreatePartnerApplicationAttachmentRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerApplicationAttachmentResponse:
    _require_partner_realm(current_realm)
    workflow = PartnerApplicationWorkflowUseCase(db)
    try:
        attachment = await workflow.create_attachment(
            draft_id=draft_id,
            applicant_admin_user_id=current_user.id,
            attachment_type=body.attachment_type,
            storage_key=body.storage_key,
            file_name=body.file_name,
            attachment_metadata=body.attachment_metadata,
            lane_application_id=body.lane_application_id,
            review_request_id=body.review_request_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    track_partner_operation(operation="create_partner_application_attachment")
    return _serialize_partner_application_attachment_response(attachment)


@router.post(
    "/partner-application-drafts/{draft_id}/submit",
    response_model=PartnerApplicationDraftDetailResponse,
)
async def submit_partner_application_draft(
    draft_id: UUID,
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerApplicationDraftDetailResponse:
    _require_partner_realm(current_realm)
    workflow = PartnerApplicationWorkflowUseCase(db)
    try:
        draft = await workflow.submit_draft(
            draft_id=draft_id,
            applicant_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    workspace = await PartnerAccountRepository(db).get_account_by_id(draft.partner_account_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner workspace not found")
    access = await resolve_partner_workspace_access(
        workspace_id=workspace.id,
        current_user=current_user,
        db=db,
    )
    track_partner_operation(operation="submit_partner_application_draft")
    return await _build_partner_application_detail_response(
        draft=draft,
        workspace=workspace,
        access=access,
        db=db,
    )


@router.post(
    "/partner-application-drafts/{draft_id}/withdraw",
    response_model=PartnerApplicationDraftDetailResponse,
)
async def withdraw_partner_application_draft(
    draft_id: UUID,
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerApplicationDraftDetailResponse:
    _require_partner_realm(current_realm)
    workflow = PartnerApplicationWorkflowUseCase(db)
    try:
        draft = await workflow.withdraw_draft(
            draft_id=draft_id,
            applicant_admin_user_id=current_user.id,
            applicant_is_email_verified=current_user.is_email_verified,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    workspace = await PartnerAccountRepository(db).get_account_by_id(draft.partner_account_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner workspace not found")
    access = await resolve_partner_workspace_access(
        workspace_id=workspace.id,
        current_user=current_user,
        db=db,
    )
    track_partner_operation(operation="withdraw_partner_application_draft")
    return await _build_partner_application_detail_response(
        draft=draft,
        workspace=workspace,
        access=access,
        db=db,
    )


@router.post(
    "/partner-application-drafts/{draft_id}/resubmit",
    response_model=PartnerApplicationDraftDetailResponse,
)
async def resubmit_partner_application_draft(
    draft_id: UUID,
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerApplicationDraftDetailResponse:
    _require_partner_realm(current_realm)
    workflow = PartnerApplicationWorkflowUseCase(db)
    try:
        draft = await workflow.submit_draft(
            draft_id=draft_id,
            applicant_admin_user_id=current_user.id,
            is_resubmission=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    workspace = await PartnerAccountRepository(db).get_account_by_id(draft.partner_account_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner workspace not found")
    access = await resolve_partner_workspace_access(
        workspace_id=workspace.id,
        current_user=current_user,
        db=db,
    )
    track_partner_operation(operation="resubmit_partner_application_draft")
    return await _build_partner_application_detail_response(
        draft=draft,
        workspace=workspace,
        access=access,
        db=db,
    )


@router.get(
    "/partner-workspaces/{workspace_id}/lane-applications",
    response_model=list[PartnerLaneApplicationResponse],
)
async def list_partner_workspace_lane_applications(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.WORKSPACE_READ)),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerLaneApplicationResponse]:
    _require_partner_realm(current_realm)
    track_partner_operation(operation="list_partner_workspace_lane_applications")
    items = await PartnerApplicationWorkflowUseCase(db).list_lane_applications(
        partner_account_id=access.workspace.id,
    )
    return [_serialize_partner_lane_application_response(item) for item in items]


@router.post(
    "/partner-workspaces/{workspace_id}/lane-applications",
    response_model=PartnerLaneApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_partner_workspace_lane_application(
    workspace_id: UUID,
    body: CreatePartnerLaneApplicationRequest,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.OPERATIONS_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerLaneApplicationResponse:
    _require_partner_realm(current_realm)
    workflow = PartnerApplicationWorkflowUseCase(db)
    draft = await workflow.get_draft_by_partner_account(partner_account_id=access.workspace.id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner application draft not found")
    try:
        item = await workflow.create_lane_application(
            draft_id=draft.id,
            applicant_admin_user_id=current_user.id,
            lane_key=body.lane_key,
            payload=body.application_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    track_partner_operation(operation="create_partner_workspace_lane_application")
    return _serialize_partner_lane_application_response(item)


@router.patch(
    "/partner-workspaces/{workspace_id}/lane-applications/{lane_application_id}",
    response_model=PartnerLaneApplicationResponse,
)
async def update_partner_workspace_lane_application(
    workspace_id: UUID,
    lane_application_id: UUID,
    body: UpdatePartnerLaneApplicationRequest,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.OPERATIONS_WRITE)),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerLaneApplicationResponse:
    _require_partner_realm(current_realm)
    try:
        item = await PartnerApplicationWorkflowUseCase(db).update_lane_application(
            lane_application_id=lane_application_id,
            partner_account_id=access.workspace.id,
            payload=body.application_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    track_partner_operation(operation="update_partner_workspace_lane_application")
    return _serialize_partner_lane_application_response(item)


@router.post(
    "/partner-workspaces/{workspace_id}/lane-applications/{lane_application_id}/submit",
    response_model=PartnerLaneApplicationResponse,
)
async def submit_partner_workspace_lane_application(
    workspace_id: UUID,
    lane_application_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.OPERATIONS_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerLaneApplicationResponse:
    _require_partner_realm(current_realm)
    try:
        item = await PartnerApplicationWorkflowUseCase(db).submit_lane_application(
            lane_application_id=lane_application_id,
            partner_account_id=access.workspace.id,
            actor_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    track_partner_operation(operation="submit_partner_workspace_lane_application")
    return _serialize_partner_lane_application_response(item)


@router.get(
    "/partner-workspaces/{workspace_id}",
    response_model=PartnerWorkspaceResponse,
)
async def get_partner_workspace(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.WORKSPACE_READ)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceResponse:
    payload = await GetPartnerWorkspaceUseCase(
        PartnerAccountRepository(db),
        PartnerRepository(db),
    ).execute(workspace_id)
    track_partner_operation(operation="get_workspace")
    return _serialize_workspace_response(payload, access=access)


@router.get(
    "/partner-workspaces/{workspace_id}/organization-profile",
    response_model=PartnerWorkspaceOrganizationProfileResponse,
)
async def get_partner_workspace_organization_profile(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.WORKSPACE_READ)),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceOrganizationProfileResponse:
    profile_repo = PartnerWorkspaceProfileRepository(db)
    profile = await profile_repo.get_or_create(access.workspace.id)
    draft = await PartnerApplicationWorkflowUseCase(db).get_draft_by_partner_account(
        partner_account_id=access.workspace.id,
    )
    programs = await BuildPartnerWorkspaceProgramsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        workspace_status=access.workspace.status,
        workspace_label=access.workspace.display_name,
    )
    primary_lane = (
        str((draft.draft_payload or {}).get("primary_lane") or "") or None if draft is not None else None
    ) or programs.primary_lane_key
    track_partner_operation(operation="get_workspace_organization_profile")
    return _serialize_workspace_organization_profile_response(
        workspace=access.workspace,
        profile=profile,
        primary_lane=primary_lane,
        current_user=current_user,
    )


@router.patch(
    "/partner-workspaces/{workspace_id}/organization-profile",
    response_model=PartnerWorkspaceOrganizationProfileResponse,
)
async def update_partner_workspace_organization_profile(
    workspace_id: UUID,
    body: UpdatePartnerWorkspaceOrganizationProfileRequest,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.OPERATIONS_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceOrganizationProfileResponse:
    updates = body.model_dump(exclude_unset=True)
    profile_repo = PartnerWorkspaceProfileRepository(db)
    profile = await profile_repo.get_or_create(access.workspace.id)

    workspace_name = updates.pop("workspace_name", None)
    if workspace_name:
        access.workspace.display_name = workspace_name
        await PartnerAccountRepository(db).update_account(access.workspace)

    for field, value in updates.items():
        if hasattr(profile, field):
            setattr(profile, field, value)

    await profile_repo.update(profile)

    draft = await PartnerApplicationWorkflowUseCase(db).get_draft_by_partner_account(
        partner_account_id=access.workspace.id,
    )
    programs = await BuildPartnerWorkspaceProgramsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        workspace_status=access.workspace.status,
        workspace_label=access.workspace.display_name,
    )
    primary_lane = (
        str((draft.draft_payload or {}).get("primary_lane") or "") or None if draft is not None else None
    ) or programs.primary_lane_key
    track_partner_operation(operation="update_workspace_organization_profile")
    return _serialize_workspace_organization_profile_response(
        workspace=access.workspace,
        profile=profile,
        primary_lane=primary_lane,
        current_user=current_user,
    )


@router.get(
    "/partner-workspaces/{workspace_id}/members",
    response_model=list[PartnerWorkspaceMemberResponse],
)
async def list_partner_workspace_members(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.MEMBERSHIP_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceMemberResponse]:
    payload = await GetPartnerWorkspaceUseCase(
        PartnerAccountRepository(db),
        PartnerRepository(db),
    ).execute(access.workspace.id)
    track_partner_operation(operation="list_workspace_members")
    return _serialize_workspace_response(payload, access=access).members


@router.get(
    "/partner-workspaces/{workspace_id}/roles",
    response_model=list[PartnerWorkspaceRoleResponse],
)
async def list_partner_workspace_roles(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.MEMBERSHIP_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceRoleResponse]:
    roles = await PartnerAccountRepository(db).list_roles()
    track_partner_operation(operation="list_workspace_roles")
    return [
        PartnerWorkspaceRoleResponse(
            id=item.id,
            role_key=item.role_key,
            display_name=item.display_name,
            description=item.description,
            permission_keys=list(item.permission_keys),
            is_system=item.is_system,
        )
        for item in roles
    ]


@router.patch(
    "/partner-workspaces/{workspace_id}/members/{member_id}",
    response_model=PartnerWorkspaceMemberResponse,
)
async def update_partner_workspace_member(
    workspace_id: UUID,
    member_id: UUID,
    body: UpdatePartnerWorkspaceMemberRequest,
    request: Request,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.MEMBERSHIP_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    current_realm: RealmResolution = Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> PartnerWorkspaceMemberResponse:
    if body.role_key is None and body.membership_status is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one member update field is required",
        )

    await _enforce_partner_passkey_fresh_auth(
        request=request,
        redis_client=redis_client,
        current_user=current_user,
        current_realm=current_realm,
        action=f"partner.member.update:{access.workspace.id}:{member_id}",
    )

    repo = PartnerAccountRepository(db)
    membership = await repo.get_membership_by_id(member_id)
    if membership is None or membership.partner_account_id != access.workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member not found")

    current_role = await repo.get_role_by_id(membership.role_id)
    if current_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Partner workspace role is missing",
        )

    if body.role_key is not None:
        role = await repo.get_role_by_key(body.role_key)
        if role is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Partner workspace role not found")
    else:
        role = current_role

    requested_membership_status = body.membership_status or membership.membership_status
    if body.membership_status is not None:
        if body.membership_status not in _WORKSPACE_MEMBER_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid workspace member status")

    await _enforce_workspace_owner_role_update_guard(
        repo,
        access=access,
        membership=membership,
        current_role_key=current_role.role_key,
        requested_role_key=role.role_key,
        requested_membership_status=requested_membership_status,
    )

    membership.role_id = role.id
    if body.membership_status is not None:
        membership.membership_status = body.membership_status

    membership = await repo.update_membership(membership)
    operator = await AdminUserRepository(db).get_by_id(membership.admin_user_id)
    track_partner_operation(operation="update_workspace_member")
    return _serialize_workspace_member(membership=membership, role=role, operator=operator)


@router.get(
    "/partner-workspaces/{workspace_id}/legal-documents",
    response_model=list[PartnerWorkspaceLegalDocumentResponse],
)
async def list_partner_workspace_legal_documents(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.WORKSPACE_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceLegalDocumentResponse]:
    workspace_payload = await GetPartnerWorkspaceUseCase(
        PartnerAccountRepository(db),
        PartnerRepository(db),
    ).execute(access.workspace.id)
    role_by_admin_user_id = _build_workspace_role_key_by_admin_user_id(workspace_payload)
    programs = await BuildPartnerWorkspaceProgramsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        workspace_status=access.workspace.status,
        workspace_label=access.workspace.display_name,
    )
    acceptances = await PartnerWorkspaceLegalAcceptanceRepository(db).list_for_workspace(
        access.workspace.id,
    )
    track_partner_operation(operation="list_workspace_legal_documents")
    return _serialize_workspace_legal_documents(
        workspace=access.workspace,
        programs=programs,
        role_by_admin_user_id=role_by_admin_user_id,
        acceptances=acceptances,
    )


@router.post(
    "/partner-workspaces/{workspace_id}/legal-documents/{document_kind}/accept",
    response_model=PartnerWorkspaceLegalDocumentResponse,
)
async def accept_partner_workspace_legal_document(
    workspace_id: UUID,
    document_kind: str,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.OPERATIONS_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceLegalDocumentResponse:
    if not _can_accept_workspace_legal_document(access):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace legal acceptance is restricted")

    workspace_payload = await GetPartnerWorkspaceUseCase(
        PartnerAccountRepository(db),
        PartnerRepository(db),
    ).execute(access.workspace.id)
    role_by_admin_user_id = _build_workspace_role_key_by_admin_user_id(workspace_payload)
    programs = await BuildPartnerWorkspaceProgramsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        workspace_status=access.workspace.status,
        workspace_label=access.workspace.display_name,
    )
    repo = PartnerWorkspaceLegalAcceptanceRepository(db)
    legal_documents = _serialize_workspace_legal_documents(
        workspace=access.workspace,
        programs=programs,
        role_by_admin_user_id=role_by_admin_user_id,
        acceptances=await repo.list_for_workspace(access.workspace.id),
    )
    target = next((item for item in legal_documents if item.kind == document_kind), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace legal document not found")
    if target.status == "read_only":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workspace legal document is not yet accepting partner acknowledgement",
        )

    existing = await repo.get_for_document(
        partner_account_id=access.workspace.id,
        document_kind=target.kind,
        document_version=target.version,
    )
    if existing is None:
        await repo.create(
            PartnerWorkspaceLegalAcceptanceModel(
                partner_account_id=access.workspace.id,
                document_kind=target.kind,
                document_version=target.version,
                accepted_by_admin_user_id=current_user.id,
            )
        )

    refreshed = _serialize_workspace_legal_documents(
        workspace=access.workspace,
        programs=programs,
        role_by_admin_user_id=role_by_admin_user_id,
        acceptances=await repo.list_for_workspace(access.workspace.id),
    )
    resolved = next((item for item in refreshed if item.kind == document_kind), None)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Accepted workspace legal document could not be reloaded",
        )
    track_partner_operation(operation="accept_workspace_legal_document")
    return resolved


@router.get(
    "/partner-workspaces/{workspace_id}/settings",
    response_model=PartnerWorkspaceSettingsResponse,
)
async def get_partner_workspace_settings(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.WORKSPACE_READ)),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceSettingsResponse:
    profile = await PartnerWorkspaceProfileRepository(db).get_or_create(access.workspace.id)
    track_partner_operation(operation="get_workspace_settings")
    return _serialize_workspace_settings_response(
        workspace=access.workspace,
        profile=profile,
        current_user=current_user,
        access=access,
    )


@router.patch(
    "/partner-workspaces/{workspace_id}/settings",
    response_model=PartnerWorkspaceSettingsResponse,
)
async def update_partner_workspace_settings(
    workspace_id: UUID,
    body: UpdatePartnerWorkspaceSettingsRequest,
    request: Request,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.OPERATIONS_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> PartnerWorkspaceSettingsResponse:
    updates = body.model_dump(exclude_unset=True)
    await _enforce_partner_passkey_fresh_auth(
        request=request,
        redis_client=redis_client,
        current_user=current_user,
        current_realm=current_realm,
        action=f"partner.settings.security.update:{access.workspace.id}",
    )
    profile_repo = PartnerWorkspaceProfileRepository(db)
    profile = await profile_repo.get_or_create(access.workspace.id)

    if "preferred_language" in updates:
        current_user.language = updates.pop("preferred_language") or current_user.language

    prefs = _build_workspace_notification_preferences(current_user)
    if "workspace_security_alerts" in updates:
        prefs["email_security"] = bool(updates.pop("workspace_security_alerts"))
    if "payout_status_emails" in updates:
        prefs["partner_payout_status_emails"] = bool(updates.pop("payout_status_emails"))
    if "product_announcements" in updates:
        prefs["email_marketing"] = bool(updates.pop("product_announcements"))
    current_user.notification_prefs = prefs

    field_map = {
        "preferred_currency": "preferred_currency",
        "reviewed_active_sessions": "reviewed_active_sessions",
    }
    for request_field, model_field in field_map.items():
        if request_field in updates:
            setattr(profile, model_field, updates[request_field])

    await AdminUserRepository(db).update(current_user)
    await profile_repo.update(profile)
    track_partner_operation(operation="update_workspace_settings")
    return _serialize_workspace_settings_response(
        workspace=access.workspace,
        profile=profile,
        current_user=current_user,
        access=access,
    )


@router.get(
    "/partner-workspaces/{workspace_id}/programs",
    response_model=PartnerWorkspaceProgramsResponse,
)
async def get_partner_workspace_programs(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.WORKSPACE_READ)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceProgramsResponse:
    programs = await BuildPartnerWorkspaceProgramsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        workspace_status=access.workspace.status,
        workspace_label=access.workspace.display_name,
    )
    track_partner_operation(operation="get_workspace_programs")
    return PartnerWorkspaceProgramsResponse(
        canonical_source=programs.canonical_source,
        primary_lane_key=programs.primary_lane_key,
        lane_memberships=[_serialize_workspace_program_lane(item) for item in programs.lane_memberships],
        readiness_items=[_serialize_workspace_program_readiness_item(item) for item in programs.readiness_items],
        updated_at=_normalize_utc(programs.updated_at),
    )


@router.get(
    "/partner-workspaces/{workspace_id}/codes",
    response_model=list[PartnerWorkspaceCodeResponse],
)
async def list_partner_workspace_codes(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.CODES_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceCodeResponse]:
    codes = await PartnerRepository(db).get_codes_by_account(access.workspace.id)
    track_partner_operation(operation="list_workspace_codes")
    return [_serialize_workspace_code(code_model) for code_model in codes]


@router.post(
    "/partner-workspaces/{workspace_id}/codes",
    response_model=PartnerWorkspaceCodeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_partner_workspace_code(
    workspace_id: UUID,
    body: CreatePartnerWorkspaceCodeRequest,
    request: Request,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.CODES_WRITE)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceCodeResponse:
    repo = PartnerRepository(db)
    _assert_no_sensitive_partner_code_fields(
        body.model_fields_set,
        operation="create",
        allow_revenue_terms=_can_manage_partner_code_revenue_terms(access),
    )
    idempotency_key = (request.headers.get("Idempotency-Key") or "").strip()
    idempotency_scope = f"partner-workspace:{access.workspace.id}:codes:create"
    request_hash = _idempotency_request_hash(body.model_dump(mode="json", exclude_unset=True))
    if idempotency_key:
        existing_record = await _get_idempotency_record(
            db,
            scope=idempotency_scope,
            idempotency_key=idempotency_key,
        )
        if existing_record is not None:
            if existing_record.request_hash and existing_record.request_hash != request_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key was already used with a different request payload",
                )
            if existing_record.resource_id is not None:
                existing_code = await repo.get_code_by_id(existing_record.resource_id)
                if existing_code is not None and existing_code.partner_account_id == access.workspace.id:
                    track_partner_operation(operation="create_workspace_code:idempotent_replay")
                    return _serialize_workspace_code(existing_code)
            if existing_record.response_payload:
                track_partner_operation(operation="create_workspace_code:idempotent_replay")
                return PartnerWorkspaceCodeResponse(**existing_record.response_payload)

    sub_id_schema = dict(body.sub_id_schema or {})
    created = None
    config_service = ConfigService(SystemConfigRepository(db))
    max_markup = await config_service.get_partner_max_markup_pct()
    if body.markup_pct > max_markup:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Markup {body.markup_pct}% exceeds maximum {max_markup}%",
        )
    for attempt in range(3):
        code = await _resolve_unique_partner_code(repo, body.code)
        public_slug = await _allocate_public_slug(repo)
        model = PartnerCodeModel(
            partner_account_id=access.workspace.id,
            partner_user_id=access.workspace.legacy_owner_user_id,
            code=code,
            code_normalized=code,
            public_slug=public_slug,
            public_token_hash=hash_partner_attribution_token(public_slug),
            markup_pct=body.markup_pct,
            is_active=True,
            lifecycle_status="active",
            approval_status="approved",
            owner_type=_validated_owner_type(body.owner_type),
            lane_key=body.lane_key.strip(),
            attribution_model=body.attribution_model.strip(),
            attribution_window_seconds=body.attribution_window_seconds,
            destination_path=_normalize_destination_path(body.destination_path),
            allowed_channels=_clean_string_list(body.allowed_channels, default=["content", "telegram", "storefront"]),
            allowed_storefront_ids=_clean_string_list(body.allowed_storefront_ids, default=["*"]),
            allowed_geographies=_clean_string_list(body.allowed_geographies, default=["*"]),
            sub_id_schema=sub_id_schema,
            expires_at=body.expires_at,
        )
        try:
            created = await repo.create_code(model)
            commission_contract = build_commission_contract_model(
                code_model=created,
                commission_pct=_resolve_base_commission_pct(await config_service.get_partner_tiers()),
                payout_hold_days=await config_service.get_partner_payout_hold_days(owner_type=created.owner_type),
                source="partner_workspace_code_create",
            )
            await repo.attach_commission_contract_to_code(created, commission_contract)
            await _ensure_default_code_link(db, created)
            break
        except IntegrityError as exc:
            await db.rollback()
            if body.code or attempt == 2:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Partner code or public slug already exists",
                ) from exc
    if created is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not create partner code")
    await _append_code_event(
        db,
        code_model=created,
        event_type="code.created",
        previous_status=None,
        next_status=created.lifecycle_status,
        reason="partner_workspace_code_create",
        payload={"idempotency_key": idempotency_key or None},
    )
    serialized = _serialize_workspace_code(created)
    if idempotency_key:
        db.add(
            ApiIdempotencyRecordModel(
                scope=idempotency_scope,
                idempotency_key=idempotency_key,
                resource_type="partner_code",
                resource_id=created.id,
                request_hash=request_hash,
                response_payload=serialized.model_dump(mode="json"),
            )
        )
        await db.flush()
    await db.commit()
    await db.refresh(created)
    track_partner_operation(operation="create_workspace_code")
    return _serialize_workspace_code(created)


@router.patch(
    "/partner-workspaces/{workspace_id}/codes/{code_id}",
    response_model=PartnerWorkspaceCodeResponse,
)
async def update_partner_workspace_code(
    workspace_id: UUID,
    code_id: UUID,
    body: UpdatePartnerWorkspaceCodeRequest,
    request: Request,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.CODES_WRITE)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceCodeResponse:
    code_model = await _get_workspace_code_or_404(db, access.workspace.id, code_id)
    _assert_code_version_matches(request, code_model)
    _assert_no_sensitive_partner_code_fields(
        body.model_fields_set,
        operation="update",
        allow_revenue_terms=_can_manage_partner_code_revenue_terms(access),
    )
    should_increment_version = True
    if body.markup_pct is not None:
        config_service = ConfigService(SystemConfigRepository(db))
        max_markup = await config_service.get_partner_max_markup_pct()
        if body.markup_pct > max_markup:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Markup {body.markup_pct}% exceeds maximum {max_markup}%",
            )
        code_model.markup_pct = Decimal(str(body.markup_pct))
        code_model.version = int(code_model.version or 1) + 1
        should_increment_version = False
        commission_contract = build_commission_contract_model(
            code_model=code_model,
            commission_pct=_resolve_base_commission_pct(await config_service.get_partner_tiers()),
            payout_hold_days=await config_service.get_partner_payout_hold_days(owner_type=code_model.owner_type),
            source="partner_workspace_code_markup_update",
            contract_id=uuid4(),
        )
        await PartnerRepository(db).attach_commission_contract_to_code(code_model, commission_contract)
    if "destination_path" in body.model_fields_set:
        code_model.destination_path = _normalize_destination_path(body.destination_path)
    if body.sub_id_schema is not None:
        code_model.sub_id_schema = dict(body.sub_id_schema)
    if "expires_at" in body.model_fields_set:
        code_model.expires_at = body.expires_at
    if should_increment_version:
        code_model.version = int(code_model.version or 1) + 1
    await _append_code_event(
        db,
        code_model=code_model,
        event_type="code.updated",
        previous_status=code_model.lifecycle_status,
        next_status=code_model.lifecycle_status,
        reason="partner_workspace_code_update",
        payload={"fields": sorted(body.model_fields_set)},
    )
    updated = await PartnerRepository(db).update_code(code_model)
    await db.commit()
    await db.refresh(updated)
    track_partner_operation(operation="update_workspace_code")
    return _serialize_workspace_code(updated)


@router.post(
    "/partner-workspaces/{workspace_id}/codes/{code_id}/activate",
    response_model=PartnerWorkspaceCodeResponse,
)
async def activate_partner_workspace_code(
    workspace_id: UUID,
    code_id: UUID,
    body: PartnerWorkspaceCodeLifecycleRequest,
    request: Request,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.CODES_WRITE)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceCodeResponse:
    return await _change_workspace_code_lifecycle(
        db=db,
        request=request,
        workspace_id=access.workspace.id,
        code_id=code_id,
        lifecycle_status="active",
        reason=body.reason,
        operation="activate_workspace_code",
    )


@router.post(
    "/partner-workspaces/{workspace_id}/codes/{code_id}/pause",
    response_model=PartnerWorkspaceCodeResponse,
)
async def pause_partner_workspace_code(
    workspace_id: UUID,
    code_id: UUID,
    body: PartnerWorkspaceCodeLifecycleRequest,
    request: Request,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.CODES_WRITE)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceCodeResponse:
    return await _change_workspace_code_lifecycle(
        db=db,
        request=request,
        workspace_id=access.workspace.id,
        code_id=code_id,
        lifecycle_status="paused",
        reason=body.reason,
        operation="pause_workspace_code",
    )


@router.post(
    "/partner-workspaces/{workspace_id}/codes/{code_id}/revoke",
    response_model=PartnerWorkspaceCodeResponse,
)
async def revoke_partner_workspace_code(
    workspace_id: UUID,
    code_id: UUID,
    body: PartnerWorkspaceCodeLifecycleRequest,
    request: Request,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.CODES_WRITE)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceCodeResponse:
    if not body.reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="reason is required for revoke")
    return await _change_workspace_code_lifecycle(
        db=db,
        request=request,
        workspace_id=access.workspace.id,
        code_id=code_id,
        lifecycle_status="revoked",
        reason=body.reason,
        operation="revoke_workspace_code",
    )


@router.post(
    "/partner-workspaces/{workspace_id}/codes/{code_id}/archive",
    response_model=PartnerWorkspaceCodeResponse,
)
async def archive_partner_workspace_code(
    workspace_id: UUID,
    code_id: UUID,
    body: PartnerWorkspaceCodeLifecycleRequest,
    request: Request,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.CODES_WRITE)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceCodeResponse:
    if not body.reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="reason is required for archive")
    return await _change_workspace_code_lifecycle(
        db=db,
        request=request,
        workspace_id=access.workspace.id,
        code_id=code_id,
        lifecycle_status="archived",
        reason=body.reason,
        operation="archive_workspace_code",
    )


@router.post(
    "/partner-workspaces/{workspace_id}/codes/{code_id}/links",
    response_model=PartnerWorkspaceCodeLinkResponse,
)
async def create_partner_workspace_code_link(
    workspace_id: UUID,
    code_id: UUID,
    body: PartnerWorkspaceCodeLinkRequest,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.CODES_WRITE)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceCodeLinkResponse:
    code_model = await _get_workspace_code_or_404(db, access.workspace.id, code_id)
    link = await _create_code_link(
        db,
        code_model=code_model,
        destination_key=body.destination_key,
        destination_path=body.destination_path,
        link_kind=body.link_kind,
        locale=body.locale,
        sale_channel=body.sale_channel,
        campaign_params=body.campaign_params,
        sub_ids=body.sub_ids,
        active_from=body.active_from,
        expires_at=body.expires_at,
    )
    await db.commit()
    await db.refresh(link)
    track_partner_operation(operation="create_workspace_code_link")
    return _serialize_code_link(link)


@router.post(
    "/partner-workspaces/{workspace_id}/codes/{code_id}/qr",
    response_model=PartnerWorkspaceCodeQrResponse,
)
async def create_partner_workspace_code_qr(
    workspace_id: UUID,
    code_id: UUID,
    body: PartnerWorkspaceCodeQrRequest,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.CODES_WRITE)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceCodeQrResponse:
    code_model = await _get_workspace_code_or_404(db, access.workspace.id, code_id)
    if body.link_id is not None:
        link = await PartnerRepository(db).get_code_link_by_id(body.link_id)
        if link is None or link.partner_code_id != code_model.id or link.partner_account_id != access.workspace.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner code link not found")
    else:
        link = await _create_code_link(
            db,
            code_model=code_model,
            destination_key=body.destination_key,
            destination_path=body.destination_path,
            link_kind="qr",
            locale=None,
            sale_channel=None,
            campaign_params={},
            sub_ids={},
            active_from=None,
            expires_at=None,
        )
        await db.commit()
        await db.refresh(link)
    share_url = build_share_url(link.public_slug)
    track_partner_operation(operation="create_workspace_code_qr")
    return PartnerWorkspaceCodeQrResponse(
        link_id=link.id,
        code_id=code_model.id,
        public_slug=link.public_slug,
        share_url=share_url,
        qr_svg=_build_code_qr_svg(share_url, body.size),
    )


@router.get(
    "/partner-workspaces/{workspace_id}/commercial-capabilities",
    response_model=PartnerWorkspaceCommercialCapabilitiesResponse,
)
async def get_partner_workspace_commercial_capabilities(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.CODES_READ)),
) -> PartnerWorkspaceCommercialCapabilitiesResponse:
    permission_keys = access.permission_keys
    actions = ["list_codes", "create_link", "download_qr"]
    if PartnerPermission.CODES_WRITE.value in permission_keys:
        actions.extend(["create_code", "update_code", "activate", "pause", "revoke", "archive"])
    track_partner_operation(operation="workspace_commercial_capabilities")
    return PartnerWorkspaceCommercialCapabilitiesResponse(
        workspace_id=access.workspace.id,
        workspace_status=access.workspace.status,
        can_read_codes=PartnerPermission.CODES_READ.value in permission_keys,
        can_write_codes=PartnerPermission.CODES_WRITE.value in permission_keys,
        can_read_finance=PartnerPermission.PAYOUTS_READ.value in permission_keys,
        attribution_enabled=bool(settings.partner_attribution_enabled),
        default_owner_type="affiliate",
        supported_owner_types=["affiliate", "performance", "reseller"],
        supported_attribution_models=["first_eligible_touch", "last_eligible_touch"],
        available_actions=actions,
    )


@router.get(
    "/partner-workspaces/{workspace_id}/finance-summary",
    response_model=PartnerWorkspaceFinanceSummaryResponse,
)
async def get_partner_workspace_finance_summary(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.PAYOUTS_READ)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceFinanceSummaryResponse:
    summary = await GetPartnerFinanceSummaryUseCase(db).execute(partner_account_id=access.workspace.id)
    track_partner_operation(operation="workspace_finance_summary")
    return PartnerWorkspaceFinanceSummaryResponse(
        workspace_id=summary.workspace_id,
        generated_at=summary.generated_at,
        source_of_truth=summary.source_of_truth,
        currencies=[PartnerWorkspaceFinanceCurrencySummaryResponse(**item.__dict__) for item in summary.currencies],
    )


@router.get(
    "/partner-workspaces/{workspace_id}/campaign-assets",
    response_model=list[PartnerWorkspaceCampaignAssetResponse],
)
async def list_partner_workspace_campaign_assets(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.TRAFFIC_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceCampaignAssetResponse]:
    creative_approvals = await ListCreativeApprovalsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        limit=100,
        offset=0,
    )
    track_partner_operation(operation="list_workspace_campaign_assets")
    return _build_workspace_campaign_assets(creative_approvals=creative_approvals)


@router.get(
    "/partner-workspaces/{workspace_id}/reseller-voucher-batches",
    response_model=list[PartnerWorkspaceResellerVoucherBatchResponse],
)
async def list_partner_workspace_reseller_voucher_batches(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.CODES_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceResellerVoucherBatchResponse]:
    if not await _workspace_reseller_voucher_capability_enabled(access=access, db=db):
        track_partner_operation(operation="list_workspace_reseller_voucher_batches")
        return []

    repo = GrowthCodeRepository(db)
    codes = await repo.list_codes(
        code_type="gift",
        owner_partner_account_id=access.workspace.id,
        limit=500,
        offset=0,
    )
    batched_codes = [code for code in codes if code.batch_id is not None]
    if not batched_codes:
        track_partner_operation(operation="list_workspace_reseller_voucher_batches")
        return []

    code_ids = [code.id for code in batched_codes]
    policies_by_code_id = await repo.list_gift_policies_for_codes(code_ids)
    redemption_counts = await repo.count_redemptions_for_codes(code_ids)

    grouped: dict[UUID, list] = {}
    for code in batched_codes:
        if code.batch_id is None:
            continue
        grouped.setdefault(code.batch_id, []).append(code)

    items = [
        _build_reseller_voucher_batch_summary(
            batch_id=batch_id,
            codes=sorted(group_codes, key=lambda item: _normalize_utc(item.created_at)),
            policies_by_code_id=policies_by_code_id,
            redemption_counts=redemption_counts,
        )
        for batch_id, group_codes in grouped.items()
    ]
    items.sort(key=lambda item: item.updated_at, reverse=True)
    track_partner_operation(operation="list_workspace_reseller_voucher_batches")
    return items


@router.post(
    "/partner-workspaces/{workspace_id}/reseller-voucher-batches/request",
    response_model=RequestPartnerWorkspaceResellerVoucherBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_partner_workspace_reseller_voucher_batch(
    workspace_id: UUID,
    body: RequestPartnerWorkspaceResellerVoucherBatchRequest,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.CODES_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> RequestPartnerWorkspaceResellerVoucherBatchResponse:
    await _ensure_workspace_reseller_voucher_capability(access=access, db=db)
    result = await IssueGiftCodeUseCase(db).execute_batch(
        owner_partner_account_id=access.workspace.id,
        plan_id=body.plan_id,
        count=body.count,
        issuer_type="partner_workspace",
        issuance_type="partner_reseller_batch",
        recipient_hint=body.recipient_hint,
        gift_message=body.gift_message,
        issued_by_admin_id=current_user.id,
        reason_code="reseller_voucher_batch_request",
    )
    redemption_counts = {item.growth_code.id: 0 for item in result.items}
    policies_by_code_id = {item.growth_code.id: item.policy for item in result.items}
    batch = _build_reseller_voucher_batch_summary(
        batch_id=result.batch_id,
        codes=[item.growth_code for item in result.items],
        policies_by_code_id=policies_by_code_id,
        redemption_counts=redemption_counts,
    )
    track_partner_operation(operation="request_workspace_reseller_voucher_batch")
    return RequestPartnerWorkspaceResellerVoucherBatchResponse(
        batch=batch,
        issued_codes=[item.raw_code for item in result.items],
    )


@router.get(
    "/partner-workspaces/{workspace_id}/statements",
    response_model=list[PartnerStatementResponse],
)
async def list_partner_workspace_statements(
    workspace_id: UUID,
    statement_status: PartnerStatementStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.EARNINGS_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerStatementResponse]:
    items = await ListPartnerStatementsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        settlement_period_id=None,
        statement_status=statement_status.value if statement_status else None,
        limit=limit,
        offset=offset,
    )
    track_partner_operation(operation="list_workspace_statements")
    return [_serialize_partner_statement(item) for item in items]


@router.get(
    "/partner-workspaces/{workspace_id}/payout-accounts",
    response_model=list[PartnerWorkspacePayoutAccountResponse],
)
async def list_partner_workspace_payout_accounts(
    workspace_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.PAYOUTS_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspacePayoutAccountResponse]:
    items = await ListPartnerPayoutAccountsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        limit=limit,
        offset=offset,
    )
    track_partner_operation(operation="list_workspace_payout_accounts")
    return [_serialize_partner_workspace_payout_account(item) for item in items]


@router.post(
    "/partner-workspaces/{workspace_id}/payout-accounts",
    response_model=PartnerWorkspacePayoutAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_partner_workspace_payout_account(
    workspace_id: UUID,
    payload: CreatePartnerWorkspacePayoutAccountRequest,
    request: Request,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.PAYOUTS_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    current_realm: RealmResolution = Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> PartnerWorkspacePayoutAccountResponse:
    await _enforce_partner_passkey_fresh_auth(
        request=request,
        redis_client=redis_client,
        current_user=current_user,
        current_realm=current_realm,
        action=f"partner.payout_account.create:{access.workspace.id}",
    )
    try:
        item = await CreatePartnerPayoutAccountUseCase(db).execute(
            partner_account_id=access.workspace.id,
            payout_rail=payload.payout_rail,
            display_label=payload.display_label,
            destination_reference=payload.destination_reference,
            destination_metadata=payload.destination_metadata,
            settlement_profile_id=payload.settlement_profile_id,
            make_default=payload.make_default,
            created_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    track_partner_operation(operation="create_workspace_payout_account")
    return _serialize_partner_workspace_payout_account(item)


@router.get(
    "/partner-workspaces/{workspace_id}/payout-accounts/{payout_account_id}/eligibility",
    response_model=PartnerWorkspacePayoutAccountEligibilityResponse,
)
async def get_partner_workspace_payout_account_eligibility(
    workspace_id: UUID,
    payout_account_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.PAYOUTS_READ)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspacePayoutAccountEligibilityResponse:
    payout_account = await ListPartnerPayoutAccountsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        limit=500,
        offset=0,
    )
    target = next((item for item in payout_account if item.id == payout_account_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner payout account not found")

    try:
        eligibility = await EvaluatePartnerPayoutAccountEligibilityUseCase(db).execute(
            payout_account_id=payout_account_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    track_partner_operation(operation="get_workspace_payout_account_eligibility")
    return _serialize_partner_workspace_payout_eligibility(eligibility)


@router.post(
    "/partner-workspaces/{workspace_id}/payout-accounts/{payout_account_id}/make-default",
    response_model=PartnerWorkspacePayoutAccountResponse,
)
async def make_partner_workspace_payout_account_default(
    workspace_id: UUID,
    payout_account_id: UUID,
    request: Request,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.PAYOUTS_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    current_realm: RealmResolution = Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> PartnerWorkspacePayoutAccountResponse:
    await _enforce_partner_passkey_fresh_auth(
        request=request,
        redis_client=redis_client,
        current_user=current_user,
        current_realm=current_realm,
        action=f"partner.payout_account.make_default:{access.workspace.id}:{payout_account_id}",
    )
    payout_accounts = await ListPartnerPayoutAccountsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        limit=500,
        offset=0,
    )
    target = next((item for item in payout_accounts if item.id == payout_account_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner payout account not found")

    try:
        item = await MakeDefaultPartnerPayoutAccountUseCase(db).execute(
            payout_account_id=payout_account_id,
            selected_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    track_partner_operation(operation="make_workspace_payout_account_default")
    return _serialize_partner_workspace_payout_account(item)


@router.get(
    "/partner-workspaces/{workspace_id}/payout-history",
    response_model=list[PartnerWorkspacePayoutHistoryResponse],
)
async def list_partner_workspace_payout_history(
    workspace_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.PAYOUTS_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspacePayoutHistoryResponse]:
    track_partner_operation(operation="list_workspace_payout_history")
    return await _load_workspace_payout_history(access=access, db=db, limit=limit, offset=offset)


@router.get(
    "/partner-workspaces/{workspace_id}/conversion-records",
    response_model=list[PartnerWorkspaceConversionRecordResponse],
)
async def list_partner_workspace_conversion_records(
    workspace_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.EARNINGS_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceConversionRecordResponse]:
    reporting_context = await BuildPartnerWorkspaceReportingUseCase(db).execute(
        partner_account_id=access.workspace.id,
        order_limit=limit,
        order_offset=offset,
    )
    track_partner_operation(operation="list_workspace_conversion_records")
    return [_serialize_workspace_conversion_record(item) for item in reporting_context.order_items]


@router.get(
    "/partner-workspaces/{workspace_id}/conversion-records/{order_id}/explainability",
    response_model=OrderExplainabilityResponse,
)
async def get_partner_workspace_conversion_explainability(
    workspace_id: UUID,
    order_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.EARNINGS_READ)),
    db: AsyncSession = Depends(get_db),
) -> OrderExplainabilityResponse:
    reporting_use_case = BuildPartnerWorkspaceReportingUseCase(db)
    is_visible = await reporting_use_case.is_order_visible_to_workspace(
        partner_account_id=access.workspace.id,
        order_id=order_id,
    )
    if not is_visible:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversion record not found for this workspace",
        )

    explainability_result = await GetOrderExplainabilityUseCase(db).execute(order_id=order_id)
    track_partner_operation(operation="get_workspace_conversion_explainability")
    return OrderExplainabilityResponse(
        order=_serialize_order_explainability_summary(explainability_result.order),
        commissionability_evaluation=_serialize_order_explainability_evaluation(
            explainability_result.commissionability_evaluation
        ),
        explainability=explainability_result.explainability_payload,
    )


@router.get(
    "/partner-workspaces/{workspace_id}/analytics-metrics",
    response_model=list[PartnerWorkspaceAnalyticsMetricResponse],
)
async def list_partner_workspace_analytics_metrics(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.EARNINGS_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceAnalyticsMetricResponse]:
    reporting_context = await BuildPartnerWorkspaceReportingUseCase(db).execute(
        partner_account_id=access.workspace.id,
        order_limit=200,
        order_offset=0,
        statement_limit=100,
        statement_offset=0,
    )
    track_partner_operation(operation="list_workspace_analytics_metrics")
    return _build_workspace_analytics_metrics(
        partner_account_id=access.workspace.id,
        report_pack=reporting_context.report_pack,
    )


@router.get(
    "/partner-workspaces/{workspace_id}/reporting-summary",
    response_model=PartnerWorkspaceReportingSummaryResponse,
)
async def get_partner_workspace_reporting_summary(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.EARNINGS_READ)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceReportingSummaryResponse:
    reporting_context = await BuildPartnerWorkspaceReportingUseCase(db).execute(
        partner_account_id=access.workspace.id,
        order_limit=500,
        order_offset=0,
        statement_limit=200,
        statement_offset=0,
        payout_limit=100,
        payout_offset=0,
    )
    track_partner_operation(operation="get_workspace_reporting_summary")
    return _build_workspace_reporting_summary(
        partner_account_id=access.workspace.id,
        report_pack=reporting_context.report_pack,
    )


@router.get(
    "/partner-workspaces/{workspace_id}/settlement-sandbox",
    response_model=PartnerWorkspaceSettlementSandboxSimulationResponse,
)
async def get_partner_workspace_settlement_sandbox(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.PAYOUTS_READ)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceSettlementSandboxSimulationResponse:
    track_partner_operation(operation="get_workspace_settlement_sandbox")
    return await _load_workspace_settlement_sandbox(access=access, db=db)


@router.get(
    "/partner-workspaces/{workspace_id}/report-exports",
    response_model=list[PartnerWorkspaceReportExportResponse],
)
async def list_partner_workspace_report_exports(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.EARNINGS_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceReportExportResponse]:
    track_partner_operation(operation="list_workspace_report_exports")
    return await _load_workspace_report_exports(access=access, db=db)


@router.post(
    "/partner-workspaces/{workspace_id}/report-exports/{export_id}/schedule",
    response_model=PartnerWorkspaceReportExportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def schedule_partner_workspace_report_export(
    workspace_id: UUID,
    export_id: str,
    payload: SchedulePartnerWorkspaceReportExportRequest,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.OPERATIONS_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceReportExportResponse:
    exports = await _load_workspace_report_exports(access=access, db=db)
    target = next((item for item in exports if item.id == export_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report export not found")
    if "schedule_export" not in target.available_actions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Report export cannot be scheduled from the current workspace state",
        )
    try:
        await CreatePartnerWorkspaceWorkflowEventUseCase(db).execute(
            partner_account_id=access.workspace.id,
            subject_kind=_WORKSPACE_REPORT_EXPORT_SUBJECT_KIND,
            subject_id=export_id,
            action_kind=_WORKSPACE_REPORT_EXPORT_SCHEDULE_ACTION,
            message=payload.message,
            event_payload={
                **payload.request_payload,
                "requested_export_kind": target.kind,
                "requested_export_cadence": target.cadence,
                "export_status_at_request": target.status,
            },
            created_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    track_partner_operation(operation="schedule_workspace_report_export")
    refreshed_exports = await _load_workspace_report_exports(access=access, db=db)
    refreshed = next((item for item in refreshed_exports if item.id == export_id), None)
    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Scheduled export not found after refresh",
        )
    return refreshed


@router.get(
    "/partner-workspaces/{workspace_id}/integration-credentials",
    response_model=list[PartnerWorkspaceIntegrationCredentialResponse],
)
async def list_partner_workspace_integration_credentials(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.INTEGRATIONS_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceIntegrationCredentialResponse]:
    items = await ListPartnerWorkspaceIntegrationCredentialsUseCase(db).execute(partner_account_id=access.workspace.id)
    track_partner_operation(operation="list_workspace_integration_credentials")
    return [
        _serialize_workspace_integration_credential(
            workspace_status=access.workspace.status,
            model=item,
        )
        for item in items
    ]


@router.post(
    "/partner-workspaces/{workspace_id}/integration-credentials/{credential_kind}/rotate",
    response_model=RotatePartnerWorkspaceIntegrationCredentialResponse,
)
async def rotate_partner_workspace_integration_credential(
    workspace_id: UUID,
    credential_kind: PartnerIntegrationCredentialKind,
    body: RotatePartnerWorkspaceIntegrationCredentialRequest,
    request: Request,
    access: PartnerWorkspaceAccess = Depends(
        require_partner_workspace_permission(PartnerPermission.INTEGRATIONS_WRITE)
    ),
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> RotatePartnerWorkspaceIntegrationCredentialResponse:
    await _enforce_partner_passkey_fresh_auth(
        request=request,
        redis_client=redis_client,
        current_user=current_user,
        current_realm=current_realm,
        action=f"partner.integration_credential.rotate:{access.workspace.id}:{credential_kind.value}",
    )
    result = await RotatePartnerWorkspaceIntegrationCredentialUseCase(db).execute(
        partner_account_id=access.workspace.id,
        credential_kind=credential_kind,
        actor_admin_user_id=current_user.id,
        destination_ref=body.destination_ref,
        credential_metadata=body.credential_metadata,
    )
    track_partner_operation(operation="rotate_workspace_integration_credential")
    return RotatePartnerWorkspaceIntegrationCredentialResponse(
        credential=_serialize_workspace_integration_credential(
            workspace_status=access.workspace.status,
            model=result.model,
        ),
        issued_secret=result.issued_secret,
        issued_at=result.issued_at,
    )


@router.get(
    "/partner-workspaces/{workspace_id}/integration-delivery-logs",
    response_model=list[PartnerWorkspaceIntegrationDeliveryLogResponse],
)
async def list_partner_workspace_integration_delivery_logs(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.INTEGRATIONS_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceIntegrationDeliveryLogResponse]:
    items = await BuildPartnerWorkspaceIntegrationDeliveryLogsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        workspace_status=access.workspace.status,
        workspace_key=access.workspace.account_key,
        workspace_label=access.workspace.display_name,
    )
    track_partner_operation(operation="list_workspace_integration_delivery_logs")
    return [_serialize_workspace_integration_delivery_log(item) for item in items]


@router.get(
    "/partner-workspaces/{workspace_id}/postback-readiness",
    response_model=PartnerWorkspacePostbackReadinessResponse,
)
async def get_partner_workspace_postback_readiness(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.INTEGRATIONS_READ)),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspacePostbackReadinessResponse:
    item = await BuildPartnerWorkspacePostbackReadinessUseCase(db).execute(
        partner_account_id=access.workspace.id,
        workspace_status=access.workspace.status,
        workspace_label=access.workspace.display_name,
    )
    track_partner_operation(operation="get_workspace_postback_readiness")
    return _serialize_workspace_postback_readiness(item)


@router.get(
    "/partner-workspaces/{workspace_id}/review-requests",
    response_model=list[PartnerWorkspaceReviewRequestResponse],
)
async def list_partner_workspace_review_requests(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.WORKSPACE_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceReviewRequestResponse]:
    track_partner_operation(operation="list_workspace_review_requests")
    return await _load_workspace_review_requests(access=access, db=db)


@router.post(
    "/partner-workspaces/{workspace_id}/review-requests/{review_request_id}/responses",
    response_model=PartnerWorkspaceThreadEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def respond_partner_workspace_review_request(
    workspace_id: UUID,
    review_request_id: str,
    payload: SubmitPartnerWorkspaceReviewRequestResponseRequest,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.OPERATIONS_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceThreadEventResponse:
    review_requests = await _load_workspace_review_requests(access=access, db=db)
    target = next((item for item in review_requests if item.id == review_request_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review request not found")
    if "submit_response" not in target.available_actions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review request can no longer accept partner responses",
        )
    try:
        parsed_review_request_id: UUID | None = None
        try:
            parsed_review_request_id = UUID(review_request_id)
        except ValueError:
            parsed_review_request_id = None

        if parsed_review_request_id is not None:
            await PartnerApplicationWorkflowUseCase(db).respond_to_review_request(
                review_request_id=parsed_review_request_id,
                applicant_admin_user_id=current_user.id,
            )
        created = await CreatePartnerWorkspaceWorkflowEventUseCase(db).execute(
            partner_account_id=access.workspace.id,
            subject_kind=_WORKSPACE_REVIEW_REQUEST_SUBJECT_KIND,
            subject_id=review_request_id,
            action_kind=_WORKSPACE_REVIEW_REQUEST_RESPONSE_ACTION,
            message=payload.message,
            event_payload=payload.response_payload,
            created_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    track_partner_operation(operation="respond_workspace_review_request")
    return _serialize_workspace_thread_event(created)


@router.get(
    "/partner-workspaces/{workspace_id}/traffic-declarations",
    response_model=list[PartnerWorkspaceTrafficDeclarationResponse],
)
async def list_partner_workspace_traffic_declarations(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.TRAFFIC_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceTrafficDeclarationResponse]:
    track_partner_operation(operation="list_workspace_traffic_declarations")
    traffic_declarations = await ListTrafficDeclarationsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        limit=100,
        offset=0,
    )
    creative_approvals = await ListCreativeApprovalsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        limit=100,
        offset=0,
    )
    return _build_workspace_traffic_declarations(
        traffic_declarations=traffic_declarations,
        creative_approvals=creative_approvals,
    )


@router.post(
    "/partner-workspaces/{workspace_id}/traffic-declarations",
    response_model=TrafficDeclarationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_partner_workspace_traffic_declaration(
    workspace_id: UUID,
    payload: SubmitPartnerWorkspaceTrafficDeclarationRequest,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.TRAFFIC_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TrafficDeclarationResponse:
    try:
        created = await CreateTrafficDeclarationUseCase(db).execute(
            partner_account_id=access.workspace.id,
            declaration_kind=payload.declaration_kind.value,
            scope_label=payload.scope_label,
            declaration_payload=payload.declaration_payload,
            notes=payload.notes,
            submitted_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    track_partner_operation(operation="submit_workspace_traffic_declaration")
    return TrafficDeclarationResponse.model_validate(created)


@router.post(
    "/partner-workspaces/{workspace_id}/creative-approvals",
    response_model=CreativeApprovalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_partner_workspace_creative_approval(
    workspace_id: UUID,
    payload: SubmitPartnerWorkspaceCreativeApprovalRequest,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.TRAFFIC_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> CreativeApprovalResponse:
    try:
        created = await CreateCreativeApprovalUseCase(db).execute(
            partner_account_id=access.workspace.id,
            approval_kind=CreativeApprovalKind.CREATIVE_APPROVAL.value,
            approval_status=CreativeApprovalStatus.UNDER_REVIEW.value,
            scope_label=payload.scope_label,
            creative_ref=payload.creative_ref,
            approval_payload=payload.approval_payload,
            notes=payload.notes,
            submitted_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    track_partner_operation(operation="submit_workspace_creative_approval")
    return CreativeApprovalResponse.model_validate(created)


@router.get(
    "/partner-workspaces/{workspace_id}/creative-approvals",
    response_model=list[CreativeApprovalResponse],
)
async def list_partner_workspace_creative_approvals(
    workspace_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.TRAFFIC_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[CreativeApprovalResponse]:
    items = await ListCreativeApprovalsUseCase(db).execute(
        partner_account_id=access.workspace.id,
        approval_kind=CreativeApprovalKind.CREATIVE_APPROVAL.value,
        limit=limit,
        offset=offset,
    )
    track_partner_operation(operation="list_workspace_creative_approvals")
    return [CreativeApprovalResponse.model_validate(item) for item in items]


@router.get(
    "/partner-workspaces/{workspace_id}/cases",
    response_model=list[PartnerWorkspaceCaseResponse],
)
async def list_partner_workspace_cases(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.WORKSPACE_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerWorkspaceCaseResponse]:
    track_partner_operation(operation="list_workspace_cases")
    return await _load_workspace_cases(access=access, db=db)


@router.post(
    "/partner-workspaces/{workspace_id}/cases/{case_id}/responses",
    response_model=PartnerWorkspaceThreadEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def respond_partner_workspace_case(
    workspace_id: UUID,
    case_id: str,
    payload: SubmitPartnerWorkspaceCaseResponseRequest,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.OPERATIONS_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceThreadEventResponse:
    cases = await _load_workspace_cases(access=access, db=db)
    target = next((item for item in cases if item.id == case_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if "reply" not in target.available_actions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Case can no longer accept partner replies",
        )
    try:
        created = await CreatePartnerWorkspaceWorkflowEventUseCase(db).execute(
            partner_account_id=access.workspace.id,
            subject_kind=_WORKSPACE_CASE_SUBJECT_KIND,
            subject_id=case_id,
            action_kind=_WORKSPACE_CASE_REPLY_ACTION,
            message=payload.message,
            event_payload=payload.response_payload,
            created_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    track_partner_operation(operation="respond_workspace_case")
    return _serialize_workspace_thread_event(created)


@router.post(
    "/partner-workspaces/{workspace_id}/cases/{case_id}/ready-for-ops",
    response_model=PartnerWorkspaceThreadEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def mark_partner_workspace_case_ready_for_ops(
    workspace_id: UUID,
    case_id: str,
    payload: MarkPartnerWorkspaceCaseReadyForOpsRequest,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.OPERATIONS_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceThreadEventResponse:
    cases = await _load_workspace_cases(access=access, db=db)
    target = next((item for item in cases if item.id == case_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if "mark_ready_for_ops" not in target.available_actions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Case cannot transition to waiting_on_ops from its current state",
        )
    try:
        created = await CreatePartnerWorkspaceWorkflowEventUseCase(db).execute(
            partner_account_id=access.workspace.id,
            subject_kind=_WORKSPACE_CASE_SUBJECT_KIND,
            subject_id=case_id,
            action_kind=_WORKSPACE_CASE_READY_FOR_OPS_ACTION,
            message=payload.message,
            event_payload=payload.response_payload,
            created_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    track_partner_operation(operation="mark_workspace_case_ready_for_ops")
    return _serialize_workspace_thread_event(created)


@router.post(
    "/partner-workspaces/{workspace_id}/members",
    response_model=PartnerWorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_partner_workspace_member(
    workspace_id: UUID,
    body: AddPartnerWorkspaceMemberRequest,
    request: Request,
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.MEMBERSHIP_WRITE)),
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    current_realm: RealmResolution = Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> PartnerWorkspaceMemberResponse:
    _require_partner_realm(current_realm)
    await _enforce_partner_passkey_fresh_auth(
        request=request,
        redis_client=redis_client,
        current_user=current_user,
        current_realm=current_realm,
        action=f"partner.member.create:{access.workspace.id}",
    )
    partner_account_repo = PartnerAccountRepository(db)
    use_case = AddPartnerWorkspaceMemberUseCase(db, partner_account_repo)
    target_admin_user_id = body.admin_user_id
    if target_admin_user_id is None and body.operator_lookup is not None:
        operator = await AdminUserRepository(db).get_by_login_or_email(
            body.operator_lookup,
            realm_id=current_realm.auth_realm.id,
        )
        if operator is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner operator not found")
        target_admin_user_id = operator.id

    if target_admin_user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Partner operator target is required")

    try:
        membership = await use_case.execute(
            partner_account_id=access.workspace.id,
            admin_user_id=target_admin_user_id,
            role_key=body.role_key,
            invited_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    role = await partner_account_repo.get_role_by_id(membership.role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Partner workspace role is missing",
        )

    operator = await AdminUserRepository(db).get_by_id(membership.admin_user_id)
    track_partner_operation(operation="add_workspace_member")
    return _serialize_workspace_member(membership=membership, role=role, operator=operator)
