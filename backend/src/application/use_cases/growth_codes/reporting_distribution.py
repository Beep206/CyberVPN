from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.growth_codes.reporting import (
    ExportGrowthReportingOverviewUseCase,
    GrowthReportingExport,
)
from src.config import settings
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.growth_reporting_daily_rollup_model import (
    GrowthReportingDailyRollupModel,
)
from src.infrastructure.database.models.growth_reporting_delivery_model import (
    GrowthReportingDeliveryModel,
)
from src.infrastructure.database.models.growth_reporting_refresh_run_model import (
    GrowthReportingRefreshRunModel,
)
from src.infrastructure.database.models.growth_reporting_subscription_model import (
    GrowthReportingSubscriptionModel,
)
from src.infrastructure.database.repositories.growth_reporting_distribution_repo import (
    GrowthReportingDeliveryWrite,
    GrowthReportingDistributionRepository,
    GrowthReportingSubscriptionWrite,
)
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    observe_growth_reporting_governance_decision,
    observe_growth_reporting_governance_followup_action,
    update_growth_reporting_governance_metrics,
)

_DELIVERY_CHANNEL = "email"
_DEFAULT_REPORTING_LIMIT = 20
_DEFAULT_CLAIM_LIMIT = 10
_AUDIENCE_ORDER = {"finance": 0, "product": 1, "risk": 2, "ops": 3}
_ALLOWED_AUDIENCES = set(_AUDIENCE_ORDER)
_ALLOWED_CADENCES = {"daily", "weekly"}
_ALLOWED_DOMAIN_POLICIES = {"allow_any", "allowlist_only"}
_FOLLOWUP_TRACKED_STATES = {"delivery_suppressed", "recipient_domain_blocked"}
_FOLLOWUP_ACTIONS = {"resolve", "dismiss"}


@dataclass(frozen=True)
class GrowthReportingTemplateDefinition:
    key: str
    subject_prefix: str
    title: str
    intro: str
    focus_note: str


_TEMPLATE_CATALOG: dict[str, GrowthReportingTemplateDefinition] = {
    "finance_exec": GrowthReportingTemplateDefinition(
        key="finance_exec",
        subject_prefix="[CyberVPN][Growth][Finance]",
        title="Finance growth reporting digest",
        intro="Finance reporting digest is ready for review.",
        focus_note="Focus: reward availability, reversals, and discount cost posture.",
    ),
    "product_exec": GrowthReportingTemplateDefinition(
        key="product_exec",
        subject_prefix="[CyberVPN][Growth][Product]",
        title="Product growth reporting digest",
        intro="Product growth adoption digest is ready for review.",
        focus_note="Focus: issue-to-redemption flow and conversion posture by growth family.",
    ),
    "risk_exec": GrowthReportingTemplateDefinition(
        key="risk_exec",
        subject_prefix="[CyberVPN][Growth][Risk]",
        title="Risk growth reporting digest",
        intro="Risk monitoring digest is ready for review.",
        focus_note="Focus: rejection pressure, blocked rewards, and suspicious delivery posture.",
    ),
    "ops_exec": GrowthReportingTemplateDefinition(
        key="ops_exec",
        subject_prefix="[CyberVPN][Growth][Ops]",
        title="Operations growth reporting digest",
        intro="Operations delivery digest is ready for review.",
        focus_note="Focus: reporting freshness, delivery health, and recurring distribution posture.",
    ),
    "cross_function_exec": GrowthReportingTemplateDefinition(
        key="cross_function_exec",
        subject_prefix="[CyberVPN][Growth][Executive]",
        title="Customer growth reporting digest",
        intro="Cross-functional growth reporting digest is ready.",
        focus_note="Focus: headline lifecycle totals and reporting health.",
    ),
}
_DEFAULT_TEMPLATE_BY_AUDIENCE = {
    "finance": "finance_exec",
    "product": "product_exec",
    "risk": "risk_exec",
    "ops": "ops_exec",
}


@dataclass(frozen=True)
class GrowthReportingRecipientPolicySummary:
    template_key: str
    template_locale: str
    email_subject_prefix: str | None
    title_override: str | None
    recipient_domain_policy: str
    allowed_recipient_domains: list[str]
    suppressed_until: datetime | None
    suppression_reason_code: str | None


@dataclass(frozen=True)
class GrowthReportingSubscriptionSummary:
    id: str
    recipient_email: str
    recipient_name: str | None
    audience_key: str
    delivery_channel: str
    cadence: str
    report_window_days: int
    subscription_status: str
    next_delivery_at: datetime
    last_delivery_attempt_at: datetime | None
    last_success_at: datetime | None
    latest_delivery_status: str | None
    latest_delivery_reason: str | None
    health_status: str
    policy: GrowthReportingRecipientPolicySummary
    followup: GrowthReportingGovernanceFollowupSummary


@dataclass(frozen=True)
class GrowthReportingDeliverySummary:
    id: str
    subscription_id: str
    recipient_email: str
    recipient_name: str | None
    audience_key: str
    delivery_channel: str
    cadence: str
    report_window_days: int
    template_key: str
    template_locale: str
    subject_line: str
    title_line: str
    delivery_status: str
    status_reason: str | None
    freshness_status: str
    artifact_checksum: str | None
    provider_name: str | None
    provider_message_id: str | None
    failure_message: str | None
    window_start: date
    window_end: date
    planned_at: datetime
    started_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime
    can_export_artifact: bool
    policy: GrowthReportingRecipientPolicySummary


@dataclass(frozen=True)
class GrowthReportingSubscriptionList:
    items: list[GrowthReportingSubscriptionSummary]
    total: int
    overdue_count: int
    active_count: int
    retention_rollup_days: int
    retention_refresh_run_days: int
    retention_delivery_days: int


@dataclass(frozen=True)
class GrowthReportingDeliveryList:
    items: list[GrowthReportingDeliverySummary]
    total: int
    failed_count: int


@dataclass(frozen=True)
class GrowthReportingGovernanceCoverageCount:
    coverage_state: str
    count: int


@dataclass(frozen=True)
class GrowthReportingGovernanceFollowupSummary:
    status: str
    reason_code: str | None
    opened_at: datetime | None
    due_at: datetime | None
    last_notified_at: datetime | None
    resolved_at: datetime | None
    resolution_code: str | None
    is_overdue: bool
    action_required: bool


@dataclass(frozen=True)
class GrowthReportingGovernanceFollowupQueueItem:
    subscription_id: str
    recipient_email: str
    audience_key: str
    health_status: str
    followup: GrowthReportingGovernanceFollowupSummary
    next_delivery_at: datetime
    latest_delivery_status: str | None
    latest_delivery_reason: str | None


@dataclass(frozen=True)
class GrowthReportingGovernanceDecisionSummary:
    delivery_id: str
    subscription_id: str
    recipient_email: str
    audience_key: str
    template_key: str
    decision_kind: str
    status_reason: str
    created_at: datetime
    planned_at: datetime
    window_start: date
    window_end: date
    can_export_artifact: bool
    summary: str


@dataclass(frozen=True)
class GrowthReportingGovernanceAuditEventSummary:
    id: str
    action: str
    entity_id: str | None
    actor_label: str
    reason_code: str | None
    changed_fields: list[str]
    created_at: datetime


@dataclass(frozen=True)
class GrowthReportingGovernanceOverview:
    generated_at: datetime
    active_subscription_count: int
    paused_subscription_count: int
    coverage_gap_count: int
    followup_open_count: int
    followup_overdue_count: int
    coverage_counts: list[GrowthReportingGovernanceCoverageCount]
    followup_queue: list[GrowthReportingGovernanceFollowupQueueItem]
    recent_decisions: list[GrowthReportingGovernanceDecisionSummary]
    recent_audit_events: list[GrowthReportingGovernanceAuditEventSummary]
    notes: list[str]


@dataclass(frozen=True)
class GrowthReportingDeliveryDispatch:
    delivery_id: str
    recipient_email: str
    recipient_name: str | None
    audience_key: str
    delivery_channel: str
    subject: str
    title: str
    message: str
    notes: list[str]
    locale: str


@dataclass(frozen=True)
class GrowthReportingDeliveryClaimResult:
    deliveries: list[GrowthReportingDeliveryDispatch]
    claimed_count: int
    skipped_count: int
    overdue_count: int


@dataclass(frozen=True)
class GrowthReportingRetentionCleanupResult:
    rollups_deleted: int
    refresh_runs_deleted: int
    deliveries_deleted: int
    executed_at: datetime


@dataclass(frozen=True)
class GrowthReportingGovernanceFollowupProcessingResult:
    processed_at: datetime
    scanned_count: int
    opened_count: int
    reopened_count: int
    auto_resolved_count: int
    reminded_count: int
    open_count: int
    overdue_count: int


@dataclass(frozen=True)
class GrowthReportingGovernanceFollowupActionResult:
    subscription: GrowthReportingSubscriptionSummary
    action: str
    processed_at: datetime


class ListGrowthReportingSubscriptionsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GrowthReportingDistributionRepository(session)

    async def execute(self) -> GrowthReportingSubscriptionList:
        now = datetime.now(UTC)
        items = await self._repo.list_subscriptions()
        summaries = [_serialize_subscription(item, now=now) for item in items]
        overdue_count = sum(1 for item in summaries if item.health_status == "overdue")
        active_count = sum(1 for item in summaries if item.subscription_status == "active")
        return GrowthReportingSubscriptionList(
            items=sorted(
                summaries,
                key=lambda item: (
                    item.subscription_status != "active",
                    _AUDIENCE_ORDER.get(item.audience_key, 999),
                    item.next_delivery_at,
                    item.recipient_email,
                ),
            ),
            total=len(summaries),
            overdue_count=overdue_count,
            active_count=active_count,
            retention_rollup_days=settings.growth_reporting_rollup_retention_days,
            retention_refresh_run_days=settings.growth_reporting_refresh_run_retention_days,
            retention_delivery_days=settings.growth_reporting_delivery_retention_days,
        )


class CreateGrowthReportingSubscriptionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GrowthReportingDistributionRepository(session)

    async def execute(
        self,
        *,
        recipient_email: str,
        recipient_name: str | None,
        audience_key: str,
        cadence: str,
        report_window_days: int,
        template_key: str | None,
        template_locale: str,
        email_subject_prefix: str | None,
        title_override: str | None,
        recipient_domain_policy: str,
        allowed_recipient_domains: list[str] | None,
        suppressed_until: datetime | None,
        suppression_reason_code: str | None,
        created_by_admin_user_id: UUID | None,
    ) -> GrowthReportingSubscriptionSummary:
        now = datetime.now(UTC)
        resolved_email = _normalize_email(recipient_email)
        resolved_audience = _normalize_audience_key(audience_key)
        resolved_cadence = _normalize_cadence(cadence)
        resolved_template_key = _normalize_template_key(template_key, audience_key=resolved_audience)
        resolved_template_locale = _normalize_locale(template_locale)
        resolved_subject_prefix = _normalize_optional_text(email_subject_prefix)
        resolved_title_override = _normalize_optional_text(title_override, max_length=160)
        resolved_domain_policy = _normalize_domain_policy(recipient_domain_policy)
        resolved_allowed_domains = _normalize_allowed_domains(allowed_recipient_domains)
        resolved_suppressed_until = _coerce_utc(suppressed_until) if suppressed_until else None
        resolved_suppression_reason = _normalize_optional_text(suppression_reason_code, max_length=80)
        _validate_recipient_domain_policy(
            email=resolved_email,
            domain_policy=resolved_domain_policy,
            allowed_domains=resolved_allowed_domains,
        )
        model = await self._repo.create_subscription(
            GrowthReportingSubscriptionWrite(
                recipient_email=resolved_email,
                recipient_name=_normalize_optional_text(recipient_name, max_length=160),
                audience_key=resolved_audience,
                delivery_channel=_DELIVERY_CHANNEL,
                cadence=resolved_cadence,
                report_window_days=max(report_window_days, 1),
                template_key=resolved_template_key,
                template_locale=resolved_template_locale,
                email_subject_prefix=resolved_subject_prefix,
                title_override=resolved_title_override,
                recipient_domain_policy=resolved_domain_policy,
                allowed_recipient_domains=resolved_allowed_domains,
                suppressed_until=resolved_suppressed_until,
                suppression_reason_code=resolved_suppression_reason,
                subscription_status="active",
                next_delivery_at=now,
                created_by_admin_user_id=created_by_admin_user_id,
                updated_by_admin_user_id=created_by_admin_user_id,
            )
        )
        _sync_governance_followup_state(model, now=now)
        await self._session.flush()
        return _serialize_subscription(model, now=now)


class UpdateGrowthReportingSubscriptionPolicyUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GrowthReportingDistributionRepository(session)

    async def execute(
        self,
        *,
        subscription_id: UUID,
        recipient_email: str,
        recipient_name: str | None,
        audience_key: str,
        cadence: str,
        report_window_days: int,
        template_key: str | None,
        template_locale: str,
        email_subject_prefix: str | None,
        title_override: str | None,
        recipient_domain_policy: str,
        allowed_recipient_domains: list[str] | None,
        suppressed_until: datetime | None,
        suppression_reason_code: str | None,
        updated_by_admin_user_id: UUID | None,
    ) -> GrowthReportingSubscriptionSummary:
        model = await self._repo.get_subscription(subscription_id)
        if model is None:
            raise ValueError("growth_reporting_subscription_not_found")

        resolved_email = _normalize_email(recipient_email)
        resolved_audience = _normalize_audience_key(audience_key)
        resolved_cadence = _normalize_cadence(cadence)
        resolved_template_key = _normalize_template_key(template_key, audience_key=resolved_audience)
        resolved_template_locale = _normalize_locale(template_locale)
        resolved_subject_prefix = _normalize_optional_text(email_subject_prefix)
        resolved_title_override = _normalize_optional_text(title_override, max_length=160)
        resolved_domain_policy = _normalize_domain_policy(recipient_domain_policy)
        resolved_allowed_domains = _normalize_allowed_domains(allowed_recipient_domains)
        resolved_suppressed_until = _coerce_utc(suppressed_until) if suppressed_until else None
        resolved_suppression_reason = _normalize_optional_text(suppression_reason_code, max_length=80)
        _validate_recipient_domain_policy(
            email=resolved_email,
            domain_policy=resolved_domain_policy,
            allowed_domains=resolved_allowed_domains,
        )

        model.recipient_email = resolved_email
        model.recipient_name = _normalize_optional_text(recipient_name, max_length=160)
        model.audience_key = resolved_audience
        model.cadence = resolved_cadence
        model.report_window_days = max(report_window_days, 1)
        model.template_key = resolved_template_key
        model.template_locale = resolved_template_locale
        model.email_subject_prefix = resolved_subject_prefix
        model.title_override = resolved_title_override
        model.recipient_domain_policy = resolved_domain_policy
        model.allowed_recipient_domains = list(resolved_allowed_domains)
        model.suppressed_until = resolved_suppressed_until
        model.suppression_reason_code = resolved_suppression_reason
        model.updated_by_admin_user_id = updated_by_admin_user_id
        now = datetime.now(UTC)
        _sync_governance_followup_state(model, now=now)
        await self._session.flush()
        return _serialize_subscription(model, now=now)


class UpdateGrowthReportingSubscriptionStatusUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GrowthReportingDistributionRepository(session)

    async def execute(
        self,
        *,
        subscription_id: UUID,
        subscription_status: str,
        updated_by_admin_user_id: UUID | None,
    ) -> GrowthReportingSubscriptionSummary:
        model = await self._repo.get_subscription(subscription_id)
        if model is None:
            raise ValueError("growth_reporting_subscription_not_found")
        model.subscription_status = subscription_status
        model.updated_by_admin_user_id = updated_by_admin_user_id
        now = datetime.now(UTC)
        if subscription_status == "active" and _coerce_utc(model.next_delivery_at) < now:
            model.next_delivery_at = now
        _sync_governance_followup_state(model, now=now)
        await self._session.flush()
        return _serialize_subscription(model, now=now)


class ListGrowthReportingDeliveriesUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = GrowthReportingDistributionRepository(session)

    async def execute(self, *, limit: int = _DEFAULT_REPORTING_LIMIT) -> GrowthReportingDeliveryList:
        items = await self._repo.list_deliveries(limit=max(1, min(limit, 100)))
        summaries = [_serialize_delivery(item) for item in items]
        return GrowthReportingDeliveryList(
            items=summaries,
            total=len(summaries),
            failed_count=sum(1 for item in summaries if item.delivery_status == "failed"),
        )


class GetGrowthReportingGovernanceOverviewUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GrowthReportingDistributionRepository(session)

    async def execute(
        self,
        *,
        delivery_limit: int = 12,
        audit_limit: int = 12,
    ) -> GrowthReportingGovernanceOverview:
        now = datetime.now(UTC)
        subscriptions = await self._repo.list_subscriptions()
        deliveries = await self._repo.list_deliveries(limit=max(delivery_limit * 4, 40))
        audit_rows = await self._list_recent_audit_rows(limit=max(audit_limit, 1))

        coverage_counts_map = _build_governance_coverage_counts(subscriptions, now=now)
        followup_counts = _build_governance_followup_metrics(subscriptions, now=now)
        update_growth_reporting_governance_metrics(
            **coverage_counts_map,
            followup_open=followup_counts["followup_open"],
            followup_overdue=followup_counts["followup_overdue"],
            followup_delivery_suppressed=followup_counts["followup_delivery_suppressed"],
            followup_recipient_domain_blocked=followup_counts["followup_recipient_domain_blocked"],
        )
        followup_summaries = [_followup_summary_from_subscription(item, now=now) for item in subscriptions]
        followup_queue = [
            GrowthReportingGovernanceFollowupQueueItem(
                subscription_id=str(item.id),
                recipient_email=item.recipient_email,
                audience_key=item.audience_key,
                health_status=_serialize_subscription(item, now=now).health_status,
                followup=followup_summary,
                next_delivery_at=_coerce_utc(item.next_delivery_at),
                latest_delivery_status=item.latest_delivery_status,
                latest_delivery_reason=item.latest_delivery_reason,
            )
            for item, followup_summary in zip(subscriptions, followup_summaries, strict=False)
            if followup_summary.status == "open"
        ]

        coverage_counts = [
            GrowthReportingGovernanceCoverageCount(coverage_state=key, count=value)
            for key, value in (
                ("active_healthy", coverage_counts_map["active_healthy"]),
                ("delivery_suppressed", coverage_counts_map["delivery_suppressed"]),
                ("recipient_domain_blocked", coverage_counts_map["recipient_domain_blocked"]),
                ("failed", coverage_counts_map["failed"]),
                ("overdue", coverage_counts_map["overdue"]),
                ("paused", coverage_counts_map["paused"]),
            )
        ]

        recent_decisions = [
            _serialize_governance_decision(item)
            for item in deliveries
            if item.status_reason in {"delivery_suppressed", "recipient_domain_blocked"}
        ][:delivery_limit]
        recent_audit_events = [
            _serialize_governance_audit_event(audit_row, actor)
            for audit_row, actor in audit_rows[:audit_limit]
        ]
        coverage_gap_count = (
            coverage_counts_map["delivery_suppressed"] + coverage_counts_map["recipient_domain_blocked"]
        )
        followup_open_count = sum(1 for item in followup_summaries if item.status == "open")
        followup_overdue_count = sum(1 for item in followup_summaries if item.status == "open" and item.is_overdue)
        notes = _build_governance_notes(
            coverage_counts_map=coverage_counts_map,
            recent_decisions=recent_decisions,
            followup_open_count=followup_open_count,
            followup_overdue_count=followup_overdue_count,
        )
        return GrowthReportingGovernanceOverview(
            generated_at=now,
            active_subscription_count=sum(
                1 for item in subscriptions if item.subscription_status == "active"
            ),
            paused_subscription_count=sum(
                1 for item in subscriptions if item.subscription_status != "active"
            ),
            coverage_gap_count=coverage_gap_count,
            followup_open_count=followup_open_count,
            followup_overdue_count=followup_overdue_count,
            coverage_counts=coverage_counts,
            followup_queue=sorted(
                followup_queue,
                key=lambda item: (
                    not item.followup.is_overdue,
                    item.followup.due_at or datetime.max.replace(tzinfo=UTC),
                    item.recipient_email,
                ),
            )[:delivery_limit],
            recent_decisions=recent_decisions,
            recent_audit_events=recent_audit_events,
            notes=notes,
        )

    async def _list_recent_audit_rows(
        self,
        *,
        limit: int,
    ) -> list[tuple[AuditLog, AdminUserModel | None]]:
        result = await self._session.execute(
            select(AuditLog, AdminUserModel)
            .outerjoin(AdminUserModel, AdminUserModel.id == AuditLog.admin_id)
            .where(AuditLog.entity_type == "growth_reporting_subscription")
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return [(audit_log, actor) for audit_log, actor in result.all()]


class ExportGrowthReportingDeliveryArtifactUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = GrowthReportingDistributionRepository(session)

    async def execute(self, *, delivery_id: UUID) -> tuple[GrowthReportingDeliverySummary, dict[str, Any], str]:
        model = await self._repo.get_delivery(delivery_id)
        if model is None:
            raise ValueError("growth_reporting_delivery_not_found")
        summary = _serialize_delivery(model)
        filename = (
            f"growth-reporting-delivery-{summary.audience_key}-"
            f"{summary.window_start.isoformat()}-{summary.window_end.isoformat()}.json"
        )
        return summary, dict(model.artifact_payload or {}), filename


class ExportGrowthReportingGovernanceSnapshotUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GrowthReportingDistributionRepository(session)

    async def execute(
        self,
        *,
        delivery_limit: int = 25,
        audit_limit: int = 25,
    ) -> tuple[GrowthReportingGovernanceOverview, dict[str, Any], str]:
        overview = await GetGrowthReportingGovernanceOverviewUseCase(self._session).execute(
            delivery_limit=delivery_limit,
            audit_limit=audit_limit,
        )
        subscriptions = await self._repo.list_subscriptions()
        snapshot = {
            "generated_at": overview.generated_at.isoformat(),
            "coverage": {
                "active_subscription_count": overview.active_subscription_count,
                "paused_subscription_count": overview.paused_subscription_count,
                "coverage_gap_count": overview.coverage_gap_count,
                "followup_open_count": overview.followup_open_count,
                "followup_overdue_count": overview.followup_overdue_count,
                "counts": [
                    {
                        "coverage_state": item.coverage_state,
                        "count": item.count,
                    }
                    for item in overview.coverage_counts
                ],
                "notes": list(overview.notes),
            },
            "followup_queue": [
                {
                    "subscription_id": item.subscription_id,
                    "recipient_email": item.recipient_email,
                    "audience_key": item.audience_key,
                    "health_status": item.health_status,
                    "next_delivery_at": item.next_delivery_at.isoformat(),
                    "latest_delivery_status": item.latest_delivery_status,
                    "latest_delivery_reason": item.latest_delivery_reason,
                    "followup": {
                        "status": item.followup.status,
                        "reason_code": item.followup.reason_code,
                        "opened_at": item.followup.opened_at.isoformat() if item.followup.opened_at else None,
                        "due_at": item.followup.due_at.isoformat() if item.followup.due_at else None,
                        "last_notified_at": item.followup.last_notified_at.isoformat()
                        if item.followup.last_notified_at
                        else None,
                        "resolved_at": item.followup.resolved_at.isoformat() if item.followup.resolved_at else None,
                        "resolution_code": item.followup.resolution_code,
                        "is_overdue": item.followup.is_overdue,
                        "action_required": item.followup.action_required,
                    },
                }
                for item in overview.followup_queue
            ],
            "recent_decisions": [
                {
                    "delivery_id": item.delivery_id,
                    "subscription_id": item.subscription_id,
                    "recipient_email": item.recipient_email,
                    "audience_key": item.audience_key,
                    "template_key": item.template_key,
                    "decision_kind": item.decision_kind,
                    "status_reason": item.status_reason,
                    "created_at": item.created_at.isoformat(),
                    "planned_at": item.planned_at.isoformat(),
                    "window_start": item.window_start.isoformat(),
                    "window_end": item.window_end.isoformat(),
                    "can_export_artifact": item.can_export_artifact,
                    "summary": item.summary,
                }
                for item in overview.recent_decisions
            ],
            "recent_audit_events": [
                {
                    "id": item.id,
                    "action": item.action,
                    "entity_id": item.entity_id,
                    "actor_label": item.actor_label,
                    "reason_code": item.reason_code,
                    "changed_fields": list(item.changed_fields),
                    "created_at": item.created_at.isoformat(),
                }
                for item in overview.recent_audit_events
            ],
            "subscriptions": [
                {
                    "id": str(item.id),
                    "recipient_email": item.recipient_email,
                    "audience_key": item.audience_key,
                    "subscription_status": item.subscription_status,
                    "health_status": _governance_state_for_subscription(item, now=overview.generated_at),
                    "next_delivery_at": _coerce_utc(item.next_delivery_at).isoformat(),
                    "latest_delivery_status": item.latest_delivery_status,
                    "latest_delivery_reason": item.latest_delivery_reason,
                    "policy": {
                        "template_key": item.template_key,
                        "template_locale": item.template_locale,
                        "recipient_domain_policy": item.recipient_domain_policy,
                        "allowed_recipient_domains": list(item.allowed_recipient_domains or []),
                        "suppressed_until": _coerce_utc(item.suppressed_until).isoformat()
                        if item.suppressed_until
                        else None,
                        "suppression_reason_code": item.suppression_reason_code,
                    },
                }
                for item in subscriptions
            ],
        }
        filename = f"growth-reporting-governance-{overview.generated_at.date().isoformat()}.json"
        return overview, snapshot, filename


class ClaimDueGrowthReportingDeliveriesUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GrowthReportingDistributionRepository(session)

    async def execute(self, *, limit: int = _DEFAULT_CLAIM_LIMIT) -> GrowthReportingDeliveryClaimResult:
        now = datetime.now(UTC)
        due_subscriptions = await self._repo.list_due_subscriptions(now=now, limit=max(1, min(limit, 50)))
        overdue_count = await _count_overdue_subscriptions(self._session, now=now)
        deliveries: list[GrowthReportingDeliveryDispatch] = []
        skipped_count = 0

        for subscription in due_subscriptions:
            export = await ExportGrowthReportingOverviewUseCase(self._session).execute(
                window_days=subscription.report_window_days,
            )
            artifact_payload = _serialize_reporting_export_snapshot(export, subscription=subscription, generated_at=now)
            artifact_checksum = _checksum_payload(artifact_payload)
            health_status = export.overview.health.freshness_status
            policy_summary = _policy_summary_from_subscription(subscription)
            template = _resolve_template_definition(subscription.template_key, audience_key=subscription.audience_key)
            subject_line = _build_reporting_email_subject(
                subscription=subscription,
                template=template,
                window_end=export.overview.window_end,
            )
            title_line = _build_reporting_email_title(subscription=subscription, template=template)
            if health_status != "fresh":
                observe_growth_reporting_governance_decision(
                    decision_kind="reporting_unfresh",
                    result="skipped",
                )
                await self._repo.create_delivery(
                    GrowthReportingDeliveryWrite(
                        subscription_id=subscription.id,
                        recipient_email=subscription.recipient_email,
                        recipient_name=subscription.recipient_name,
                        audience_key=subscription.audience_key,
                        delivery_channel=subscription.delivery_channel,
                        cadence=subscription.cadence,
                        report_window_days=subscription.report_window_days,
                        template_key=policy_summary.template_key,
                        template_locale=policy_summary.template_locale,
                        subject_line=subject_line,
                        title_line=title_line,
                        recipient_domain_policy=policy_summary.recipient_domain_policy,
                        allowed_recipient_domains=policy_summary.allowed_recipient_domains,
                        delivery_status="skipped",
                        status_reason=f"reporting_{health_status}",
                        window_start=export.overview.window_start,
                        window_end=export.overview.window_end,
                        freshness_status=health_status,
                        artifact_checksum=artifact_checksum,
                        artifact_payload=artifact_payload,
                        planned_at=now,
                        started_at=now,
                        delivered_at=None,
                        failure_message=f"Growth reporting was {health_status} at claim time.",
                    )
                )
                subscription.latest_delivery_status = "skipped"
                subscription.latest_delivery_reason = f"reporting_{health_status}"
                subscription.last_delivery_attempt_at = now
                subscription.next_delivery_at = _advance_next_delivery_at(
                    current_due_at=subscription.next_delivery_at,
                    cadence=subscription.cadence,
                    now=now,
                )
                _sync_governance_followup_state(subscription, now=now)
                skipped_count += 1
                continue

            if policy_summary.suppressed_until and policy_summary.suppressed_until > now:
                observe_growth_reporting_governance_decision(
                    decision_kind="delivery_suppressed",
                    result="skipped",
                )
                await self._repo.create_delivery(
                    GrowthReportingDeliveryWrite(
                        subscription_id=subscription.id,
                        recipient_email=subscription.recipient_email,
                        recipient_name=subscription.recipient_name,
                        audience_key=subscription.audience_key,
                        delivery_channel=subscription.delivery_channel,
                        cadence=subscription.cadence,
                        report_window_days=subscription.report_window_days,
                        template_key=policy_summary.template_key,
                        template_locale=policy_summary.template_locale,
                        subject_line=subject_line,
                        title_line=title_line,
                        recipient_domain_policy=policy_summary.recipient_domain_policy,
                        allowed_recipient_domains=policy_summary.allowed_recipient_domains,
                        delivery_status="skipped",
                        status_reason="delivery_suppressed",
                        window_start=export.overview.window_start,
                        window_end=export.overview.window_end,
                        freshness_status=health_status,
                        artifact_checksum=artifact_checksum,
                        artifact_payload=artifact_payload,
                        planned_at=now,
                        started_at=now,
                        delivered_at=None,
                        failure_message=(
                            "Growth reporting delivery is suppressed until "
                            f"{policy_summary.suppressed_until.isoformat()}."
                        ),
                    )
                )
                subscription.latest_delivery_status = "skipped"
                subscription.latest_delivery_reason = "delivery_suppressed"
                subscription.last_delivery_attempt_at = now
                subscription.next_delivery_at = _advance_next_delivery_at(
                    current_due_at=subscription.next_delivery_at,
                    cadence=subscription.cadence,
                    now=now,
                )
                _sync_governance_followup_state(subscription, now=now)
                skipped_count += 1
                continue

            if not _is_recipient_domain_allowed(
                email=subscription.recipient_email,
                domain_policy=policy_summary.recipient_domain_policy,
                allowed_domains=policy_summary.allowed_recipient_domains,
            ):
                observe_growth_reporting_governance_decision(
                    decision_kind="recipient_domain_blocked",
                    result="skipped",
                )
                await self._repo.create_delivery(
                    GrowthReportingDeliveryWrite(
                        subscription_id=subscription.id,
                        recipient_email=subscription.recipient_email,
                        recipient_name=subscription.recipient_name,
                        audience_key=subscription.audience_key,
                        delivery_channel=subscription.delivery_channel,
                        cadence=subscription.cadence,
                        report_window_days=subscription.report_window_days,
                        template_key=policy_summary.template_key,
                        template_locale=policy_summary.template_locale,
                        subject_line=subject_line,
                        title_line=title_line,
                        recipient_domain_policy=policy_summary.recipient_domain_policy,
                        allowed_recipient_domains=policy_summary.allowed_recipient_domains,
                        delivery_status="skipped",
                        status_reason="recipient_domain_blocked",
                        window_start=export.overview.window_start,
                        window_end=export.overview.window_end,
                        freshness_status=health_status,
                        artifact_checksum=artifact_checksum,
                        artifact_payload=artifact_payload,
                        planned_at=now,
                        started_at=now,
                        delivered_at=None,
                        failure_message="Growth reporting recipient domain is blocked by policy.",
                    )
                )
                subscription.latest_delivery_status = "skipped"
                subscription.latest_delivery_reason = "recipient_domain_blocked"
                subscription.last_delivery_attempt_at = now
                subscription.next_delivery_at = _advance_next_delivery_at(
                    current_due_at=subscription.next_delivery_at,
                    cadence=subscription.cadence,
                    now=now,
                )
                _sync_governance_followup_state(subscription, now=now)
                skipped_count += 1
                continue

            delivery = await self._repo.create_delivery(
                GrowthReportingDeliveryWrite(
                    subscription_id=subscription.id,
                    recipient_email=subscription.recipient_email,
                    recipient_name=subscription.recipient_name,
                    audience_key=subscription.audience_key,
                    delivery_channel=subscription.delivery_channel,
                    cadence=subscription.cadence,
                    report_window_days=subscription.report_window_days,
                    template_key=policy_summary.template_key,
                    template_locale=policy_summary.template_locale,
                    subject_line=subject_line,
                    title_line=title_line,
                    recipient_domain_policy=policy_summary.recipient_domain_policy,
                    allowed_recipient_domains=policy_summary.allowed_recipient_domains,
                    delivery_status="processing",
                    status_reason=None,
                    window_start=export.overview.window_start,
                    window_end=export.overview.window_end,
                    freshness_status=health_status,
                    artifact_checksum=artifact_checksum,
                    artifact_payload=artifact_payload,
                    planned_at=now,
                    started_at=now,
                )
            )
            observe_growth_reporting_governance_decision(
                decision_kind="claimed",
                result="processing",
            )
            subscription.latest_delivery_status = "processing"
            subscription.latest_delivery_reason = None
            subscription.last_delivery_attempt_at = now
            subscription.next_delivery_at = _advance_next_delivery_at(
                current_due_at=subscription.next_delivery_at,
                cadence=subscription.cadence,
                now=now,
            )
            _sync_governance_followup_state(subscription, now=now)
            deliveries.append(
                GrowthReportingDeliveryDispatch(
                    delivery_id=str(delivery.id),
                    recipient_email=delivery.recipient_email,
                    recipient_name=delivery.recipient_name,
                    audience_key=delivery.audience_key,
                    delivery_channel=delivery.delivery_channel,
                    subject=delivery.subject_line,
                    title=delivery.title_line,
                    message=_build_reporting_email_message(artifact_payload, template=template),
                    notes=_build_reporting_email_notes(artifact_payload, template=template),
                    locale=delivery.template_locale,
                )
            )

        subscriptions = await self._repo.list_subscriptions()
        coverage_counts_map = _build_governance_coverage_counts(subscriptions, now=now)
        followup_counts = _build_governance_followup_metrics(subscriptions, now=now)
        update_growth_reporting_governance_metrics(
            **coverage_counts_map,
            followup_open=followup_counts["followup_open"],
            followup_overdue=followup_counts["followup_overdue"],
            followup_delivery_suppressed=followup_counts["followup_delivery_suppressed"],
            followup_recipient_domain_blocked=followup_counts["followup_recipient_domain_blocked"],
        )
        await self._session.flush()
        return GrowthReportingDeliveryClaimResult(
            deliveries=deliveries,
            claimed_count=len(deliveries),
            skipped_count=skipped_count,
            overdue_count=overdue_count,
        )


class CompleteGrowthReportingDeliveryUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GrowthReportingDistributionRepository(session)

    async def execute(
        self,
        *,
        delivery_id: UUID,
        delivery_status: str,
        provider_name: str | None,
        provider_message_id: str | None,
        failure_message: str | None,
    ) -> GrowthReportingDeliverySummary:
        delivery = await self._repo.get_delivery(delivery_id)
        if delivery is None:
            raise ValueError("growth_reporting_delivery_not_found")
        subscription = await self._repo.get_subscription(delivery.subscription_id)
        if subscription is None:
            raise ValueError("growth_reporting_subscription_not_found")

        now = datetime.now(UTC)
        delivery.delivery_status = delivery_status
        delivery.provider_name = provider_name
        delivery.provider_message_id = provider_message_id
        delivery.failure_message = failure_message
        delivery.status_reason = (
            None
            if delivery_status == "delivered"
            else (delivery.status_reason or "delivery_failed")
        )
        delivery.delivered_at = now if delivery_status == "delivered" else None

        subscription.latest_delivery_status = delivery_status
        subscription.latest_delivery_reason = delivery.status_reason if delivery_status != "delivered" else None
        if delivery_status == "delivered":
            subscription.last_success_at = now

        _sync_governance_followup_state(subscription, now=now)
        await self._session.flush()
        return _serialize_delivery(delivery)


class ProcessGrowthReportingGovernanceFollowupsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GrowthReportingDistributionRepository(session)

    async def execute(self) -> GrowthReportingGovernanceFollowupProcessingResult:
        now = datetime.now(UTC)
        subscriptions = await self._repo.list_subscriptions()
        opened_count = 0
        reopened_count = 0
        auto_resolved_count = 0
        reminded_count = 0

        for item in subscriptions:
            transition = _sync_governance_followup_state(item, now=now)
            if transition == "opened":
                opened_count += 1
                _append_governance_followup_audit_entry(
                    session=self._session,
                    action="growth_reporting.subscription.followup.opened",
                    subscription=item,
                    reason_code=item.governance_followup_reason_code,
                    now=now,
                )
            elif transition == "reopened":
                reopened_count += 1
                _append_governance_followup_audit_entry(
                    session=self._session,
                    action="growth_reporting.subscription.followup.reopened",
                    subscription=item,
                    reason_code=item.governance_followup_reason_code,
                    now=now,
                )
            elif transition == "auto_resolved":
                auto_resolved_count += 1
                _append_governance_followup_audit_entry(
                    session=self._session,
                    action="growth_reporting.subscription.followup.auto_resolved",
                    subscription=item,
                    reason_code=item.governance_followup_resolution_code,
                    now=now,
                )

            if _should_emit_followup_reminder(item, now=now):
                item.governance_followup_last_notified_at = now
                reminded_count += 1
                observe_growth_reporting_governance_followup_action(
                    action_kind="reminded",
                    result="success",
                )
                _append_governance_followup_audit_entry(
                    session=self._session,
                    action="growth_reporting.subscription.followup.reminded",
                    subscription=item,
                    reason_code=item.governance_followup_reason_code,
                    now=now,
                )

        coverage_counts_map = _build_governance_coverage_counts(subscriptions, now=now)
        followup_counts = _build_governance_followup_metrics(subscriptions, now=now)
        update_growth_reporting_governance_metrics(
            **coverage_counts_map,
            followup_open=followup_counts["followup_open"],
            followup_overdue=followup_counts["followup_overdue"],
            followup_delivery_suppressed=followup_counts["followup_delivery_suppressed"],
            followup_recipient_domain_blocked=followup_counts["followup_recipient_domain_blocked"],
        )
        await self._session.flush()
        return GrowthReportingGovernanceFollowupProcessingResult(
            processed_at=now,
            scanned_count=len(subscriptions),
            opened_count=opened_count,
            reopened_count=reopened_count,
            auto_resolved_count=auto_resolved_count,
            reminded_count=reminded_count,
            open_count=followup_counts["followup_open"],
            overdue_count=followup_counts["followup_overdue"],
        )


class UpdateGrowthReportingGovernanceFollowupUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GrowthReportingDistributionRepository(session)

    async def execute(
        self,
        *,
        subscription_id: UUID,
        action: str,
        reason_code: str | None,
        updated_by_admin_user_id: UUID | None,
    ) -> GrowthReportingGovernanceFollowupActionResult:
        if action not in _FOLLOWUP_ACTIONS:
            raise ValueError("growth_reporting_invalid_followup_action")
        model = await self._repo.get_subscription(subscription_id)
        if model is None:
            raise ValueError("growth_reporting_subscription_not_found")

        now = datetime.now(UTC)
        current_followup = _followup_summary_from_subscription(model, now=now)
        if current_followup.status != "open":
            raise ValueError("growth_reporting_followup_not_actionable")
        normalized_reason = _normalize_optional_text(reason_code, max_length=120) or f"manual_{action}"
        if action == "resolve":
            model.governance_followup_status = "resolved"
        else:
            model.governance_followup_status = "dismissed"
        model.governance_followup_reason_code = current_followup.reason_code
        model.governance_followup_opened_at = current_followup.opened_at or now
        model.governance_followup_due_at = current_followup.due_at
        model.governance_followup_resolution_code = normalized_reason
        model.governance_followup_resolved_at = now
        model.governance_followup_last_notified_at = now
        model.updated_by_admin_user_id = updated_by_admin_user_id
        observe_growth_reporting_governance_followup_action(
            action_kind=action,
            result="success",
        )
        await self._session.flush()
        return GrowthReportingGovernanceFollowupActionResult(
            subscription=_serialize_subscription(model, now=now),
            action=action,
            processed_at=now,
        )


class CleanupGrowthReportingArtifactsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GrowthReportingDistributionRepository(session)

    async def execute(self) -> GrowthReportingRetentionCleanupResult:
        now = datetime.now(UTC)
        deliveries_deleted = await self._repo.delete_old_deliveries(
            older_than=now - timedelta(days=settings.growth_reporting_delivery_retention_days),
        )
        refresh_runs_deleted = await self._delete_refresh_runs(
            older_than=now - timedelta(days=settings.growth_reporting_refresh_run_retention_days),
        )
        rollups_deleted = await self._delete_rollups(
            older_than=now.date() - timedelta(days=settings.growth_reporting_rollup_retention_days),
        )
        await self._session.flush()
        return GrowthReportingRetentionCleanupResult(
            rollups_deleted=rollups_deleted,
            refresh_runs_deleted=refresh_runs_deleted,
            deliveries_deleted=deliveries_deleted,
            executed_at=now,
        )

    async def _delete_refresh_runs(self, *, older_than: datetime) -> int:
        result = await self._session.execute(
            delete(GrowthReportingRefreshRunModel).where(
                GrowthReportingRefreshRunModel.finished_at < older_than,
            )
        )
        return int(result.rowcount or 0)

    async def _delete_rollups(self, *, older_than: date) -> int:
        result = await self._session.execute(
            delete(GrowthReportingDailyRollupModel).where(
                GrowthReportingDailyRollupModel.report_date < older_than,
            )
        )
        return int(result.rowcount or 0)


def _build_governance_coverage_counts(
    subscriptions: list[GrowthReportingSubscriptionModel],
    *,
    now: datetime,
) -> dict[str, int]:
    counts = {
        "active_healthy": 0,
        "delivery_suppressed": 0,
        "recipient_domain_blocked": 0,
        "failed": 0,
        "overdue": 0,
        "paused": 0,
    }
    for item in subscriptions:
        counts[_governance_state_for_subscription(item, now=now)] += 1
    return counts


def _build_governance_followup_metrics(
    subscriptions: list[GrowthReportingSubscriptionModel],
    *,
    now: datetime,
) -> dict[str, int]:
    counts = {
        "followup_open": 0,
        "followup_overdue": 0,
        "followup_delivery_suppressed": 0,
        "followup_recipient_domain_blocked": 0,
    }
    for item in subscriptions:
        summary = _followup_summary_from_subscription(item, now=now)
        if summary.status != "open":
            continue
        counts["followup_open"] += 1
        if summary.is_overdue:
            counts["followup_overdue"] += 1
        if summary.reason_code == "delivery_suppressed":
            counts["followup_delivery_suppressed"] += 1
        elif summary.reason_code == "recipient_domain_blocked":
            counts["followup_recipient_domain_blocked"] += 1
    return counts


def _governance_state_for_subscription(
    item: GrowthReportingSubscriptionModel,
    *,
    now: datetime,
) -> str:
    if item.subscription_status != "active":
        return "paused"
    policy = _policy_summary_from_subscription(item)
    if policy.suppressed_until and policy.suppressed_until > now:
        return "delivery_suppressed"
    if not _is_recipient_domain_allowed(
        email=item.recipient_email,
        domain_policy=policy.recipient_domain_policy,
        allowed_domains=policy.allowed_recipient_domains,
    ):
        return "recipient_domain_blocked"
    if item.latest_delivery_status == "failed":
        return "failed"
    if _coerce_utc(item.next_delivery_at) < now - _grace_period_for_cadence(item.cadence):
        return "overdue"
    return "active_healthy"


def _followup_summary_from_subscription(
    item: GrowthReportingSubscriptionModel,
    *,
    now: datetime,
) -> GrowthReportingGovernanceFollowupSummary:
    governance_state = _governance_state_for_subscription(item, now=now)
    if (item.governance_followup_status or "none") == "none" and governance_state in _FOLLOWUP_TRACKED_STATES:
        due_at = _followup_due_at_for_state(item, governance_state=governance_state, now=now)
        return GrowthReportingGovernanceFollowupSummary(
            status="open",
            reason_code=governance_state,
            opened_at=None,
            due_at=due_at,
            last_notified_at=None,
            resolved_at=None,
            resolution_code=None,
            is_overdue=due_at <= now,
            action_required=True,
        )
    due_at = _coerce_utc(item.governance_followup_due_at) if item.governance_followup_due_at else None
    opened_at = _coerce_utc(item.governance_followup_opened_at) if item.governance_followup_opened_at else None
    last_notified_at = (
        _coerce_utc(item.governance_followup_last_notified_at)
        if item.governance_followup_last_notified_at
        else None
    )
    resolved_at = _coerce_utc(item.governance_followup_resolved_at) if item.governance_followup_resolved_at else None
    status = item.governance_followup_status or "none"
    is_overdue = bool(status == "open" and due_at and due_at <= now)
    return GrowthReportingGovernanceFollowupSummary(
        status=status,
        reason_code=item.governance_followup_reason_code,
        opened_at=opened_at,
        due_at=due_at,
        last_notified_at=last_notified_at,
        resolved_at=resolved_at,
        resolution_code=item.governance_followup_resolution_code,
        is_overdue=is_overdue,
        action_required=status == "open",
    )


def _sync_governance_followup_state(
    item: GrowthReportingSubscriptionModel,
    *,
    now: datetime,
) -> str | None:
    governance_state = _governance_state_for_subscription(item, now=now)
    current_status = item.governance_followup_status or "none"
    current_reason = item.governance_followup_reason_code

    if governance_state in _FOLLOWUP_TRACKED_STATES:
        due_at = _followup_due_at_for_state(item, governance_state=governance_state, now=now)
        if current_status == "open" and current_reason == governance_state:
            item.governance_followup_due_at = due_at
            item.governance_followup_resolution_code = None
            item.governance_followup_resolved_at = None
            return None

        transition = "reopened" if current_status in {"resolved", "dismissed"} else "opened"
        item.governance_followup_status = "open"
        item.governance_followup_reason_code = governance_state
        item.governance_followup_opened_at = now
        item.governance_followup_due_at = due_at
        item.governance_followup_last_notified_at = None
        item.governance_followup_resolved_at = None
        item.governance_followup_resolution_code = None
        observe_growth_reporting_governance_followup_action(
            action_kind=transition,
            result="success",
        )
        return transition

    if current_status == "open":
        item.governance_followup_status = "resolved"
        item.governance_followup_resolution_code = "governance_gap_cleared"
        item.governance_followup_resolved_at = now
        observe_growth_reporting_governance_followup_action(
            action_kind="auto_resolved",
            result="success",
        )
        return "auto_resolved"
    return None


def _followup_due_at_for_state(
    item: GrowthReportingSubscriptionModel,
    *,
    governance_state: str,
    now: datetime,
) -> datetime:
    if governance_state == "delivery_suppressed":
        policy = _policy_summary_from_subscription(item)
        if policy.suppressed_until and policy.suppressed_until > now:
            return policy.suppressed_until + timedelta(hours=1)
        return now + timedelta(hours=1)
    if governance_state == "recipient_domain_blocked":
        return now + timedelta(hours=2)
    return now + timedelta(hours=4)


def _should_emit_followup_reminder(
    item: GrowthReportingSubscriptionModel,
    *,
    now: datetime,
) -> bool:
    summary = _followup_summary_from_subscription(item, now=now)
    if summary.status != "open" or not summary.is_overdue:
        return False
    if summary.last_notified_at is None:
        return True
    return summary.last_notified_at <= now - timedelta(hours=24)


def _append_governance_followup_audit_entry(
    *,
    session: AsyncSession,
    action: str,
    subscription: GrowthReportingSubscriptionModel,
    reason_code: str | None,
    now: datetime,
    admin_user_id: UUID | None = None,
) -> None:
    session.add(
        AuditLog(
            admin_id=admin_user_id,
            action=action,
            entity_type="growth_reporting_subscription",
            entity_id=str(subscription.id),
            old_value=None,
            new_value={
                "recipient_email": subscription.recipient_email,
                "audience_key": subscription.audience_key,
                "followup_status": subscription.governance_followup_status,
                "followup_reason_code": subscription.governance_followup_reason_code,
                "followup_due_at": subscription.governance_followup_due_at.isoformat()
                if subscription.governance_followup_due_at
                else None,
                "followup_resolution_code": subscription.governance_followup_resolution_code,
                "reason_code": reason_code,
            },
            ip_address=None,
            user_agent="growth_reporting_governance_followup_automation",
            created_at=now,
        )
    )


def _serialize_governance_decision(
    item: GrowthReportingDeliveryModel,
) -> GrowthReportingGovernanceDecisionSummary:
    decision_kind = item.status_reason or item.delivery_status
    summary = "Delivery skipped due to governance policy."
    if item.status_reason == "delivery_suppressed":
        summary = "Delivery skipped because the subscription is currently suppressed."
    elif item.status_reason == "recipient_domain_blocked":
        summary = "Delivery skipped because the recipient domain is blocked by policy."
    return GrowthReportingGovernanceDecisionSummary(
        delivery_id=str(item.id),
        subscription_id=str(item.subscription_id),
        recipient_email=item.recipient_email,
        audience_key=item.audience_key,
        template_key=item.template_key,
        decision_kind=decision_kind,
        status_reason=item.status_reason or item.delivery_status,
        created_at=_coerce_utc(item.created_at),
        planned_at=_coerce_utc(item.planned_at),
        window_start=item.window_start,
        window_end=item.window_end,
        can_export_artifact=bool(item.artifact_payload),
        summary=summary,
    )


def _serialize_governance_audit_event(
    audit_row: AuditLog,
    actor: AdminUserModel | None,
) -> GrowthReportingGovernanceAuditEventSummary:
    old_value = dict(audit_row.old_value or {})
    new_value = dict(audit_row.new_value or {})
    actor_label = "System"
    if actor is not None:
        actor_label = actor.display_name or actor.login or actor.email or str(actor.id)
    return GrowthReportingGovernanceAuditEventSummary(
        id=str(audit_row.id),
        action=audit_row.action,
        entity_id=audit_row.entity_id,
        actor_label=actor_label,
        reason_code=_normalize_optional_text(new_value.get("reason_code"), max_length=120),
        changed_fields=_diff_growth_reporting_audit_fields(old_value=old_value, new_value=new_value),
        created_at=_coerce_utc(audit_row.created_at),
    )


def _diff_growth_reporting_audit_fields(
    *,
    old_value: dict[str, Any],
    new_value: dict[str, Any],
) -> list[str]:
    changed_fields: list[str] = []
    for key in (
        "recipient_email",
        "recipient_name",
        "audience_key",
        "cadence",
        "report_window_days",
        "subscription_status",
        "health_status",
    ):
        if old_value.get(key) != new_value.get(key):
            changed_fields.append(key)
    old_policy = dict(old_value.get("policy") or {})
    new_policy = dict(new_value.get("policy") or {})
    for key in (
        "template_key",
        "template_locale",
        "email_subject_prefix",
        "title_override",
        "recipient_domain_policy",
        "allowed_recipient_domains",
        "suppressed_until",
        "suppression_reason_code",
    ):
        if old_policy.get(key) != new_policy.get(key):
            changed_fields.append(f"policy.{key}")
    old_followup = dict(old_value.get("followup") or {})
    new_followup = dict(new_value.get("followup") or {})
    for key in (
        "status",
        "reason_code",
        "opened_at",
        "due_at",
        "last_notified_at",
        "resolved_at",
        "resolution_code",
        "is_overdue",
        "action_required",
    ):
        if old_followup.get(key) != new_followup.get(key):
            changed_fields.append(f"followup.{key}")
    if not changed_fields and new_value:
        changed_fields.append("state_snapshot")
    return changed_fields


def _build_governance_notes(
    *,
    coverage_counts_map: dict[str, int],
    recent_decisions: list[GrowthReportingGovernanceDecisionSummary],
    followup_open_count: int,
    followup_overdue_count: int,
) -> list[str]:
    notes: list[str] = []
    if coverage_counts_map["delivery_suppressed"] > 0:
        notes.append(
            f"{coverage_counts_map['delivery_suppressed']} active subscriptions are currently suppressed."
        )
    if coverage_counts_map["recipient_domain_blocked"] > 0:
        notes.append(
            f"{coverage_counts_map['recipient_domain_blocked']} active subscriptions are "
            "blocked by recipient domain policy."
        )
    if not notes:
        notes.append("No active reporting subscriptions are currently blocked by governance policy.")
    if followup_open_count > 0:
        notes.append(f"{followup_open_count} governance follow-up items are currently open.")
    if followup_overdue_count > 0:
        notes.append(f"{followup_overdue_count} governance follow-up items are overdue and need operator action.")
    if recent_decisions:
        notes.append(
            "Recent governance decisions captured: "
            f"{len(recent_decisions)} exportable delivery artifacts are available "
            "for forensics."
        )
    return notes


def _serialize_subscription(
    item: GrowthReportingSubscriptionModel,
    *,
    now: datetime,
) -> GrowthReportingSubscriptionSummary:
    next_delivery_at = _coerce_utc(item.next_delivery_at)
    governance_state = _governance_state_for_subscription(item, now=now)
    health_status = {
        "paused": "paused",
        "delivery_suppressed": "suppressed",
        "recipient_domain_blocked": "recipient_domain_blocked",
        "failed": "failed",
        "overdue": "overdue",
        "active_healthy": "healthy",
    }[governance_state]
    return GrowthReportingSubscriptionSummary(
        id=str(item.id),
        recipient_email=item.recipient_email,
        recipient_name=item.recipient_name,
        audience_key=item.audience_key,
        delivery_channel=item.delivery_channel,
        cadence=item.cadence,
        report_window_days=item.report_window_days,
        subscription_status=item.subscription_status,
        next_delivery_at=next_delivery_at,
        last_delivery_attempt_at=_coerce_utc(item.last_delivery_attempt_at) if item.last_delivery_attempt_at else None,
        last_success_at=_coerce_utc(item.last_success_at) if item.last_success_at else None,
        latest_delivery_status=item.latest_delivery_status,
        latest_delivery_reason=item.latest_delivery_reason,
        health_status=health_status,
        policy=_policy_summary_from_subscription(item),
        followup=_followup_summary_from_subscription(item, now=now),
    )


def _serialize_delivery(item: GrowthReportingDeliveryModel) -> GrowthReportingDeliverySummary:
    artifact_payload = dict(item.artifact_payload or {})
    delivery_template = dict(artifact_payload.get("delivery_template") or {})
    recipient_policy = dict(artifact_payload.get("recipient_policy") or {})
    return GrowthReportingDeliverySummary(
        id=str(item.id),
        subscription_id=str(item.subscription_id),
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
        planned_at=_coerce_utc(item.planned_at),
        started_at=_coerce_utc(item.started_at) if item.started_at else None,
        delivered_at=_coerce_utc(item.delivered_at) if item.delivered_at else None,
        created_at=_coerce_utc(item.created_at),
        updated_at=_coerce_utc(item.updated_at),
        can_export_artifact=bool(item.artifact_payload),
        policy=GrowthReportingRecipientPolicySummary(
            template_key=item.template_key,
            template_locale=item.template_locale,
            email_subject_prefix=_normalize_optional_text(
                delivery_template.get("email_subject_prefix"),
                max_length=120,
            ),
            title_override=_normalize_optional_text(delivery_template.get("title_override"), max_length=160),
            recipient_domain_policy=item.recipient_domain_policy,
            allowed_recipient_domains=list(item.allowed_recipient_domains or []),
            suppressed_until=_coerce_utc(
                datetime.fromisoformat(str(recipient_policy["suppressed_until"]).replace("Z", "+00:00"))
            )
            if recipient_policy.get("suppressed_until")
            else None,
            suppression_reason_code=_normalize_optional_text(
                recipient_policy.get("suppression_reason_code"),
                max_length=80,
            ),
        ),
    )


async def _count_overdue_subscriptions(session: AsyncSession, *, now: datetime) -> int:
    result = await session.execute(select(GrowthReportingSubscriptionModel))
    subscriptions = list(result.scalars().all())
    return sum(
        1
        for item in subscriptions
        if _governance_state_for_subscription(item, now=now) == "overdue"
    )


def _advance_next_delivery_at(*, current_due_at: datetime, cadence: str, now: datetime) -> datetime:
    delta = timedelta(days=1) if cadence == "daily" else timedelta(days=7)
    cursor = _coerce_utc(current_due_at)
    floor = _coerce_utc(now)
    while cursor <= floor:
        cursor += delta
    return cursor


def _grace_period_for_cadence(cadence: str) -> timedelta:
    return timedelta(hours=6) if cadence == "daily" else timedelta(days=2)


def _checksum_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _serialize_reporting_export_snapshot(
    export: GrowthReportingExport,
    *,
    subscription: GrowthReportingSubscriptionModel,
    generated_at: datetime,
) -> dict[str, Any]:
    overview = export.overview
    policy = _policy_summary_from_subscription(subscription)
    template = _resolve_template_definition(policy.template_key, audience_key=subscription.audience_key)
    subject_line = _build_reporting_email_subject(
        subscription=subscription,
        template=template,
        window_end=overview.window_end,
    )
    title_line = _build_reporting_email_title(subscription=subscription, template=template)
    return {
        "generated_at": generated_at.isoformat(),
        "audience_key": subscription.audience_key,
        "recipient_email": subscription.recipient_email,
        "delivery_template": {
            "template_key": policy.template_key,
            "template_locale": policy.template_locale,
            "subject_line": subject_line,
            "title_line": title_line,
            "email_subject_prefix": policy.email_subject_prefix,
            "title_override": policy.title_override,
        },
        "recipient_policy": {
            "recipient_domain_policy": policy.recipient_domain_policy,
            "allowed_recipient_domains": list(policy.allowed_recipient_domains),
            "suppressed_until": policy.suppressed_until.isoformat() if policy.suppressed_until else None,
            "suppression_reason_code": policy.suppression_reason_code,
        },
        "window_start": overview.window_start.isoformat(),
        "window_end": overview.window_end.isoformat(),
        "latest_rollup_date": overview.latest_rollup_date.isoformat() if overview.latest_rollup_date else None,
        "refreshed_at": overview.refreshed_at.isoformat() if overview.refreshed_at else None,
        "health": {
            "freshness_status": overview.health.freshness_status,
            "stale_reason": overview.health.stale_reason,
            "refresh_age_seconds": overview.health.refresh_age_seconds,
            "latest_attempt_at": overview.health.latest_attempt_at.isoformat()
            if overview.health.latest_attempt_at
            else None,
            "latest_success_at": overview.health.latest_success_at.isoformat()
            if overview.health.latest_success_at
            else None,
            "latest_failure_message": overview.health.latest_failure_message,
        },
        "executive_summary": {
            "total_issued": overview.executive_summary.total_issued,
            "total_redemptions": overview.executive_summary.total_redemptions,
            "total_reward_available_usd": overview.executive_summary.total_reward_available_usd,
            "total_reward_reversed_usd": overview.executive_summary.total_reward_reversed_usd,
            "resolution_acceptance_rate_pct": overview.executive_summary.resolution_acceptance_rate_pct,
            "dominant_family": overview.executive_summary.dominant_family,
            "highlights": list(overview.executive_summary.highlights),
        },
        "totals": {
            "issued_total": overview.totals.issued_total,
            "redemption_total": overview.totals.redemption_total,
            "reward_created_amount_usd": overview.totals.reward_created_amount_usd,
            "reward_available_amount_usd": overview.totals.reward_available_amount_usd,
            "reward_reversed_amount_usd": overview.totals.reward_reversed_amount_usd,
        },
        "coverage_notes": list(overview.coverage_notes),
        "raw_rows": [_json_ready(row) for row in export.raw_rows],
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, datetime):
        return _coerce_utc(value).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _policy_summary_from_subscription(
    item: GrowthReportingSubscriptionModel,
) -> GrowthReportingRecipientPolicySummary:
    return GrowthReportingRecipientPolicySummary(
        template_key=_normalize_template_key(item.template_key, audience_key=item.audience_key),
        template_locale=_normalize_locale(item.template_locale),
        email_subject_prefix=_normalize_optional_text(item.email_subject_prefix, max_length=120),
        title_override=_normalize_optional_text(item.title_override, max_length=160),
        recipient_domain_policy=_normalize_domain_policy(item.recipient_domain_policy),
        allowed_recipient_domains=_normalize_allowed_domains(item.allowed_recipient_domains),
        suppressed_until=_coerce_utc(item.suppressed_until) if item.suppressed_until else None,
        suppression_reason_code=_normalize_optional_text(item.suppression_reason_code, max_length=80),
    )


def _build_reporting_email_subject(
    *,
    subscription: GrowthReportingSubscriptionModel,
    template: GrowthReportingTemplateDefinition,
    window_end: date,
) -> str:
    prefix = _normalize_optional_text(subscription.email_subject_prefix, max_length=120) or template.subject_prefix
    return f"{prefix} {subscription.cadence.title()} digest {window_end.isoformat()}"


def _build_reporting_email_title(
    *,
    subscription: GrowthReportingSubscriptionModel,
    template: GrowthReportingTemplateDefinition,
) -> str:
    return _normalize_optional_text(subscription.title_override, max_length=160) or template.title


def _build_reporting_email_message(
    payload: dict[str, Any],
    *,
    template: GrowthReportingTemplateDefinition,
) -> str:
    summary = dict(payload.get("executive_summary") or {})
    total_issued = int(summary.get("total_issued") or 0)
    total_redemptions = int(summary.get("total_redemptions") or 0)
    available_usd = float(summary.get("total_reward_available_usd") or 0)
    dominant_family = str(summary.get("dominant_family") or "none")
    return (
        f"{template.intro} "
        f"Issued={total_issued}, redemptions={total_redemptions}, "
        f"available_rewards_usd={available_usd:.2f}, dominant_family={dominant_family}."
    )


def _build_reporting_email_notes(
    payload: dict[str, Any],
    *,
    template: GrowthReportingTemplateDefinition,
) -> list[str]:
    summary = dict(payload.get("executive_summary") or {})
    health = dict(payload.get("health") or {})
    notes = [
        template.focus_note,
        f"Window: {payload.get('window_start')} -> {payload.get('window_end')}",
        f"Freshness: {health.get('freshness_status') or 'unknown'}",
    ]
    for highlight in list(summary.get("highlights") or [])[:4]:
        if str(highlight).strip():
            notes.append(str(highlight).strip())
    return notes


def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("growth_reporting_invalid_recipient_email")
    return normalized


def _normalize_optional_text(value: str | None, *, max_length: int = 120) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized[:max_length]


def _normalize_audience_key(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in _ALLOWED_AUDIENCES:
        raise ValueError("growth_reporting_invalid_audience")
    return normalized


def _normalize_cadence(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in _ALLOWED_CADENCES:
        raise ValueError("growth_reporting_invalid_cadence")
    return normalized


def _normalize_locale(value: str | None) -> str:
    normalized = (value or "en-EN").strip()
    return normalized or "en-EN"


def _normalize_template_key(value: str | None, *, audience_key: str) -> str:
    normalized = (value or _DEFAULT_TEMPLATE_BY_AUDIENCE.get(audience_key, "cross_function_exec")).strip().lower()
    if normalized not in _TEMPLATE_CATALOG:
        raise ValueError("growth_reporting_invalid_template")
    return normalized


def _resolve_template_definition(
    template_key: str,
    *,
    audience_key: str,
) -> GrowthReportingTemplateDefinition:
    resolved_key = _normalize_template_key(template_key, audience_key=audience_key)
    return _TEMPLATE_CATALOG[resolved_key]


def _normalize_domain_policy(value: str | None) -> str:
    normalized = (value or "allow_any").strip().lower()
    if normalized not in _ALLOWED_DOMAIN_POLICIES:
        raise ValueError("growth_reporting_invalid_domain_policy")
    return normalized


def _normalize_allowed_domains(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for item in values or []:
        candidate = str(item).strip().lower()
        if not candidate:
            continue
        if candidate not in normalized:
            normalized.append(candidate)
    return normalized


def _extract_email_domain(email: str) -> str:
    if "@" not in email:
        return ""
    return email.rsplit("@", 1)[-1].strip().lower()


def _is_recipient_domain_allowed(
    *,
    email: str,
    domain_policy: str,
    allowed_domains: list[str],
) -> bool:
    if domain_policy == "allow_any":
        return True
    email_domain = _extract_email_domain(email)
    if not email_domain:
        return False
    return email_domain in set(allowed_domains)


def _validate_recipient_domain_policy(
    *,
    email: str,
    domain_policy: str,
    allowed_domains: list[str],
) -> None:
    if domain_policy == "allowlist_only" and not allowed_domains:
        raise ValueError("growth_reporting_missing_allowed_recipient_domains")
    if not _is_recipient_domain_allowed(
        email=email,
        domain_policy=domain_policy,
        allowed_domains=allowed_domains,
    ):
        raise ValueError("growth_reporting_recipient_domain_not_allowed")


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
