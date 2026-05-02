"""Admin routes for referral, gift-code, and partner analytics."""

import hmac
from datetime import UTC, datetime
from decimal import Decimal
from time import perf_counter
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.gifts import IssueGiftCodeUseCase, ListGiftCodesUseCase
from src.application.use_cases.growth_codes import ResolveGrowthCodeUseCase
from src.application.use_cases.growth_codes.admin_signals import (
    GetAdminGrowthSignalsOverviewUseCase,
    ListAdminGrowthAbuseSignalsUseCase,
)
from src.application.use_cases.growth_codes.reporting import (
    ExportGrowthReportingOverviewUseCase,
    GetGrowthReportingOverviewUseCase,
    GrowthReportingDailyPoint,
    GrowthReportingExecutiveSummary,
    GrowthReportingExport,
    GrowthReportingFamilySummary,
    GrowthReportingHealth,
    GrowthReportingOverview,
    GrowthReportingRefreshResult,
    GrowthReportingRefreshRunSummary,
    RefreshGrowthReportingRollupsUseCase,
)
from src.application.use_cases.growth_codes.reporting_distribution import (
    ClaimDueGrowthReportingDeliveriesUseCase,
    CleanupGrowthReportingArtifactsUseCase,
    CompleteGrowthReportingDeliveryUseCase,
    CreateGrowthReportingSubscriptionUseCase,
    ExportGrowthReportingDeliveryArtifactUseCase,
    ExportGrowthReportingGovernanceSnapshotUseCase,
    GetGrowthReportingGovernanceOverviewUseCase,
    GrowthReportingDeliveryClaimResult,
    GrowthReportingDeliveryList,
    GrowthReportingDeliverySummary,
    GrowthReportingGovernanceAuditEventSummary,
    GrowthReportingGovernanceCoverageCount,
    GrowthReportingGovernanceDecisionSummary,
    GrowthReportingGovernanceFollowupQueueItem,
    GrowthReportingGovernanceFollowupSummary,
    GrowthReportingGovernanceOverview,
    GrowthReportingRecipientPolicySummary,
    GrowthReportingSubscriptionList,
    GrowthReportingSubscriptionSummary,
    ListGrowthReportingDeliveriesUseCase,
    ListGrowthReportingSubscriptionsUseCase,
    ProcessGrowthReportingGovernanceFollowupsUseCase,
    UpdateGrowthReportingGovernanceFollowupUseCase,
    UpdateGrowthReportingSubscriptionPolicyUseCase,
    UpdateGrowthReportingSubscriptionStatusUseCase,
)
from src.application.use_cases.growth_notifications.admin_controls import (
    CreateAdminManualGrowthNotificationUseCase,
    ManageCustomerGrowthNotificationDeliveryUseCase,
)
from src.application.use_cases.growth_notifications.forensics import (
    GetCustomerGrowthNotificationDeliveryForensicsUseCase,
)
from src.config import settings
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.notification_queue_model import NotificationQueue
from src.infrastructure.database.models.referral_commission_model import ReferralCommissionModel
from src.infrastructure.database.repositories.customer_growth_notification_delivery_repository import (
    CustomerGrowthNotificationDeliveryRepository,
)
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.infrastructure.database.repositories.referral_commission_repo import (
    ReferralCommissionRepository,
)
from src.infrastructure.database.repositories.storefront_repo import StorefrontRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    ADMIN_GROWTH_SURFACE,
    log_growth_code_event,
    observe_growth_admin_grant,
    observe_growth_admin_lookup,
    observe_growth_reporting_refresh,
    update_growth_reporting_health_metrics,
)
from src.infrastructure.monitoring.metrics import route_operations_total
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission, require_role

from .growth_schemas import (
    AdminCreateGrowthReportingSubscriptionRequest,
    AdminGiftCodeListItemResponse,
    AdminGrowthAbuseSignalResponse,
    AdminGrowthAbuseSignalsResponse,
    AdminGrowthCodeLookupRequest,
    AdminGrowthCodeLookupResponse,
    AdminGrowthLifecycleEventResponse,
    AdminGrowthNotificationDeliveryActionRequest,
    AdminGrowthNotificationDeliveryDetailResponse,
    AdminGrowthNotificationDeliveryEventResponse,
    AdminGrowthNotificationDeliveryExportResponse,
    AdminGrowthNotificationDeliveryResponse,
    AdminGrowthNotificationQueueSnapshotResponse,
    AdminGrowthNotificationSourceSummaryResponse,
    AdminGrowthReportingDailyPointResponse,
    AdminGrowthReportingDeliveriesResponse,
    AdminGrowthReportingDeliveryArtifactExportResponse,
    AdminGrowthReportingDeliveryResponse,
    AdminGrowthReportingExecutiveSummaryResponse,
    AdminGrowthReportingFamilySummaryResponse,
    AdminGrowthReportingGovernanceAuditEventResponse,
    AdminGrowthReportingGovernanceCoverageCountResponse,
    AdminGrowthReportingGovernanceDecisionResponse,
    AdminGrowthReportingGovernanceExportResponse,
    AdminGrowthReportingGovernanceFollowupQueueItemResponse,
    AdminGrowthReportingGovernanceFollowupResponse,
    AdminGrowthReportingGovernanceOverviewResponse,
    AdminGrowthReportingHealthResponse,
    AdminGrowthReportingOverviewResponse,
    AdminGrowthReportingRecipientPolicyResponse,
    AdminGrowthReportingRefreshResponse,
    AdminGrowthReportingRefreshRunResponse,
    AdminGrowthReportingSubscriptionResponse,
    AdminGrowthReportingSubscriptionsResponse,
    AdminGrowthSignalCountResponse,
    AdminGrowthSignalsOverviewResponse,
    AdminGrowthUserSummary,
    AdminIssueGiftCodeBatchRequest,
    AdminIssueGiftCodeBatchResponse,
    AdminIssueGiftCodeRequest,
    AdminIssueGiftCodeResponse,
    AdminListGiftCodesResponse,
    AdminListGrowthNotificationDeliveriesResponse,
    AdminManualGrowthNotificationRequest,
    AdminManualGrowthNotificationResponse,
    AdminPartnerDetailResponse,
    AdminPartnerListItemResponse,
    AdminPartnersListResponse,
    AdminReferralCommissionRecord,
    AdminReferralOverviewResponse,
    AdminReferralReferrerRow,
    AdminReferralUserDetailResponse,
    AdminUpdateGrowthReportingGovernanceFollowupRequest,
    AdminUpdateGrowthReportingSubscriptionRequest,
    AdminUpdateGrowthReportingSubscriptionStatusRequest,
    InternalClaimGrowthReportingDeliveriesResponse,
    InternalCleanupGrowthReportingArtifactsResponse,
    InternalCompleteGrowthReportingDeliveryRequest,
    InternalProcessGrowthReportingGovernanceFollowupsResponse,
)

router = APIRouter(prefix="/admin", tags=["admin", "growth"])


def _is_valid_telegram_bot_secret(secret: str | None) -> bool:
    configured = settings.telegram_bot_internal_secret.get_secret_value().strip()
    if not configured or not secret:
        return False
    return hmac.compare_digest(secret.strip(), configured)


def _require_telegram_bot_secret(secret: str | None) -> None:
    if _is_valid_telegram_bot_secret(secret):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def _iso_or_none(value) -> str | None:
    return value.isoformat() if value is not None else None


def _serialize_growth_reporting_subscription_audit_payload(
    item: GrowthReportingSubscriptionSummary,
) -> dict[str, object]:
    return {
        "recipient_email": item.recipient_email,
        "recipient_name": item.recipient_name,
        "audience_key": item.audience_key,
        "cadence": item.cadence,
        "report_window_days": item.report_window_days,
        "subscription_status": item.subscription_status,
        "health_status": item.health_status,
        "policy": {
            "template_key": item.policy.template_key,
            "template_locale": item.policy.template_locale,
            "email_subject_prefix": item.policy.email_subject_prefix,
            "title_override": item.policy.title_override,
            "recipient_domain_policy": item.policy.recipient_domain_policy,
            "allowed_recipient_domains": list(item.policy.allowed_recipient_domains),
            "suppressed_until": _iso_or_none(item.policy.suppressed_until),
            "suppression_reason_code": item.policy.suppression_reason_code,
        },
        "followup": {
            "status": item.followup.status,
            "reason_code": item.followup.reason_code,
            "opened_at": _iso_or_none(item.followup.opened_at),
            "due_at": _iso_or_none(item.followup.due_at),
            "last_notified_at": _iso_or_none(item.followup.last_notified_at),
            "resolved_at": _iso_or_none(item.followup.resolved_at),
            "resolution_code": item.followup.resolution_code,
            "is_overdue": item.followup.is_overdue,
            "action_required": item.followup.action_required,
        },
    }


async def _write_growth_reporting_subscription_audit_entry(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    action: str,
    subscription_id: str,
    previous_payload: dict[str, object] | None,
    next_payload: dict[str, object],
    reason_code: str | None,
) -> None:
    db.add(
        AuditLog(
            admin_id=actor.id,
            action=action,
            entity_type="growth_reporting_subscription",
            entity_id=subscription_id,
            old_value=previous_payload,
            new_value={
                **next_payload,
                "reason_code": reason_code,
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    )
    await db.flush()


def _serialize_user_summary(user: MobileUserModel | None) -> AdminGrowthUserSummary | None:
    if user is None:
        return None

    return AdminGrowthUserSummary(
        id=user.id,
        email=user.email,
        username=user.username,
        telegram_username=user.telegram_username,
        referral_code=user.referral_code,
        is_partner=user.is_partner,
    )


def _serialize_referral_commission(
    commission: ReferralCommissionModel,
    users_by_id: dict[UUID, MobileUserModel],
) -> AdminReferralCommissionRecord:
    return AdminReferralCommissionRecord(
        id=commission.id,
        referrer_user_id=commission.referrer_user_id,
        referred_user_id=commission.referred_user_id,
        payment_id=commission.payment_id,
        commission_rate=float(commission.commission_rate),
        base_amount=float(commission.base_amount),
        commission_amount=float(commission.commission_amount),
        currency=commission.currency,
        created_at=commission.created_at,
        referrer=_serialize_user_summary(users_by_id.get(commission.referrer_user_id)),
        referred_user=_serialize_user_summary(users_by_id.get(commission.referred_user_id)),
    )


def _uuid_or_none(value: object) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _serialize_referral_reward_record(
    allocation,
    users_by_id: dict[UUID, MobileUserModel],
) -> AdminReferralCommissionRecord:
    reward_payload = dict(allocation.reward_payload or {})
    referred_user_id = _uuid_or_none(reward_payload.get("referred_user_id"))
    payment_id = _uuid_or_none(reward_payload.get("payment_id"))
    commission_rate = float(
        reward_payload.get("legacy_commission_rate")
        or reward_payload.get("friend_discount_value")
        or 0
    )
    return AdminReferralCommissionRecord(
        id=allocation.id,
        referrer_user_id=allocation.beneficiary_user_id,
        referred_user_id=referred_user_id,
        payment_id=payment_id,
        commission_rate=commission_rate,
        base_amount=float(reward_payload.get("base_amount") or 0),
        commission_amount=float(allocation.quantity),
        currency=allocation.currency_code or "USD",
        reward_status=allocation.allocation_status,
        hold_until=allocation.hold_until,
        available_at=allocation.available_at,
        reversed_at=allocation.reversed_at,
        source_model="growth_reward",
        created_at=allocation.allocated_at,
        referrer=_serialize_user_summary(users_by_id.get(allocation.beneficiary_user_id)),
        referred_user=_serialize_user_summary(users_by_id.get(referred_user_id)),
    )


def _serialize_partner_list_item(
    user: MobileUserModel,
    stats: dict[str, object] | None,
) -> AdminPartnerListItemResponse:
    resolved_stats = stats or {}
    return AdminPartnerListItemResponse(
        user=_serialize_user_summary(user),
        promoted_at=user.partner_promoted_at,
        code_count=int(resolved_stats.get("code_count", 0) or 0),
        active_code_count=int(resolved_stats.get("active_code_count", 0) or 0),
        total_clients=int(resolved_stats.get("total_clients", 0) or 0),
        total_earned=float(resolved_stats.get("total_earned", 0) or 0),
        last_activity_at=resolved_stats.get("last_activity_at"),
    )


def _serialize_admin_gift_code(
    code,
    policy,
    issuance,
    redemption,
) -> AdminGiftCodeListItemResponse:
    policy_snapshot = dict(policy.policy_snapshot or {}) if policy is not None else {}
    return AdminGiftCodeListItemResponse(
        id=code.id,
        masked_code=f"{code.code_prefix}••••",
        raw_code=issuance.raw_code_encrypted if issuance is not None else None,
        batch_id=code.batch_id,
        status=code.status,
        issuer_type=code.issuer_type,
        source_type=issuance.issuance_type if issuance is not None else None,
        owner_user_id=code.owner_user_id,
        issued_by_admin_id=issuance.issued_by_admin_id if issuance is not None else None,
        plan_family=policy.plan_family if policy is not None else None,
        duration_days=policy.duration_days if policy is not None else None,
        recipient_hint=policy_snapshot.get("recipient_hint"),
        gift_message=policy_snapshot.get("gift_message"),
        expires_at=code.expires_at,
        created_at=code.created_at,
        redeemed_at=redemption.redeemed_at if redemption is not None else None,
        redeemed_by_user_id=redemption.redeemer_user_id if redemption is not None else None,
        source_order_id=issuance.source_order_id if issuance is not None else None,
        source_payment_id=issuance.source_payment_id if issuance is not None else None,
    )


def _serialize_growth_signal_breakdown(items: list[dict[str, object]]) -> list[AdminGrowthSignalCountResponse]:
    serialized: list[AdminGrowthSignalCountResponse] = []
    for item in items:
        if "status" in item:
            key = f"{item.get('code_type', 'unknown')}:{item.get('status', 'unknown')}"
        elif "result" in item:
            key = str(item.get("result") or "unknown")
        elif "reject_reason" in item:
            key = str(item.get("reject_reason") or "unknown")
        elif "allocation_status" in item:
            key = str(item.get("allocation_status") or "unknown")
        elif "reward_type" in item:
            key = str(item.get("reward_type") or "unknown")
        else:
            key = str(item.get("code_type") or "unknown")
        serialized.append(
            AdminGrowthSignalCountResponse(
                key=key,
                count=int(item.get("count", 0) or 0),
            )
        )
    return serialized


def _serialize_growth_reporting_family_summary(
    item: GrowthReportingFamilySummary,
) -> AdminGrowthReportingFamilySummaryResponse:
    return AdminGrowthReportingFamilySummaryResponse(
        family=item.family,
        issued_total=item.issued_total,
        resolution_attempts_total=item.resolution_attempts_total,
        resolution_accepted_total=item.resolution_accepted_total,
        resolution_rejected_total=item.resolution_rejected_total,
        redemption_total=item.redemption_total,
        reservations_reserved_total=item.reservations_reserved_total,
        reservations_consumed_total=item.reservations_consumed_total,
        reservations_released_total=item.reservations_released_total,
        reservations_expired_total=item.reservations_expired_total,
        rewards_created_total=item.rewards_created_total,
        rewards_available_total=item.rewards_available_total,
        rewards_reversed_total=item.rewards_reversed_total,
        reward_created_amount_usd=item.reward_created_amount_usd,
        reward_available_amount_usd=item.reward_available_amount_usd,
        reward_reversed_amount_usd=item.reward_reversed_amount_usd,
    )


def _serialize_growth_reporting_daily_point(
    item: GrowthReportingDailyPoint,
) -> AdminGrowthReportingDailyPointResponse:
    return AdminGrowthReportingDailyPointResponse(
        report_date=item.report_date,
        family=item.family,
        issued_total=item.issued_total,
        resolution_attempts_total=item.resolution_attempts_total,
        resolution_accepted_total=item.resolution_accepted_total,
        resolution_rejected_total=item.resolution_rejected_total,
        redemption_total=item.redemption_total,
        reservations_reserved_total=item.reservations_reserved_total,
        reservations_consumed_total=item.reservations_consumed_total,
        reservations_released_total=item.reservations_released_total,
        reservations_expired_total=item.reservations_expired_total,
        rewards_created_total=item.rewards_created_total,
        rewards_available_total=item.rewards_available_total,
        rewards_reversed_total=item.rewards_reversed_total,
        reward_created_amount_usd=item.reward_created_amount_usd,
        reward_available_amount_usd=item.reward_available_amount_usd,
        reward_reversed_amount_usd=item.reward_reversed_amount_usd,
    )


def _serialize_growth_reporting_refresh_run(
    item: GrowthReportingRefreshRunSummary | None,
) -> AdminGrowthReportingRefreshRunResponse | None:
    if item is None:
        return None
    return AdminGrowthReportingRefreshRunResponse(
        id=item.id,
        trigger_kind=item.trigger_kind,
        refresh_status=item.refresh_status,
        requested_window_days=item.requested_window_days,
        window_start=item.window_start,
        window_end=item.window_end,
        latest_rollup_date=item.latest_rollup_date,
        rows_written=item.rows_written,
        families_updated=list(item.families_updated),
        error_message=item.error_message,
        started_at=item.started_at,
        finished_at=item.finished_at,
        refreshed_at=item.refreshed_at,
    )


def _serialize_growth_reporting_health(
    item: GrowthReportingHealth,
) -> AdminGrowthReportingHealthResponse:
    return AdminGrowthReportingHealthResponse(
        freshness_status=item.freshness_status,
        stale_reason=item.stale_reason,
        refresh_age_seconds=item.refresh_age_seconds,
        expected_refresh_interval_seconds=item.expected_refresh_interval_seconds,
        stale_after_seconds=item.stale_after_seconds,
        auto_refresh_enabled=item.auto_refresh_enabled,
        latest_attempt_at=item.latest_attempt_at,
        latest_success_at=item.latest_success_at,
        latest_failure_at=item.latest_failure_at,
        latest_failure_message=item.latest_failure_message,
        latest_run=_serialize_growth_reporting_refresh_run(item.latest_run),
    )


def _serialize_growth_reporting_executive_summary(
    item: GrowthReportingExecutiveSummary,
) -> AdminGrowthReportingExecutiveSummaryResponse:
    return AdminGrowthReportingExecutiveSummaryResponse(
        total_issued=item.total_issued,
        total_redemptions=item.total_redemptions,
        total_reward_available_usd=item.total_reward_available_usd,
        total_reward_reversed_usd=item.total_reward_reversed_usd,
        resolution_acceptance_rate_pct=item.resolution_acceptance_rate_pct,
        dominant_family=item.dominant_family,
        highlights=list(item.highlights),
    )


def _serialize_growth_reporting_policy(
    item: GrowthReportingRecipientPolicySummary,
) -> AdminGrowthReportingRecipientPolicyResponse:
    return AdminGrowthReportingRecipientPolicyResponse(
        template_key=item.template_key,
        template_locale=item.template_locale,
        email_subject_prefix=item.email_subject_prefix,
        title_override=item.title_override,
        recipient_domain_policy=item.recipient_domain_policy,
        allowed_recipient_domains=list(item.allowed_recipient_domains),
        suppressed_until=item.suppressed_until,
        suppression_reason_code=item.suppression_reason_code,
    )


def _serialize_growth_reporting_governance_coverage_count(
    item: GrowthReportingGovernanceCoverageCount,
) -> AdminGrowthReportingGovernanceCoverageCountResponse:
    return AdminGrowthReportingGovernanceCoverageCountResponse(
        coverage_state=item.coverage_state,
        count=item.count,
    )


def _serialize_growth_reporting_governance_followup(
    item: GrowthReportingGovernanceFollowupSummary,
) -> AdminGrowthReportingGovernanceFollowupResponse:
    return AdminGrowthReportingGovernanceFollowupResponse(
        status=item.status,
        reason_code=item.reason_code,
        opened_at=item.opened_at,
        due_at=item.due_at,
        last_notified_at=item.last_notified_at,
        resolved_at=item.resolved_at,
        resolution_code=item.resolution_code,
        is_overdue=item.is_overdue,
        action_required=item.action_required,
    )


def _serialize_growth_reporting_governance_followup_queue_item(
    item: GrowthReportingGovernanceFollowupQueueItem,
) -> AdminGrowthReportingGovernanceFollowupQueueItemResponse:
    return AdminGrowthReportingGovernanceFollowupQueueItemResponse(
        subscription_id=item.subscription_id,
        recipient_email=item.recipient_email,
        audience_key=item.audience_key,
        health_status=item.health_status,
        followup=_serialize_growth_reporting_governance_followup(item.followup),
        next_delivery_at=item.next_delivery_at,
        latest_delivery_status=item.latest_delivery_status,
        latest_delivery_reason=item.latest_delivery_reason,
    )


def _serialize_growth_reporting_governance_decision(
    item: GrowthReportingGovernanceDecisionSummary,
) -> AdminGrowthReportingGovernanceDecisionResponse:
    return AdminGrowthReportingGovernanceDecisionResponse(
        delivery_id=item.delivery_id,
        subscription_id=item.subscription_id,
        recipient_email=item.recipient_email,
        audience_key=item.audience_key,
        template_key=item.template_key,
        decision_kind=item.decision_kind,
        status_reason=item.status_reason,
        created_at=item.created_at,
        planned_at=item.planned_at,
        window_start=item.window_start,
        window_end=item.window_end,
        can_export_artifact=item.can_export_artifact,
        summary=item.summary,
    )


def _serialize_growth_reporting_governance_audit_event(
    item: GrowthReportingGovernanceAuditEventSummary,
) -> AdminGrowthReportingGovernanceAuditEventResponse:
    return AdminGrowthReportingGovernanceAuditEventResponse(
        id=item.id,
        action=item.action,
        entity_id=item.entity_id,
        actor_label=item.actor_label,
        reason_code=item.reason_code,
        changed_fields=list(item.changed_fields),
        created_at=item.created_at,
    )


def _serialize_growth_reporting_governance_overview(
    item: GrowthReportingGovernanceOverview,
) -> AdminGrowthReportingGovernanceOverviewResponse:
    return AdminGrowthReportingGovernanceOverviewResponse(
        generated_at=item.generated_at,
        active_subscription_count=item.active_subscription_count,
        paused_subscription_count=item.paused_subscription_count,
        coverage_gap_count=item.coverage_gap_count,
        followup_open_count=item.followup_open_count,
        followup_overdue_count=item.followup_overdue_count,
        coverage_counts=[
            _serialize_growth_reporting_governance_coverage_count(entry)
            for entry in item.coverage_counts
        ],
        followup_queue=[
            _serialize_growth_reporting_governance_followup_queue_item(entry)
            for entry in item.followup_queue
        ],
        recent_decisions=[
            _serialize_growth_reporting_governance_decision(entry)
            for entry in item.recent_decisions
        ],
        recent_audit_events=[
            _serialize_growth_reporting_governance_audit_event(entry)
            for entry in item.recent_audit_events
        ],
        notes=list(item.notes),
    )


def _serialize_growth_reporting_subscription(
    item: GrowthReportingSubscriptionSummary,
) -> AdminGrowthReportingSubscriptionResponse:
    return AdminGrowthReportingSubscriptionResponse(
        id=item.id,
        recipient_email=item.recipient_email,
        recipient_name=item.recipient_name,
        audience_key=item.audience_key,
        delivery_channel=item.delivery_channel,
        cadence=item.cadence,
        report_window_days=item.report_window_days,
        subscription_status=item.subscription_status,
        next_delivery_at=item.next_delivery_at,
        last_delivery_attempt_at=item.last_delivery_attempt_at,
        last_success_at=item.last_success_at,
        latest_delivery_status=item.latest_delivery_status,
        latest_delivery_reason=item.latest_delivery_reason,
        health_status=item.health_status,
        policy=_serialize_growth_reporting_policy(item.policy),
        followup=_serialize_growth_reporting_governance_followup(item.followup),
    )


def _serialize_growth_reporting_delivery(
    item: GrowthReportingDeliverySummary,
) -> AdminGrowthReportingDeliveryResponse:
    return AdminGrowthReportingDeliveryResponse(
        id=item.id,
        subscription_id=item.subscription_id,
        recipient_email=item.recipient_email,
        recipient_name=item.recipient_name,
        audience_key=item.audience_key,
        delivery_channel=item.delivery_channel,
        cadence=item.cadence,
        report_window_days=item.report_window_days,
        template_key=item.template_key,
        template_locale=item.template_locale,
        subject_line=item.subject_line,
        title_line=item.title_line,
        delivery_status=item.delivery_status,
        status_reason=item.status_reason,
        freshness_status=item.freshness_status,
        artifact_checksum=item.artifact_checksum,
        provider_name=item.provider_name,
        provider_message_id=item.provider_message_id,
        failure_message=item.failure_message,
        window_start=item.window_start,
        window_end=item.window_end,
        planned_at=item.planned_at,
        started_at=item.started_at,
        delivered_at=item.delivered_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        can_export_artifact=item.can_export_artifact,
        policy=_serialize_growth_reporting_policy(item.policy),
    )


def _serialize_growth_reporting_subscription_list(
    payload: GrowthReportingSubscriptionList,
) -> AdminGrowthReportingSubscriptionsResponse:
    return AdminGrowthReportingSubscriptionsResponse(
        items=[_serialize_growth_reporting_subscription(item) for item in payload.items],
        total=payload.total,
        overdue_count=payload.overdue_count,
        active_count=payload.active_count,
        retention_rollup_days=payload.retention_rollup_days,
        retention_refresh_run_days=payload.retention_refresh_run_days,
        retention_delivery_days=payload.retention_delivery_days,
    )


def _serialize_growth_reporting_delivery_list(
    payload: GrowthReportingDeliveryList,
) -> AdminGrowthReportingDeliveriesResponse:
    return AdminGrowthReportingDeliveriesResponse(
        items=[_serialize_growth_reporting_delivery(item) for item in payload.items],
        total=payload.total,
        failed_count=payload.failed_count,
    )


def _serialize_growth_reporting_delivery_claims(
    payload: GrowthReportingDeliveryClaimResult,
) -> InternalClaimGrowthReportingDeliveriesResponse:
    return InternalClaimGrowthReportingDeliveriesResponse(
        deliveries=[
            {
                "delivery_id": item.delivery_id,
                "recipient_email": item.recipient_email,
                "recipient_name": item.recipient_name,
                "audience_key": item.audience_key,
                "delivery_channel": item.delivery_channel,
                "subject": item.subject,
                "title": item.title,
                "message": item.message,
                "notes": list(item.notes),
                "locale": item.locale,
            }
            for item in payload.deliveries
        ],
        claimed_count=payload.claimed_count,
        skipped_count=payload.skipped_count,
        overdue_count=payload.overdue_count,
    )


def _serialize_growth_reporting_overview(
    overview: GrowthReportingOverview,
) -> AdminGrowthReportingOverviewResponse:
    return AdminGrowthReportingOverviewResponse(
        window_start=overview.window_start,
        window_end=overview.window_end,
        latest_rollup_date=overview.latest_rollup_date,
        refreshed_at=overview.refreshed_at,
        family_summaries=[
            _serialize_growth_reporting_family_summary(item)
            for item in overview.family_summaries
        ],
        daily_points=[
            _serialize_growth_reporting_daily_point(item)
            for item in overview.daily_points
        ],
        totals=_serialize_growth_reporting_family_summary(overview.totals),
        health=_serialize_growth_reporting_health(overview.health),
        executive_summary=_serialize_growth_reporting_executive_summary(overview.executive_summary),
        coverage_notes=list(overview.coverage_notes),
    )


def _serialize_growth_reporting_refresh_result(
    result: GrowthReportingRefreshResult,
) -> AdminGrowthReportingRefreshResponse:
    return AdminGrowthReportingRefreshResponse(
        trigger_kind=result.trigger_kind,
        window_start=result.window_start,
        window_end=result.window_end,
        latest_rollup_date=result.latest_rollup_date,
        refreshed_at=result.refreshed_at,
        rows_written=result.rows_written,
        families_updated=list(result.families_updated),
        coverage_notes=list(result.coverage_notes),
    )


def _serialize_growth_reporting_export_payload(export: GrowthReportingExport) -> dict[str, Any]:
    return {
        "window_start": export.overview.window_start.isoformat(),
        "window_end": export.overview.window_end.isoformat(),
        "latest_rollup_date": (
            export.overview.latest_rollup_date.isoformat()
            if export.overview.latest_rollup_date is not None
            else None
        ),
        "refreshed_at": export.overview.refreshed_at.isoformat() if export.overview.refreshed_at else None,
        "coverage_notes": list(export.overview.coverage_notes),
        "totals": jsonable_encoder(_serialize_growth_reporting_family_summary(export.overview.totals)),
        "family_summaries": jsonable_encoder(
            [_serialize_growth_reporting_family_summary(item) for item in export.overview.family_summaries]
        ),
        "daily_points": jsonable_encoder(
            [_serialize_growth_reporting_daily_point(item) for item in export.overview.daily_points]
        ),
        "health": jsonable_encoder(_serialize_growth_reporting_health(export.overview.health)),
        "executive_summary": jsonable_encoder(
            _serialize_growth_reporting_executive_summary(export.overview.executive_summary),
        ),
        "raw_rows": export.raw_rows,
    }


def _serialize_growth_delivery(
    delivery,
    *,
    users_by_id: dict[UUID, MobileUserModel],
    queues_by_id: dict[UUID, NotificationQueue],
) -> AdminGrowthNotificationDeliveryResponse:
    payload = dict(delivery.delivery_payload or {})
    queue_entry = (
        queues_by_id.get(delivery.notification_queue_id)
        if delivery.notification_queue_id is not None
        else None
    )
    current_status = delivery.delivery_status
    if delivery.delivery_channel == "telegram" and queue_entry is not None:
        if queue_entry.status == "sent":
            current_status = "delivered"
        elif queue_entry.status == "failed":
            current_status = "failed"
        elif queue_entry.status == "cancelled" and current_status not in {"paused", "revoked"}:
            current_status = "revoked"

    notes = [
        str(item)
        for item in list(payload.get("notes") or [])
        if str(item).strip()
    ]
    can_resend = delivery.delivery_channel in {"email", "telegram"}
    can_pause = current_status in {"planned", "queued", "processing", "failed"}
    can_revoke = current_status in {"planned", "queued", "processing", "failed", "paused"}
    can_resolve = current_status in {"failed", "skipped", "paused", "revoked"}
    return AdminGrowthNotificationDeliveryResponse(
        id=delivery.id,
        mobile_user_id=delivery.mobile_user_id,
        user=_serialize_user_summary(users_by_id.get(delivery.mobile_user_id)),
        notification_key=delivery.notification_key,
        notification_kind=delivery.notification_kind,
        delivery_channel=delivery.delivery_channel,
        delivery_status=current_status,
        status_reason=delivery.status_reason,
        title=delivery.title,
        message=delivery.message,
        route_slug=payload.get("route_slug"),
        notes=notes,
        source_kind=delivery.source_kind,
        source_id=delivery.source_id,
        notification_queue_id=delivery.notification_queue_id,
        queue_status=queue_entry.status if queue_entry is not None else None,
        queue_error_message=queue_entry.error_message if queue_entry is not None else None,
        created_by_admin_user_id=delivery.created_by_admin_user_id,
        planned_at=delivery.planned_at,
        delivered_at=delivery.delivered_at,
        created_at=delivery.created_at,
        updated_at=delivery.updated_at,
        can_resend=can_resend,
        can_pause=can_pause,
        can_revoke=can_revoke,
        can_resolve=can_resolve,
    )


def _serialize_growth_delivery_event(event) -> AdminGrowthNotificationDeliveryEventResponse:
    return AdminGrowthNotificationDeliveryEventResponse(
        id=event.id,
        event_type=event.event_type,
        delivery_status=event.delivery_status,
        reason_code=event.reason_code,
        event_payload=dict(event.event_payload or {}),
        event_note=event.event_note,
        notification_queue_id=event.notification_queue_id,
        created_by_admin_user_id=event.created_by_admin_user_id,
        occurred_at=event.occurred_at,
        created_at=event.created_at,
    )


def _serialize_growth_notification_queue_snapshot(
    queue_entry: NotificationQueue | None,
) -> AdminGrowthNotificationQueueSnapshotResponse | None:
    if queue_entry is None:
        return None
    return AdminGrowthNotificationQueueSnapshotResponse(
        id=queue_entry.id,
        status=queue_entry.status,
        attempts=queue_entry.attempts,
        scheduled_at=queue_entry.scheduled_at,
        sent_at=queue_entry.sent_at,
        error_message=queue_entry.error_message,
    )


def _serialize_growth_notification_source_summary(
    source_summary: dict[str, Any] | None,
) -> AdminGrowthNotificationSourceSummaryResponse | None:
    if source_summary is None:
        return None
    return AdminGrowthNotificationSourceSummaryResponse(
        source_kind=str(source_summary.get("source_kind") or "unknown"),
        source_id=str(source_summary.get("source_id")) if source_summary.get("source_id") is not None else None,
        source_label=(
            str(source_summary.get("source_label"))
            if source_summary.get("source_label") is not None
            else None
        ),
        source_status=(
            str(source_summary.get("source_status"))
            if source_summary.get("source_status") is not None
            else None
        ),
        owner_user_id=(
            str(source_summary.get("owner_user_id"))
            if source_summary.get("owner_user_id") is not None
            else None
        ),
        beneficiary_user_id=(
            str(source_summary.get("beneficiary_user_id"))
            if source_summary.get("beneficiary_user_id") is not None
            else None
        ),
        metadata=dict(source_summary.get("metadata") or {}),
    )


def _serialize_growth_notification_delivery_detail(
    *,
    forensics,
    users_by_id: dict[UUID, MobileUserModel],
    queues_by_id: dict[UUID, NotificationQueue],
) -> AdminGrowthNotificationDeliveryDetailResponse:
    return AdminGrowthNotificationDeliveryDetailResponse(
        delivery=_serialize_growth_delivery(
            forensics.delivery,
            users_by_id=users_by_id,
            queues_by_id=queues_by_id,
        ),
        sibling_deliveries=[
            _serialize_growth_delivery(item, users_by_id=users_by_id, queues_by_id=queues_by_id)
            for item in forensics.sibling_deliveries
            if item.id != forensics.delivery.id
        ],
        event_timeline=[_serialize_growth_delivery_event(item) for item in forensics.delivery_events],
        queue_snapshot=_serialize_growth_notification_queue_snapshot(forensics.queue_snapshot),
        source_summary=_serialize_growth_notification_source_summary(forensics.source_summary),
        lifecycle_events=[
            AdminGrowthLifecycleEventResponse(
                id=item.id,
                event_name=item.event_name,
                event_family=item.event_family,
                aggregate_type=item.aggregate_type,
                aggregate_id=item.aggregate_id,
                occurred_at=item.occurred_at,
                event_status=item.event_status,
            )
            for item in forensics.lifecycle_events
        ],
        troubleshooting_state=forensics.troubleshooting_state,
        customer_message_key=forensics.customer_message_key,
        support_summary=forensics.support_summary,
    )


def _growth_delivery_export_filename(delivery_id: UUID) -> str:
    return f"growth-notification-delivery-{delivery_id}.json"


def _build_growth_delivery_export_response(
    *,
    delivery_id: UUID,
    payload: AdminGrowthNotificationDeliveryDetailResponse,
) -> JSONResponse:
    filename = _growth_delivery_export_filename(delivery_id)
    export_payload = AdminGrowthNotificationDeliveryExportResponse(
        export_kind="growth_notification_delivery_forensics",
        filename=filename,
        exported_at=datetime.now(UTC),
        delivery_id=delivery_id,
        payload=payload,
    )
    return JSONResponse(
        content=jsonable_encoder(export_payload),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _publish_growth_reporting_health(overview: GrowthReportingOverview) -> None:
    latest_attempt_unix = (
        overview.health.latest_attempt_at.timestamp()
        if overview.health.latest_attempt_at is not None
        else None
    )
    latest_success_unix = (
        overview.health.latest_success_at.timestamp()
        if overview.health.latest_success_at is not None
        else None
    )
    latest_rows_written = (
        overview.health.latest_run.rows_written
        if overview.health.latest_run is not None and overview.health.latest_run.refresh_status == "success"
        else None
    )
    update_growth_reporting_health_metrics(
        freshness_status=overview.health.freshness_status,
        refresh_age_seconds=overview.health.refresh_age_seconds,
        latest_attempt_at=latest_attempt_unix,
        latest_success_at=latest_success_unix,
        rows_written=latest_rows_written,
    )


@router.get("/referrals/overview", response_model=AdminReferralOverviewResponse)
async def get_referral_overview(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> AdminReferralOverviewResponse:
    referral_repo = ReferralCommissionRepository(db)
    reward_repo = GrowthRewardAllocationRepository(db)
    mobile_user_repo = MobileUserRepository(db)

    legacy_overview = await referral_repo.get_admin_overview_metrics()
    reward_overview = await reward_repo.get_referral_reward_overview_metrics()
    recent_commissions = await referral_repo.get_recent(limit=10)
    recent_rewards = await reward_repo.list(
        reward_type="referral_credit",
        limit=10,
        offset=0,
    )
    top_referrers_stats = await referral_repo.get_top_referrer_stats(limit=25)
    top_reward_referrers = await reward_repo.get_top_referrer_reward_stats(limit=25)

    user_ids = {
        commission.referrer_user_id
        for commission in recent_commissions
    } | {
        commission.referred_user_id
        for commission in recent_commissions
    } | {
        stat["referrer_user_id"]
        for stat in top_referrers_stats
    } | {
        reward.beneficiary_user_id
        for reward in recent_rewards
    } | {
        _uuid_or_none(reward.reward_payload.get("referred_user_id"))
        for reward in recent_rewards
    } | {
        stat["beneficiary_user_id"]
        for stat in top_reward_referrers
    }
    user_ids.discard(None)

    users = await mobile_user_repo.list_by_ids(list(user_ids))
    users_by_id = {user.id: user for user in users}
    referred_user_count_map = await mobile_user_repo.count_referred_users_map(
        [
            user_id
            for user_id in {
                *[stat["referrer_user_id"] for stat in top_referrers_stats],
                *[stat["beneficiary_user_id"] for stat in top_reward_referrers],
            }
            if user_id is not None
        ]
    )

    top_referrers_map: dict[UUID, dict[str, object]] = {}
    for stat in top_referrers_stats:
        referrer_user_id = stat["referrer_user_id"]
        row = top_referrers_map.setdefault(
            referrer_user_id,
            {
                "commission_count": 0,
                "total_earned": 0.0,
                "last_commission_at": None,
            },
        )
        row["commission_count"] = int(row["commission_count"]) + int(stat["commission_count"])
        row["total_earned"] = float(row["total_earned"]) + float(stat["total_earned"])
        last_activity = row["last_commission_at"]
        if last_activity is None or (
            stat["last_commission_at"] is not None and stat["last_commission_at"] > last_activity
        ):
            row["last_commission_at"] = stat["last_commission_at"]
    for stat in top_reward_referrers:
        referrer_user_id = stat["beneficiary_user_id"]
        row = top_referrers_map.setdefault(
            referrer_user_id,
            {
                "commission_count": 0,
                "total_earned": 0.0,
                "last_commission_at": None,
            },
        )
        row["commission_count"] = int(row["commission_count"]) + int(stat["reward_count"])
        row["total_earned"] = float(row["total_earned"]) + float(stat["total_earned"])
        last_activity = row["last_commission_at"]
        if last_activity is None or (
            stat["last_reward_at"] is not None and stat["last_reward_at"] > last_activity
        ):
            row["last_commission_at"] = stat["last_reward_at"]

    recent_items = [
        *[
            _serialize_referral_commission(commission, users_by_id)
            for commission in recent_commissions
        ],
        *[_serialize_referral_reward_record(reward, users_by_id) for reward in recent_rewards],
    ]
    recent_items.sort(key=lambda item: item.created_at, reverse=True)

    route_operations_total.labels(route="admin_referrals", action="overview", status="success").inc()
    return AdminReferralOverviewResponse(
        total_commissions=int(legacy_overview["total_commissions"]) + int(reward_overview["total_rewards"]),
        total_earned=float(legacy_overview["total_earned"]) + float(reward_overview["total_earned"]),
        unique_referrers=max(
            int(legacy_overview["unique_referrers"]),
            int(reward_overview["unique_referrers"]),
            await mobile_user_repo.count_distinct_referrers(),
        ),
        unique_referred_users=await mobile_user_repo.count_all_referred_users(),
        recent_commissions=recent_items[:10],
        top_referrers=[
            AdminReferralReferrerRow(
                user=_serialize_user_summary(users_by_id.get(referrer_user_id)),
                commission_count=int(stat["commission_count"]),
                referred_users=int(referred_user_count_map.get(referrer_user_id, 0)),
                total_earned=float(stat["total_earned"]),
                last_commission_at=stat["last_commission_at"],
            )
            for referrer_user_id, stat in sorted(
                top_referrers_map.items(),
                key=lambda item: (
                    float(item[1]["total_earned"]),
                    int(item[1]["commission_count"]),
                ),
                reverse=True,
            )[:10]
            if users_by_id.get(referrer_user_id) is not None
        ],
    )


@router.get("/growth-signals/overview", response_model=AdminGrowthSignalsOverviewResponse)
async def get_growth_signals_overview(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> AdminGrowthSignalsOverviewResponse:
    overview = await GetAdminGrowthSignalsOverviewUseCase(db).execute()
    route_operations_total.labels(route="admin_growth_signals", action="overview", status="success").inc()
    return AdminGrowthSignalsOverviewResponse(
        total_codes=overview.total_codes,
        active_codes=overview.active_codes,
        total_redemptions=overview.total_redemptions,
        active_reservations=overview.active_reservations,
        blocked_reward_count=overview.blocked_reward_count,
        available_referral_credit_usd=overview.available_referral_credit_usd,
        code_status_breakdown=_serialize_growth_signal_breakdown(overview.code_status_breakdown),
        resolution_result_breakdown=_serialize_growth_signal_breakdown(overview.resolution_result_breakdown),
        rejection_reason_breakdown=_serialize_growth_signal_breakdown(overview.rejection_reason_breakdown),
        redemption_breakdown=_serialize_growth_signal_breakdown(overview.redemption_breakdown),
        reward_status_breakdown=_serialize_growth_signal_breakdown(overview.reward_status_breakdown),
        reward_type_breakdown=_serialize_growth_signal_breakdown(overview.reward_type_breakdown),
        recent_lifecycle_events=[
            AdminGrowthLifecycleEventResponse(**item)
            for item in overview.recent_lifecycle_events
        ],
    )


@router.get("/growth-signals/abuse-queue", response_model=AdminGrowthAbuseSignalsResponse)
async def list_growth_abuse_signals(
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> AdminGrowthAbuseSignalsResponse:
    items = await ListAdminGrowthAbuseSignalsUseCase(db).execute(limit=limit)
    route_operations_total.labels(route="admin_growth_signals", action="abuse_queue", status="success").inc()
    return AdminGrowthAbuseSignalsResponse(
        items=[
            AdminGrowthAbuseSignalResponse(
                signal_key=item.signal_key,
                signal_type=item.signal_type,
                severity=item.severity,
                code_type=item.code_type,
                reason_code=item.reason_code,
                count=item.count,
                unique_users=item.unique_users,
                latest_event_at=item.latest_event_at,
                review_hint=item.review_hint,
                growth_code_id=item.growth_code_id,
                reward_allocation_id=item.reward_allocation_id,
                beneficiary_user_id=item.beneficiary_user_id,
                source_redemption_id=item.source_redemption_id,
            )
            for item in items
        ],
        total=len(items),
    )


@router.get("/growth-reporting/overview", response_model=AdminGrowthReportingOverviewResponse)
async def get_growth_reporting_overview(
    window_days: int = Query(14, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> AdminGrowthReportingOverviewResponse:
    overview = await GetGrowthReportingOverviewUseCase(db).execute(window_days=window_days)
    _publish_growth_reporting_health(overview)
    route_operations_total.labels(route="admin_growth_reporting", action="overview", status="success").inc()
    return _serialize_growth_reporting_overview(overview)


@router.get(
    "/growth-reporting/governance",
    response_model=AdminGrowthReportingGovernanceOverviewResponse,
)
async def get_growth_reporting_governance_overview(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> AdminGrowthReportingGovernanceOverviewResponse:
    overview = await GetGrowthReportingGovernanceOverviewUseCase(db).execute()
    route_operations_total.labels(route="admin_growth_reporting", action="governance_overview", status="success").inc()
    return _serialize_growth_reporting_governance_overview(overview)


@router.get(
    "/growth-reporting/subscriptions",
    response_model=AdminGrowthReportingSubscriptionsResponse,
)
async def list_growth_reporting_subscriptions(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> AdminGrowthReportingSubscriptionsResponse:
    payload = await ListGrowthReportingSubscriptionsUseCase(db).execute()
    route_operations_total.labels(route="admin_growth_reporting", action="subscriptions", status="success").inc()
    return _serialize_growth_reporting_subscription_list(payload)


@router.post(
    "/growth-reporting/subscriptions",
    response_model=AdminGrowthReportingSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_growth_reporting_subscription(
    request: AdminCreateGrowthReportingSubscriptionRequest,
    raw_request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminGrowthReportingSubscriptionResponse:
    try:
        item = await CreateGrowthReportingSubscriptionUseCase(db).execute(
            recipient_email=request.recipient_email,
            recipient_name=request.recipient_name,
            audience_key=request.audience_key,
            cadence=request.cadence,
            report_window_days=request.report_window_days,
            template_key=request.policy.template_key,
            template_locale=request.policy.template_locale,
            email_subject_prefix=request.policy.email_subject_prefix,
            title_override=request.policy.title_override,
            recipient_domain_policy=request.policy.recipient_domain_policy,
            allowed_recipient_domains=request.policy.allowed_recipient_domains,
            suppressed_until=request.policy.suppressed_until,
            suppression_reason_code=request.policy.suppression_reason_code,
            created_by_admin_user_id=admin_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await _write_growth_reporting_subscription_audit_entry(
        db=db,
        request=raw_request,
        actor=admin_user,
        action="growth_reporting.subscription.created",
        subscription_id=item.id,
        previous_payload=None,
        next_payload=_serialize_growth_reporting_subscription_audit_payload(item),
        reason_code="subscription_created",
    )
    await db.commit()
    route_operations_total.labels(route="admin_growth_reporting", action="create_subscription", status="success").inc()
    return _serialize_growth_reporting_subscription(item)


@router.put(
    "/growth-reporting/subscriptions/{subscription_id}",
    response_model=AdminGrowthReportingSubscriptionResponse,
)
async def update_growth_reporting_subscription(
    subscription_id: UUID,
    request: AdminUpdateGrowthReportingSubscriptionRequest,
    raw_request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminGrowthReportingSubscriptionResponse:
    existing = await ListGrowthReportingSubscriptionsUseCase(db).execute()
    previous_item = next((item for item in existing.items if item.id == str(subscription_id)), None)
    try:
        item = await UpdateGrowthReportingSubscriptionPolicyUseCase(db).execute(
            subscription_id=subscription_id,
            recipient_email=request.recipient_email,
            recipient_name=request.recipient_name,
            audience_key=request.audience_key,
            cadence=request.cadence,
            report_window_days=request.report_window_days,
            template_key=request.policy.template_key,
            template_locale=request.policy.template_locale,
            email_subject_prefix=request.policy.email_subject_prefix,
            title_override=request.policy.title_override,
            recipient_domain_policy=request.policy.recipient_domain_policy,
            allowed_recipient_domains=request.policy.allowed_recipient_domains,
            suppressed_until=request.policy.suppressed_until,
            suppression_reason_code=request.policy.suppression_reason_code,
            updated_by_admin_user_id=admin_user.id,
        )
    except ValueError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if str(exc) == "growth_reporting_subscription_not_found"
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    await _write_growth_reporting_subscription_audit_entry(
        db=db,
        request=raw_request,
        actor=admin_user,
        action="growth_reporting.subscription.updated",
        subscription_id=item.id,
        previous_payload=_serialize_growth_reporting_subscription_audit_payload(previous_item)
        if previous_item is not None
        else None,
        next_payload=_serialize_growth_reporting_subscription_audit_payload(item),
        reason_code=request.reason_code,
    )
    await db.commit()
    route_operations_total.labels(route="admin_growth_reporting", action="update_subscription", status="success").inc()
    return _serialize_growth_reporting_subscription(item)


@router.post(
    "/growth-reporting/subscriptions/{subscription_id}/pause",
    response_model=AdminGrowthReportingSubscriptionResponse,
)
async def pause_growth_reporting_subscription(
    subscription_id: UUID,
    request: AdminUpdateGrowthReportingSubscriptionStatusRequest,
    raw_request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminGrowthReportingSubscriptionResponse:
    existing = await ListGrowthReportingSubscriptionsUseCase(db).execute()
    previous_item = next((item for item in existing.items if item.id == str(subscription_id)), None)
    try:
        item = await UpdateGrowthReportingSubscriptionStatusUseCase(db).execute(
            subscription_id=subscription_id,
            subscription_status="paused",
            updated_by_admin_user_id=admin_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await _write_growth_reporting_subscription_audit_entry(
        db=db,
        request=raw_request,
        actor=admin_user,
        action="growth_reporting.subscription.paused",
        subscription_id=item.id,
        previous_payload=_serialize_growth_reporting_subscription_audit_payload(previous_item)
        if previous_item is not None
        else None,
        next_payload=_serialize_growth_reporting_subscription_audit_payload(item),
        reason_code=request.reason_code,
    )
    await db.commit()
    route_operations_total.labels(route="admin_growth_reporting", action="pause_subscription", status="success").inc()
    return _serialize_growth_reporting_subscription(item)


@router.post(
    "/growth-reporting/subscriptions/{subscription_id}/resume",
    response_model=AdminGrowthReportingSubscriptionResponse,
)
async def resume_growth_reporting_subscription(
    subscription_id: UUID,
    request: AdminUpdateGrowthReportingSubscriptionStatusRequest,
    raw_request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminGrowthReportingSubscriptionResponse:
    existing = await ListGrowthReportingSubscriptionsUseCase(db).execute()
    previous_item = next((item for item in existing.items if item.id == str(subscription_id)), None)
    try:
        item = await UpdateGrowthReportingSubscriptionStatusUseCase(db).execute(
            subscription_id=subscription_id,
            subscription_status="active",
            updated_by_admin_user_id=admin_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await _write_growth_reporting_subscription_audit_entry(
        db=db,
        request=raw_request,
        actor=admin_user,
        action="growth_reporting.subscription.resumed",
        subscription_id=item.id,
        previous_payload=_serialize_growth_reporting_subscription_audit_payload(previous_item)
        if previous_item is not None
        else None,
        next_payload=_serialize_growth_reporting_subscription_audit_payload(item),
        reason_code=request.reason_code,
    )
    await db.commit()
    route_operations_total.labels(route="admin_growth_reporting", action="resume_subscription", status="success").inc()
    return _serialize_growth_reporting_subscription(item)


@router.post(
    "/growth-reporting/subscriptions/{subscription_id}/follow-up/{action}",
    response_model=AdminGrowthReportingSubscriptionResponse,
)
async def update_growth_reporting_governance_followup(
    subscription_id: UUID,
    action: str,
    request: AdminUpdateGrowthReportingGovernanceFollowupRequest,
    raw_request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminGrowthReportingSubscriptionResponse:
    existing = await ListGrowthReportingSubscriptionsUseCase(db).execute()
    previous_item = next((item for item in existing.items if item.id == str(subscription_id)), None)
    try:
        result = await UpdateGrowthReportingGovernanceFollowupUseCase(db).execute(
            subscription_id=subscription_id,
            action=action,
            reason_code=request.reason_code,
            updated_by_admin_user_id=admin_user.id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if detail == "growth_reporting_subscription_not_found"
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc
    await _write_growth_reporting_subscription_audit_entry(
        db=db,
        request=raw_request,
        actor=admin_user,
        action=f"growth_reporting.subscription.followup.{result.action}",
        subscription_id=result.subscription.id,
        previous_payload=_serialize_growth_reporting_subscription_audit_payload(previous_item)
        if previous_item is not None
        else None,
        next_payload=_serialize_growth_reporting_subscription_audit_payload(result.subscription),
        reason_code=request.reason_code or f"manual_{result.action}",
    )
    await db.commit()
    route_operations_total.labels(
        route="admin_growth_reporting",
        action=f"followup_{result.action}",
        status="success",
    ).inc()
    return _serialize_growth_reporting_subscription(result.subscription)


@router.get(
    "/growth-reporting/deliveries",
    response_model=AdminGrowthReportingDeliveriesResponse,
)
async def list_growth_reporting_deliveries(
    limit: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> AdminGrowthReportingDeliveriesResponse:
    payload = await ListGrowthReportingDeliveriesUseCase(db).execute(limit=limit)
    route_operations_total.labels(route="admin_growth_reporting", action="deliveries", status="success").inc()
    return _serialize_growth_reporting_delivery_list(payload)


@router.post("/growth-reporting/refresh", response_model=AdminGrowthReportingRefreshResponse)
async def refresh_growth_reporting(
    window_days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminGrowthReportingRefreshResponse:
    started = perf_counter()
    try:
        result = await RefreshGrowthReportingRollupsUseCase(db).execute(
            window_days=window_days,
            trigger_kind="manual",
        )
        observe_growth_reporting_refresh(
            trigger_kind="manual",
            result="success",
            duration_seconds=perf_counter() - started,
        )
        update_growth_reporting_health_metrics(
            freshness_status="fresh",
            refresh_age_seconds=0,
            latest_attempt_at=result.refreshed_at.timestamp(),
            latest_success_at=result.refreshed_at.timestamp(),
            rows_written=result.rows_written,
        )
        await db.commit()
    except Exception:
        observe_growth_reporting_refresh(
            trigger_kind="manual",
            result="failure",
            duration_seconds=perf_counter() - started,
        )
        update_growth_reporting_health_metrics(
            freshness_status="failed",
            refresh_age_seconds=None,
            latest_attempt_at=datetime.now(UTC).timestamp(),
            latest_success_at=None,
            rows_written=None,
        )
        await db.commit()
        raise
    route_operations_total.labels(route="admin_growth_reporting", action="refresh", status="success").inc()
    return _serialize_growth_reporting_refresh_result(result)


@router.post("/growth-reporting/internal/refresh", response_model=AdminGrowthReportingRefreshResponse)
async def internal_refresh_growth_reporting(
    window_days: int = Query(30, ge=1, le=90),
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthReportingRefreshResponse:
    _require_telegram_bot_secret(telegram_bot_secret)
    started = perf_counter()
    try:
        result = await RefreshGrowthReportingRollupsUseCase(db).execute(
            window_days=window_days,
            trigger_kind="worker",
        )
        observe_growth_reporting_refresh(
            trigger_kind="worker",
            result="success",
            duration_seconds=perf_counter() - started,
        )
        update_growth_reporting_health_metrics(
            freshness_status="fresh",
            refresh_age_seconds=0,
            latest_attempt_at=result.refreshed_at.timestamp(),
            latest_success_at=result.refreshed_at.timestamp(),
            rows_written=result.rows_written,
        )
        await db.commit()
    except Exception:
        observe_growth_reporting_refresh(
            trigger_kind="worker",
            result="failure",
            duration_seconds=perf_counter() - started,
        )
        update_growth_reporting_health_metrics(
            freshness_status="failed",
            refresh_age_seconds=None,
            latest_attempt_at=datetime.now(UTC).timestamp(),
            latest_success_at=None,
            rows_written=None,
        )
        await db.commit()
        raise
    route_operations_total.labels(route="admin_growth_reporting", action="internal_refresh", status="success").inc()
    return _serialize_growth_reporting_refresh_result(result)


@router.post(
    "/growth-reporting/internal/governance/followups/process",
    response_model=InternalProcessGrowthReportingGovernanceFollowupsResponse,
)
async def internal_process_growth_reporting_governance_followups(
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> InternalProcessGrowthReportingGovernanceFollowupsResponse:
    _require_telegram_bot_secret(telegram_bot_secret)
    result = await ProcessGrowthReportingGovernanceFollowupsUseCase(db).execute()
    await db.commit()
    route_operations_total.labels(
        route="admin_growth_reporting",
        action="internal_process_governance_followups",
        status="success",
    ).inc()
    return InternalProcessGrowthReportingGovernanceFollowupsResponse(
        processed_at=result.processed_at,
        scanned_count=result.scanned_count,
        opened_count=result.opened_count,
        reopened_count=result.reopened_count,
        auto_resolved_count=result.auto_resolved_count,
        reminded_count=result.reminded_count,
        open_count=result.open_count,
        overdue_count=result.overdue_count,
    )


@router.get("/growth-reporting/export")
async def export_growth_reporting_overview(
    window_days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> JSONResponse:
    export = await ExportGrowthReportingOverviewUseCase(db).execute(window_days=window_days)
    route_operations_total.labels(route="admin_growth_reporting", action="export", status="success").inc()
    payload = _serialize_growth_reporting_export_payload(export)
    filename = (
        "growth-reporting-"
        f"{export.overview.window_start.isoformat()}-"
        f"{export.overview.window_end.isoformat()}.json"
    )
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/growth-reporting/governance/export",
    response_model=AdminGrowthReportingGovernanceExportResponse,
)
async def export_growth_reporting_governance_snapshot(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> JSONResponse:
    overview, payload, filename = await ExportGrowthReportingGovernanceSnapshotUseCase(db).execute()
    route_operations_total.labels(route="admin_growth_reporting", action="export_governance", status="success").inc()
    return JSONResponse(
        content=jsonable_encoder(
            AdminGrowthReportingGovernanceExportResponse(
                export_kind="growth_reporting_governance_snapshot",
                filename=filename,
                exported_at=datetime.now(UTC),
                overview=_serialize_growth_reporting_governance_overview(overview),
                payload=payload,
            )
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/growth-reporting/deliveries/{delivery_id}/artifact",
    response_model=AdminGrowthReportingDeliveryArtifactExportResponse,
)
async def export_growth_reporting_delivery_artifact(
    delivery_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> JSONResponse:
    try:
        delivery, payload, filename = await ExportGrowthReportingDeliveryArtifactUseCase(db).execute(
            delivery_id=delivery_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    route_operations_total.labels(route="admin_growth_reporting", action="export_delivery", status="success").inc()
    return JSONResponse(
        content=jsonable_encoder(
            AdminGrowthReportingDeliveryArtifactExportResponse(
                export_kind="growth_reporting_delivery_artifact",
                filename=filename,
                exported_at=datetime.now(UTC),
                delivery=_serialize_growth_reporting_delivery(delivery),
                payload=payload,
            )
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/growth-reporting/internal/deliveries/claim",
    response_model=InternalClaimGrowthReportingDeliveriesResponse,
)
async def internal_claim_growth_reporting_deliveries(
    limit: int = Query(10, ge=1, le=50),
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> InternalClaimGrowthReportingDeliveriesResponse:
    _require_telegram_bot_secret(telegram_bot_secret)
    payload = await ClaimDueGrowthReportingDeliveriesUseCase(db).execute(limit=limit)
    await db.commit()
    route_operations_total.labels(
        route="admin_growth_reporting",
        action="internal_claim_deliveries",
        status="success",
    ).inc()
    return _serialize_growth_reporting_delivery_claims(payload)


@router.post(
    "/growth-reporting/internal/deliveries/{delivery_id}/complete",
    response_model=AdminGrowthReportingDeliveryResponse,
)
async def internal_complete_growth_reporting_delivery(
    delivery_id: UUID,
    request: InternalCompleteGrowthReportingDeliveryRequest,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthReportingDeliveryResponse:
    _require_telegram_bot_secret(telegram_bot_secret)
    try:
        item = await CompleteGrowthReportingDeliveryUseCase(db).execute(
            delivery_id=delivery_id,
            delivery_status=request.delivery_status,
            provider_name=request.provider_name,
            provider_message_id=request.provider_message_id,
            failure_message=request.failure_message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    route_operations_total.labels(
        route="admin_growth_reporting",
        action="internal_complete_delivery",
        status="success",
    ).inc()
    return _serialize_growth_reporting_delivery(item)


@router.post(
    "/growth-reporting/internal/cleanup",
    response_model=InternalCleanupGrowthReportingArtifactsResponse,
)
async def internal_cleanup_growth_reporting_artifacts(
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> InternalCleanupGrowthReportingArtifactsResponse:
    _require_telegram_bot_secret(telegram_bot_secret)
    result = await CleanupGrowthReportingArtifactsUseCase(db).execute()
    await db.commit()
    route_operations_total.labels(route="admin_growth_reporting", action="internal_cleanup", status="success").inc()
    return InternalCleanupGrowthReportingArtifactsResponse(
        rollups_deleted=result.rollups_deleted,
        refresh_runs_deleted=result.refresh_runs_deleted,
        deliveries_deleted=result.deliveries_deleted,
        executed_at=result.executed_at,
    )


@router.get("/referrals/users/{user_id}", response_model=AdminReferralUserDetailResponse)
async def get_referral_user_detail(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> AdminReferralUserDetailResponse:
    mobile_user_repo = MobileUserRepository(db)
    referral_repo = ReferralCommissionRepository(db)
    reward_repo = GrowthRewardAllocationRepository(db)

    user = await mobile_user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile user not found")

    recent_commissions = await referral_repo.get_by_referrer(user_id, limit=20)
    recent_rewards = await reward_repo.list_recent_referral_rewards(beneficiary_user_id=user_id, limit=20)
    stats_map = await referral_repo.get_referrer_stats_map([user_id])
    reward_stats_map = await reward_repo.get_referral_reward_stats_map([user_id])
    stats = stats_map.get(
        user_id,
        {
            "commission_count": 0,
            "referred_users": 0,
            "total_earned": 0,
            "last_commission_at": None,
        },
    )
    reward_stats = reward_stats_map.get(
        user_id,
        {
            "reward_count": 0,
            "total_earned": 0,
            "last_reward_at": None,
        },
    )

    related_user_ids = {user.id}
    related_user_ids.update(commission.referred_user_id for commission in recent_commissions)
    related_user_ids.update(
        referred_user_id
        for referred_user_id in (
            _uuid_or_none(reward.reward_payload.get("referred_user_id"))
            for reward in recent_rewards
        )
        if referred_user_id is not None
    )
    users = await mobile_user_repo.list_by_ids(list(related_user_ids))
    users_by_id = {item.id: item for item in users}
    referred_users = await mobile_user_repo.count_referred_users(user_id)

    recent_items = [
        *[
            _serialize_referral_commission(commission, users_by_id)
            for commission in recent_commissions
        ],
        *[_serialize_referral_reward_record(reward, users_by_id) for reward in recent_rewards],
    ]
    recent_items.sort(key=lambda item: item.created_at, reverse=True)

    route_operations_total.labels(route="admin_referrals", action="user_detail", status="success").inc()
    return AdminReferralUserDetailResponse(
        user=_serialize_user_summary(user),
        referred_by_user_id=user.referred_by_user_id,
        commission_count=int(stats["commission_count"]) + int(reward_stats["reward_count"]),
        referred_users=referred_users,
        total_earned=float(stats["total_earned"]) + float(reward_stats["total_earned"]),
        recent_commissions=recent_items[:20],
    )


@router.get("/partners", response_model=AdminPartnersListResponse)
async def list_partners(
    search: str | None = Query(None, description="Search by email, username, telegram, UUID, referral code"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> AdminPartnersListResponse:
    mobile_user_repo = MobileUserRepository(db)
    partner_repo = PartnerRepository(db)

    users = await mobile_user_repo.list_admin(
        search=search,
        is_partner=True,
        offset=offset,
        limit=limit,
    )
    total = await mobile_user_repo.count_admin(search=search, is_partner=True)
    stats_map = await partner_repo.get_partner_stats_map([user.id for user in users])

    route_operations_total.labels(route="admin_partners", action="list", status="success").inc()
    return AdminPartnersListResponse(
        items=[
            _serialize_partner_list_item(user, stats_map.get(user.id))
            for user in users
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/partners/{user_id}", response_model=AdminPartnerDetailResponse)
async def get_partner_detail(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> AdminPartnerDetailResponse:
    mobile_user_repo = MobileUserRepository(db)
    partner_repo = PartnerRepository(db)

    user = await mobile_user_repo.get_by_id(user_id)
    if user is None or not user.is_partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")

    stats_map = await partner_repo.get_partner_stats_map([user_id])
    stats = stats_map.get(user_id, {})
    codes = await partner_repo.get_codes_by_partner(user_id)
    earnings = await partner_repo.get_earnings_by_partner(user_id, limit=20)

    route_operations_total.labels(route="admin_partners", action="detail", status="success").inc()
    return AdminPartnerDetailResponse(
        **_serialize_partner_list_item(user, stats).model_dump(),
        codes=[code for code in codes],
        recent_earnings=[earning for earning in earnings],
    )


@router.post("/growth-codes/lookup", response_model=AdminGrowthCodeLookupResponse)
async def lookup_growth_code(
    body: AdminGrowthCodeLookupRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> AdminGrowthCodeLookupResponse:
    storefront_id = None
    if body.storefront_key:
        storefront_repo = StorefrontRepository(db)
        storefront = await storefront_repo.get_storefront_by_key(body.storefront_key)
        if storefront is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Storefront not found")
        storefront_id = storefront.id

    use_case = ResolveGrowthCodeUseCase(db)
    result = await use_case.execute(
        code=body.code,
        action_context=body.action_context,
        user_id=body.lookup_user_id,
        plan_id=body.plan_id,
        amount=Decimal(str(body.amount)) if body.amount is not None else None,
        storefront_id=storefront_id,
        existing_partner_code_present=body.existing_partner_code_present,
        existing_promo_present=body.existing_promo_present,
        surface=f"admin:{body.channel}",
    )
    growth_repo = GrowthCodeRepository(db)
    reward_repo = GrowthRewardAllocationRepository(db)
    issuances: list[dict[str, str | int | float | None]] = []
    touchpoints: list[dict[str, str | int | float | None]] = []
    signup_attributions: list[dict[str, str | int | float | None]] = []
    redemptions: list[dict[str, str | int | float | None]] = []
    rewards: list[dict[str, str | int | float | None]] = []
    resolution_events: list[dict[str, str | int | float | None]] = []
    lifecycle_summary: dict[str, int] = {}

    if result.growth_code_id is not None:
        issuance_items = await growth_repo.list_issuances(result.growth_code_id)
        touchpoint_items = await growth_repo.list_touchpoints(result.growth_code_id)
        signup_items = await growth_repo.list_signup_attributions(result.growth_code_id)
        redemption_items = await growth_repo.list_redemptions(result.growth_code_id)
        reward_items = await reward_repo.list_for_source_code(result.growth_code_id)
        resolution_items = await growth_repo.list_resolution_events(growth_code_id=result.growth_code_id, limit=25)

        issuances = [
            {
                "id": str(item.id),
                "issuance_type": item.issuance_type,
                "issued_to_user_id": str(item.issued_to_user_id) if item.issued_to_user_id else None,
                "issued_by_admin_id": str(item.issued_by_admin_id) if item.issued_by_admin_id else None,
                "source_order_id": str(item.source_order_id) if item.source_order_id else None,
                "source_payment_id": str(item.source_payment_id) if item.source_payment_id else None,
                "reason_code": item.reason_code,
                "created_at": _iso_or_none(item.created_at),
            }
            for item in issuance_items
        ]
        touchpoints = [
            {
                "id": str(item.id),
                "surface": item.surface,
                "channel": item.channel,
                "registered_user_id": str(item.registered_user_id) if item.registered_user_id else None,
                "converted_to_signup_at": _iso_or_none(item.converted_to_signup_at),
                "converted_to_order_id": str(item.converted_to_order_id) if item.converted_to_order_id else None,
                "created_at": _iso_or_none(item.created_at),
            }
            for item in touchpoint_items
        ]
        signup_attributions = [
            {
                "id": str(item.id),
                "user_id": str(item.user_id),
                "touchpoint_id": str(item.touchpoint_id),
                "attribution_source": item.attribution_source,
                "created_at": _iso_or_none(item.created_at),
            }
            for item in signup_items
        ]
        redemptions = [
            {
                "id": str(item.id),
                "redeemer_user_id": str(item.redeemer_user_id) if item.redeemer_user_id else None,
                "beneficiary_user_id": str(item.beneficiary_user_id) if item.beneficiary_user_id else None,
                "order_id": str(item.order_id) if item.order_id else None,
                "entitlement_grant_id": str(item.entitlement_grant_id) if item.entitlement_grant_id else None,
                "reward_allocation_id": str(item.reward_allocation_id) if item.reward_allocation_id else None,
                "status": item.status,
                "redeemed_at": _iso_or_none(item.redeemed_at),
            }
            for item in redemption_items
        ]
        rewards = [
            {
                "id": str(item.id),
                "reward_type": item.reward_type,
                "allocation_status": item.allocation_status,
                "beneficiary_user_id": str(item.beneficiary_user_id),
                "source_redemption_id": str(item.source_redemption_id) if item.source_redemption_id else None,
                "quantity": float(item.quantity),
                "unit": item.unit,
                "currency_code": item.currency_code,
                "created_at": _iso_or_none(item.created_at),
            }
            for item in reward_items
        ]
        resolution_events = [
            {
                "id": str(item.id),
                "result": item.result,
                "reject_reason": item.reject_reason,
                "conflict_code": item.conflict_code,
                "action_context": item.action_context,
                "surface": item.surface,
                "user_id": str(item.user_id) if item.user_id else None,
                "created_at": _iso_or_none(item.created_at),
            }
            for item in resolution_items
        ]
        lifecycle_summary = {
            "issuance_count": len(issuances),
            "touchpoint_count": len(touchpoints),
            "signup_attribution_count": len(signup_attributions),
            "redemption_count": len(redemptions),
            "reward_count": len(rewards),
            "resolution_event_count": len(resolution_events),
        }
    await db.commit()
    observe_growth_admin_lookup(
        action_context=result.action_context.value,
        code_type=result.code_type.value if result.code_type else None,
        result=result.result.value,
    )
    log_growth_code_event(
        "admin_growth.lookup",
        surface=ADMIN_GROWTH_SURFACE,
        code_type=result.code_type.value if result.code_type else None,
        action_context=result.action_context.value,
        result=result.result.value,
        reject_reason=result.reject_reason.value if result.reject_reason else None,
        growth_code_id=str(result.growth_code_id) if result.growth_code_id else None,
    )
    route_operations_total.labels(route="admin_growth_codes", action="lookup", status="success").inc()
    return AdminGrowthCodeLookupResponse(
        accepted=result.accepted,
        code_type=result.code_type,
        action_context=result.action_context,
        result=result.result,
        reject_reason=result.reject_reason,
        conflict_code=result.conflict_code,
        wrong_context_target=result.wrong_context_target,
        issuer_type=result.issuer_type,
        owner_type=result.owner_type,
        resolved_code_id=result.resolved_code_id,
        growth_code_id=result.growth_code_id,
        promo_code_id=result.promo_code_id,
        partner_code_id=result.partner_code_id,
        user_message_key=result.user_message_key,
        lifecycle_summary=lifecycle_summary,
        issuances=issuances,
        touchpoints=touchpoints,
        signup_attributions=signup_attributions,
        redemptions=redemptions,
        rewards=rewards,
        resolution_events=resolution_events,
    )


@router.get(
    "/growth-notification-deliveries",
    response_model=AdminListGrowthNotificationDeliveriesResponse,
)
async def list_growth_notification_deliveries(
    mobile_user_id: UUID | None = Query(None),
    delivery_channel: str | None = Query(None),
    delivery_status: str | None = Query(None),
    source_kind: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> AdminListGrowthNotificationDeliveriesResponse:
    delivery_repo = CustomerGrowthNotificationDeliveryRepository(db)
    mobile_user_repo = MobileUserRepository(db)
    items = await delivery_repo.list_deliveries(
        mobile_user_id=mobile_user_id,
        delivery_channel=delivery_channel,
        delivery_status=delivery_status,
        source_kind=source_kind,
        offset=offset,
        limit=limit,
    )
    total = await delivery_repo.count_deliveries(
        mobile_user_id=mobile_user_id,
        delivery_channel=delivery_channel,
        delivery_status=delivery_status,
        source_kind=source_kind,
    )

    users = await mobile_user_repo.list_by_ids(list({item.mobile_user_id for item in items}))
    users_by_id = {user.id: user for user in users}
    queue_ids = [item.notification_queue_id for item in items if item.notification_queue_id is not None]
    queues: list[NotificationQueue] = []
    if queue_ids:
        queue_rows = await db.execute(select(NotificationQueue).where(NotificationQueue.id.in_(queue_ids)))
        queues = list(queue_rows.scalars().all())
    queues_by_id = {queue.id: queue for queue in queues}

    route_operations_total.labels(
        route="admin_growth_notification_deliveries",
        action="list",
        status="success",
    ).inc()
    return AdminListGrowthNotificationDeliveriesResponse(
        items=[
            _serialize_growth_delivery(
                item,
                users_by_id=users_by_id,
                queues_by_id=queues_by_id,
            )
            for item in items
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/growth-notification-deliveries/manual",
    response_model=AdminManualGrowthNotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_growth_notification(
    body: AdminManualGrowthNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminManualGrowthNotificationResponse:
    try:
        deliveries = await CreateAdminManualGrowthNotificationUseCase(db).execute(
            mobile_user_id=body.mobile_user_id,
            title=body.title,
            message=body.message,
            route_slug=body.route_slug,
            channels={channel.strip().lower() for channel in body.channels if channel.strip()},
            created_by_admin_user_id=current_admin.id,
            locale=body.locale,
            notes=[note for note in body.notes if note.strip()],
        )
    except ValueError as exc:
        if str(exc) == "customer_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile user not found") from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await db.commit()
    users = await MobileUserRepository(db).list_by_ids([body.mobile_user_id])
    users_by_id = {user.id: user for user in users}
    queue_ids = [item.notification_queue_id for item in deliveries if item.notification_queue_id is not None]
    queues: list[NotificationQueue] = []
    if queue_ids:
        queue_rows = await db.execute(select(NotificationQueue).where(NotificationQueue.id.in_(queue_ids)))
        queues = list(queue_rows.scalars().all())
    queues_by_id = {queue.id: queue for queue in queues}

    route_operations_total.labels(
        route="admin_growth_notification_deliveries",
        action="manual_create",
        status="success",
    ).inc()
    return AdminManualGrowthNotificationResponse(
        deliveries=[
            _serialize_growth_delivery(
                item,
                users_by_id=users_by_id,
                queues_by_id=queues_by_id,
            )
            for item in deliveries
        ]
    )


@router.post(
    "/growth-notification-deliveries/{delivery_id}/resend",
    response_model=AdminGrowthNotificationDeliveryResponse,
)
async def resend_growth_notification_delivery(
    delivery_id: UUID,
    body: AdminGrowthNotificationDeliveryActionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminGrowthNotificationDeliveryResponse:
    try:
        result = await ManageCustomerGrowthNotificationDeliveryUseCase(db).resend(
            delivery_id=delivery_id,
            admin_user_id=current_admin.id,
            reason_code=body.reason_code,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "delivery_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Growth notification delivery not found",
            ) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc

    await db.commit()
    users = await MobileUserRepository(db).list_by_ids([result.delivery.mobile_user_id])
    users_by_id = {user.id: user for user in users}
    queues_by_id = {}
    if result.telegram_queue is not None:
        queues_by_id[result.telegram_queue.id] = result.telegram_queue
    route_operations_total.labels(
        route="admin_growth_notification_deliveries",
        action="resend",
        status="success",
    ).inc()
    return _serialize_growth_delivery(result.delivery, users_by_id=users_by_id, queues_by_id=queues_by_id)


@router.post(
    "/growth-notification-deliveries/{delivery_id}/pause",
    response_model=AdminGrowthNotificationDeliveryResponse,
)
async def pause_growth_notification_delivery(
    delivery_id: UUID,
    body: AdminGrowthNotificationDeliveryActionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminGrowthNotificationDeliveryResponse:
    try:
        result = await ManageCustomerGrowthNotificationDeliveryUseCase(db).pause(
            delivery_id=delivery_id,
            admin_user_id=current_admin.id,
            reason_code=body.reason_code,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "delivery_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Growth notification delivery not found",
            ) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc

    await db.commit()
    users = await MobileUserRepository(db).list_by_ids([result.delivery.mobile_user_id])
    users_by_id = {user.id: user for user in users}
    queues_by_id = {}
    if result.telegram_queue is not None:
        queues_by_id[result.telegram_queue.id] = result.telegram_queue
    route_operations_total.labels(
        route="admin_growth_notification_deliveries",
        action="pause",
        status="success",
    ).inc()
    return _serialize_growth_delivery(result.delivery, users_by_id=users_by_id, queues_by_id=queues_by_id)


@router.post(
    "/growth-notification-deliveries/{delivery_id}/revoke",
    response_model=AdminGrowthNotificationDeliveryResponse,
)
async def revoke_growth_notification_delivery(
    delivery_id: UUID,
    body: AdminGrowthNotificationDeliveryActionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminGrowthNotificationDeliveryResponse:
    try:
        result = await ManageCustomerGrowthNotificationDeliveryUseCase(db).revoke(
            delivery_id=delivery_id,
            admin_user_id=current_admin.id,
            reason_code=body.reason_code,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "delivery_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Growth notification delivery not found",
            ) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc

    await db.commit()
    users = await MobileUserRepository(db).list_by_ids([result.delivery.mobile_user_id])
    users_by_id = {user.id: user for user in users}
    queues_by_id = {}
    if result.telegram_queue is not None:
        queues_by_id[result.telegram_queue.id] = result.telegram_queue
    route_operations_total.labels(
        route="admin_growth_notification_deliveries",
        action="revoke",
        status="success",
    ).inc()
    return _serialize_growth_delivery(result.delivery, users_by_id=users_by_id, queues_by_id=queues_by_id)


@router.post(
    "/growth-notification-deliveries/{delivery_id}/resolve",
    response_model=AdminGrowthNotificationDeliveryResponse,
)
async def resolve_growth_notification_delivery(
    delivery_id: UUID,
    body: AdminGrowthNotificationDeliveryActionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminGrowthNotificationDeliveryResponse:
    try:
        result = await ManageCustomerGrowthNotificationDeliveryUseCase(db).resolve(
            delivery_id=delivery_id,
            admin_user_id=current_admin.id,
            reason_code=body.reason_code,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail in {"delivery_not_found", "customer_not_found"}:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Growth notification delivery not found",
            ) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc

    await db.commit()
    users = await MobileUserRepository(db).list_by_ids([result.delivery.mobile_user_id])
    users_by_id = {user.id: user for user in users}
    queue_ids = [
        queue_id
        for queue_id in {
            result.delivery.notification_queue_id,
            result.telegram_queue.id if result.telegram_queue is not None else None,
        }
        if queue_id is not None
    ]
    queues: list[NotificationQueue] = []
    if queue_ids:
        queue_rows = await db.execute(select(NotificationQueue).where(NotificationQueue.id.in_(queue_ids)))
        queues = list(queue_rows.scalars().all())
    queues_by_id = {queue.id: queue for queue in queues}
    route_operations_total.labels(
        route="admin_growth_notification_deliveries",
        action="resolve",
        status="success",
    ).inc()
    return _serialize_growth_delivery(result.delivery, users_by_id=users_by_id, queues_by_id=queues_by_id)


@router.get(
    "/growth-notification-deliveries/{delivery_id}",
    response_model=AdminGrowthNotificationDeliveryDetailResponse,
)
async def get_growth_notification_delivery_detail(
    delivery_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> AdminGrowthNotificationDeliveryDetailResponse:
    try:
        forensics = await GetCustomerGrowthNotificationDeliveryForensicsUseCase(db).execute(
            delivery_id=delivery_id
        )
    except ValueError as exc:
        if str(exc) == "delivery_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Growth notification delivery not found",
            ) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    sibling_items = [forensics.delivery, *forensics.sibling_deliveries]
    users = await MobileUserRepository(db).list_by_ids(
        list({item.mobile_user_id for item in sibling_items})
    )
    users_by_id = {user.id: user for user in users}
    queue_ids = [
        item.notification_queue_id
        for item in sibling_items
        if item.notification_queue_id is not None
    ]
    if forensics.queue_snapshot is not None:
        queue_ids.append(forensics.queue_snapshot.id)
    queues: list[NotificationQueue] = []
    if queue_ids:
        queue_rows = await db.execute(select(NotificationQueue).where(NotificationQueue.id.in_(queue_ids)))
        queues = list(queue_rows.scalars().all())
    queues_by_id = {queue.id: queue for queue in queues}

    route_operations_total.labels(
        route="admin_growth_notification_deliveries",
        action="detail",
        status="success",
    ).inc()
    return _serialize_growth_notification_delivery_detail(
        forensics=forensics,
        users_by_id=users_by_id,
        queues_by_id=queues_by_id,
    )


@router.get("/growth-notification-deliveries/{delivery_id}/export")
async def export_growth_notification_delivery_detail(
    delivery_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> JSONResponse:
    try:
        forensics = await GetCustomerGrowthNotificationDeliveryForensicsUseCase(db).execute(
            delivery_id=delivery_id
        )
    except ValueError as exc:
        if str(exc) == "delivery_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Growth notification delivery not found",
            ) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    sibling_items = [forensics.delivery, *forensics.sibling_deliveries]
    users = await MobileUserRepository(db).list_by_ids(
        list({item.mobile_user_id for item in sibling_items})
    )
    users_by_id = {user.id: user for user in users}
    queue_ids = [
        item.notification_queue_id
        for item in sibling_items
        if item.notification_queue_id is not None
    ]
    if forensics.queue_snapshot is not None:
        queue_ids.append(forensics.queue_snapshot.id)
    queues: list[NotificationQueue] = []
    if queue_ids:
        queue_rows = await db.execute(select(NotificationQueue).where(NotificationQueue.id.in_(queue_ids)))
        queues = list(queue_rows.scalars().all())
    queues_by_id = {queue.id: queue for queue in queues}
    payload = _serialize_growth_notification_delivery_detail(
        forensics=forensics,
        users_by_id=users_by_id,
        queues_by_id=queues_by_id,
    )
    route_operations_total.labels(
        route="admin_growth_notification_deliveries",
        action="export",
        status="success",
    ).inc()
    return _build_growth_delivery_export_response(delivery_id=delivery_id, payload=payload)


@router.get("/gift-codes", response_model=AdminListGiftCodesResponse)
async def list_gift_codes(
    owner_user_id: UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> AdminListGiftCodesResponse:
    repo = GrowthCodeRepository(db)
    items = await ListGiftCodesUseCase(db).execute(
        owner_user_id=owner_user_id,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_codes(
        code_type="gift",
        owner_user_id=owner_user_id,
    )
    route_operations_total.labels(route="admin_gift_codes", action="list", status="success").inc()
    return AdminListGiftCodesResponse(
        items=[
            _serialize_admin_gift_code(code, policy, issuance, redemption)
            for code, policy, issuance, redemption in items
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/gift-codes/issue", response_model=AdminIssueGiftCodeResponse, status_code=status.HTTP_201_CREATED)
async def issue_gift_code(
    body: AdminIssueGiftCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminIssueGiftCodeResponse:
    owner = await MobileUserRepository(db).get_by_id(body.owner_user_id)
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile user not found")

    issued = await IssueGiftCodeUseCase(db).execute(
        owner_user_id=body.owner_user_id,
        plan_id=body.plan_id,
        issuer_type="admin",
        issuance_type="admin_manual_gift",
        recipient_hint=body.recipient_hint,
        gift_message=body.gift_message,
        issued_by_admin_id=current_admin.id,
        auth_realm_id=owner.auth_realm_id,
        reason_code=body.reason_code or "admin_manual_gift",
        admin_note=body.admin_note,
    )
    observe_growth_admin_grant(
        code_type="gift",
        admin_action_type="single_issue",
        reason_code=body.reason_code,
        result="success",
    )
    log_growth_code_event(
        "admin_growth.gift_issued",
        surface=ADMIN_GROWTH_SURFACE,
        code_type="gift",
        result="success",
        admin_action_type="single_issue",
        growth_code_id=str(issued.growth_code.id),
        owner_user_id=str(issued.growth_code.owner_user_id) if issued.growth_code.owner_user_id else None,
    )
    route_operations_total.labels(route="admin_gift_codes", action="issue", status="success").inc()
    return AdminIssueGiftCodeResponse(
        gift_code=_serialize_admin_gift_code(
            issued.growth_code,
            issued.policy,
            issued.issuance,
            None,
        ).model_copy(update={"raw_code": issued.raw_code}),
    )


@router.post(
    "/gift-code-batches/issue",
    response_model=AdminIssueGiftCodeBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def issue_gift_code_batch(
    body: AdminIssueGiftCodeBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminIssueGiftCodeBatchResponse:
    owner = await MobileUserRepository(db).get_by_id(body.owner_user_id)
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile user not found")

    issued_batch = await IssueGiftCodeUseCase(db).execute_batch(
        owner_user_id=body.owner_user_id,
        plan_id=body.plan_id,
        count=body.count,
        issuer_type="admin",
        issuance_type="admin_gift_batch",
        recipient_hint=body.recipient_hint,
        gift_message=body.gift_message,
        issued_by_admin_id=current_admin.id,
        auth_realm_id=owner.auth_realm_id,
        reason_code=body.reason_code or "admin_gift_batch",
        admin_note=body.admin_note,
    )
    observe_growth_admin_grant(
        code_type="gift",
        admin_action_type="batch_issue",
        reason_code=body.reason_code,
        result="success",
    )
    log_growth_code_event(
        "admin_growth.gift_batch_issued",
        surface=ADMIN_GROWTH_SURFACE,
        code_type="gift",
        result="success",
        admin_action_type="batch_issue",
        batch_id=str(issued_batch.batch_id),
        issued_count=len(issued_batch.items),
    )
    route_operations_total.labels(route="admin_gift_codes", action="issue_batch", status="success").inc()
    return AdminIssueGiftCodeBatchResponse(
        batch_id=issued_batch.batch_id,
        issued_count=len(issued_batch.items),
        gift_codes=[
            _serialize_admin_gift_code(
                issued.growth_code,
                issued.policy,
                issued.issuance,
                None,
            ).model_copy(update={"raw_code": issued.raw_code})
            for issued in issued_batch.items
        ],
    )
