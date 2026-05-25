"""Partner runtime observability helpers.

This module owns the partner portal runtime telemetry that should be expressed
explicitly instead of relying on generic auth or route counters:
- structured logs with trace correlation
- current span enrichment
- partner-specific Prometheus metrics
"""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from typing import Any

import structlog
from opentelemetry import trace

from src.application.use_cases.auth_realms import RealmResolution
from src.infrastructure.monitoring.partner_runtime_metrics import (
    cybervpn_partner_admin_ops_overview_requests_total,
    cybervpn_partner_application_decision_duration_seconds,
    cybervpn_partner_application_decisions_total,
    cybervpn_partner_application_drafts_created_total,
    cybervpn_partner_application_drafts_saved_total,
    cybervpn_partner_application_evidence_upload_failures_total,
    cybervpn_partner_application_evidence_uploads_total,
    cybervpn_partner_application_requested_info_total,
    cybervpn_partner_application_submissions_total,
    cybervpn_partner_application_submit_duration_seconds,
    cybervpn_partner_attribution_no_owner_total,
    cybervpn_partner_attribution_resolution_duration_seconds,
    cybervpn_partner_attribution_resolutions_total,
    cybervpn_partner_audit_events_observed_total,
    cybervpn_partner_auth_cross_realm_denied_total,
    cybervpn_partner_auth_email_verification_total,
    cybervpn_partner_auth_login_attempts_total,
    cybervpn_partner_auth_logout_total,
    cybervpn_partner_auth_mfa_challenges_total,
    cybervpn_partner_auth_mfa_failures_total,
    cybervpn_partner_auth_password_reset_requested_total,
    cybervpn_partner_auth_refresh_attempts_total,
    cybervpn_partner_auth_wrong_host_token_rejected_total,
    cybervpn_partner_bootstrap_duration_seconds,
    cybervpn_partner_bootstrap_failures_total,
    cybervpn_partner_bootstrap_requests_total,
    cybervpn_partner_case_actions_total,
    cybervpn_partner_cases_created_total,
    cybervpn_partner_frontend_api_call_duration_seconds,
    cybervpn_partner_frontend_cls_ratio,
    cybervpn_partner_frontend_fcp_seconds,
    cybervpn_partner_frontend_form_validation_errors_total,
    cybervpn_partner_frontend_inp_seconds,
    cybervpn_partner_frontend_lcp_seconds,
    cybervpn_partner_frontend_render_errors_total,
    cybervpn_partner_frontend_route_guard_blocks_total,
    cybervpn_partner_frontend_route_load_duration_seconds,
    cybervpn_partner_frontend_submit_attempts_total,
    cybervpn_partner_frontend_submit_failures_total,
    cybervpn_partner_frontend_ttfb_seconds,
    cybervpn_partner_frontend_unhandled_errors_total,
    cybervpn_partner_notification_state_changes_total,
    cybervpn_partner_notifications_generated_total,
    cybervpn_partner_outbox_events_created_total,
    cybervpn_partner_outbox_events_published_total,
    cybervpn_partner_outbox_lag_seconds,
    cybervpn_partner_outbox_publish_failures_total,
    cybervpn_partner_payout_accounts_created_total,
    cybervpn_partner_payout_accounts_verified_total,
    cybervpn_partner_payout_execution_duration_seconds,
    cybervpn_partner_payout_executions_total,
    cybervpn_partner_payout_failures_total,
    cybervpn_partner_payout_instructions_created_total,
    cybervpn_partner_payout_review_queue_items,
    cybervpn_partner_statement_close_duration_seconds,
    cybervpn_partner_statement_reopen_total,
    cybervpn_partner_statements_closed_total,
    cybervpn_partner_support_cases_open,
    cybervpn_partner_touchpoints_recorded_total,
    cybervpn_partner_touchpoints_rejected_total,
)

logger = structlog.get_logger("cybervpn.partner.runtime")

PARTNER_PORTAL_SURFACE = "partner_portal"
PARTNER_ADMIN_SURFACE = "partner_admin"
PARTNER_WORKER_SURFACE = "partner_worker"
CUSTOMER_COMMERCE_SURFACE = "customer_commerce"
PARTNER_PRINCIPAL_CLASS = "partner_operator"
PARTNER_REALM_TYPE = "partner"
ADMIN_PORTAL_SURFACE = "admin_portal"
PARTNER_PORTAL_FRONTEND_SURFACE = "partner_portal"
ADMIN_PRINCIPAL_CLASS = "admin"
ADMIN_REALM_TYPE = "admin"


def _sanitize_label(value: str | None, *, default: str = "unknown") -> str:
    if value is None:
        return default
    normalized = value.strip()
    return normalized or default


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _current_trace_fields() -> dict[str, str]:
    span = trace.get_current_span()
    span_context = span.get_span_context()
    if not span_context or not span_context.is_valid:
        return {}
    return {
        "trace_id": format(span_context.trace_id, "032x"),
        "span_id": format(span_context.span_id, "016x"),
    }


def _set_span_attributes(attributes: dict[str, Any]) -> None:
    span = trace.get_current_span()
    if span is None or not span.is_recording():
        return
    for key, value in attributes.items():
        if value is None:
            continue
        span.set_attribute(key, value)


def bind_partner_runtime_context(
    *,
    surface: str,
    realm_type: str,
    principal_class: str,
    route_group: str,
    workspace_status: str | None = None,
    lane: str | None = None,
    blocked_reason: str | None = None,
    result: str | None = None,
    error_code: str | None = None,
    review_level: str | None = None,
    decision: str | None = None,
) -> None:
    context = {
        "surface": _sanitize_label(surface, default=PARTNER_PORTAL_SURFACE),
        "realm_type": _sanitize_label(realm_type, default=PARTNER_REALM_TYPE),
        "principal_class": _sanitize_label(principal_class, default=PARTNER_PRINCIPAL_CLASS),
        "route_group": _sanitize_label(route_group),
    }
    if workspace_status is not None:
        context["workspace_status"] = _sanitize_label(workspace_status)
    if lane is not None:
        context["lane"] = _sanitize_label(lane)
    if blocked_reason is not None:
        context["blocked_reason"] = _sanitize_label(blocked_reason)
    if result is not None:
        context["result"] = _sanitize_label(result)
    if error_code is not None:
        context["error_code"] = _sanitize_label(error_code)
    if review_level is not None:
        context["review_level"] = _sanitize_label(review_level)
    if decision is not None:
        context["decision"] = _sanitize_label(decision)
    context.update(_current_trace_fields())
    structlog.contextvars.bind_contextvars(**context)
    _set_span_attributes(
        {
            "cybervpn.surface": context["surface"],
            "cybervpn.realm_type": context["realm_type"],
            "cybervpn.principal_class": context["principal_class"],
            "cybervpn.route_group": context["route_group"],
            "cybervpn.workspace_status": context.get("workspace_status"),
            "cybervpn.partner.lane": context.get("lane"),
            "cybervpn.partner.blocked_reason": context.get("blocked_reason"),
            "cybervpn.result": context.get("result"),
            "cybervpn.error_code": context.get("error_code"),
            "cybervpn.partner.review_level": context.get("review_level"),
            "cybervpn.partner.decision": context.get("decision"),
        }
    )


def bind_partner_context_from_realm(
    *,
    current_realm: RealmResolution,
    route_group: str,
    surface: str = PARTNER_PORTAL_SURFACE,
    principal_class: str = PARTNER_PRINCIPAL_CLASS,
    workspace_status: str | None = None,
    lane: str | None = None,
    blocked_reason: str | None = None,
    result: str | None = None,
    error_code: str | None = None,
    review_level: str | None = None,
    decision: str | None = None,
) -> bool:
    if current_realm.realm_type != PARTNER_REALM_TYPE:
        return False
    bind_partner_runtime_context(
        surface=surface,
        realm_type=current_realm.realm_type,
        principal_class=principal_class,
        route_group=route_group,
        workspace_status=workspace_status,
        lane=lane,
        blocked_reason=blocked_reason,
        result=result,
        error_code=error_code,
        review_level=review_level,
        decision=decision,
    )
    return True


def bind_partner_frontend_runtime_context(
    *,
    surface: str,
    route_group: str,
    workspace_status: str | None = None,
    lane: str | None = None,
    blocked_reason: str | None = None,
    result: str | None = None,
    error_code: str | None = None,
    endpoint_template: str | None = None,
    form_name: str | None = None,
    request_id: str | None = None,
    method: str | None = None,
) -> None:
    normalized_surface = _sanitize_label(surface, default=PARTNER_PORTAL_FRONTEND_SURFACE)
    bind_partner_runtime_context(
        surface=normalized_surface,
        realm_type=ADMIN_REALM_TYPE if normalized_surface == ADMIN_PORTAL_SURFACE else PARTNER_REALM_TYPE,
        principal_class=(
            ADMIN_PRINCIPAL_CLASS
            if normalized_surface == ADMIN_PORTAL_SURFACE
            else PARTNER_PRINCIPAL_CLASS
        ),
        route_group=route_group,
        workspace_status=workspace_status,
        lane=lane,
        blocked_reason=blocked_reason,
        result=result,
        error_code=error_code,
    )
    _set_span_attributes(
        {
            "cybervpn.frontend.endpoint_template": _sanitize_label(endpoint_template, default="none"),
            "cybervpn.frontend.form_name": _sanitize_label(form_name, default="none"),
            "cybervpn.frontend.request_id": _sanitize_label(request_id, default="none"),
            "cybervpn.frontend.method": _sanitize_label(method, default="none"),
        }
    )


def bind_partner_frontend_web_vital_context(
    *,
    surface: str,
    route_group: str,
    metric: str,
    rating: str,
    request_id: str | None = None,
) -> None:
    bind_partner_frontend_runtime_context(
        surface=surface,
        route_group=route_group,
        request_id=request_id,
        result=rating,
    )
    _set_span_attributes(
        {
            "cybervpn.frontend.web_vital.metric": _sanitize_label(metric, default="unknown"),
            "cybervpn.frontend.web_vital.rating": _sanitize_label(rating, default="unknown"),
        }
    )


def log_partner_runtime_event(
    event_name: str,
    *,
    level: str = "info",
    **fields: Any,
) -> None:
    method = getattr(logger, level, logger.info)
    method(event_name, event_name=event_name, **_current_trace_fields(), **fields)


def observe_partner_frontend_runtime_event(
    *,
    event: str,
    surface: str,
    route_group: str,
    duration_ms: float | None = None,
    endpoint_template: str | None = None,
    error_code: str | None = None,
    form_name: str | None = None,
    lane: str | None = None,
    method: str | None = None,
    result: str | None = None,
    workspace_status: str | None = None,
    blocked_reason: str | None = None,
) -> None:
    normalized_surface = _sanitize_label(surface, default=PARTNER_PORTAL_FRONTEND_SURFACE)
    normalized_route_group = _sanitize_label(route_group)
    normalized_error_code = _sanitize_label(error_code, default="none")
    normalized_result = _sanitize_label(result, default="none")

    if event == "route_load" and duration_ms is not None:
        cybervpn_partner_frontend_route_load_duration_seconds.labels(
            surface=normalized_surface,
            route_group=normalized_route_group,
        ).observe(max(duration_ms / 1000.0, 0.0))
        return

    if event == "api_call" and duration_ms is not None:
        cybervpn_partner_frontend_api_call_duration_seconds.labels(
            surface=normalized_surface,
            route_group=normalized_route_group,
            method=_sanitize_label(method, default="unknown"),
            endpoint_template=_sanitize_label(endpoint_template, default="none"),
            result=normalized_result,
            error_code=normalized_error_code,
        ).observe(max(duration_ms / 1000.0, 0.0))
        return

    if event == "route_guard_block":
        cybervpn_partner_frontend_route_guard_blocks_total.labels(
            surface=normalized_surface,
            route_group=normalized_route_group,
            blocked_reason=_sanitize_label(blocked_reason, default="unknown"),
            workspace_status=_sanitize_label(workspace_status, default="none"),
            lane=_sanitize_label(lane, default="none"),
        ).inc()
        return

    if event == "form_validation_error":
        cybervpn_partner_frontend_form_validation_errors_total.labels(
            surface=normalized_surface,
            route_group=normalized_route_group,
            form_name=_sanitize_label(form_name, default="unknown"),
            error_code=normalized_error_code,
        ).inc()
        return

    if event == "submit_attempt":
        cybervpn_partner_frontend_submit_attempts_total.labels(
            surface=normalized_surface,
            route_group=normalized_route_group,
            form_name=_sanitize_label(form_name, default="unknown"),
            result=normalized_result,
        ).inc()
        return

    if event == "submit_failure":
        cybervpn_partner_frontend_submit_failures_total.labels(
            surface=normalized_surface,
            route_group=normalized_route_group,
            form_name=_sanitize_label(form_name, default="unknown"),
            error_code=normalized_error_code,
        ).inc()
        return

    if event == "unhandled_error":
        cybervpn_partner_frontend_unhandled_errors_total.labels(
            surface=normalized_surface,
            route_group=normalized_route_group,
            error_code=normalized_error_code,
        ).inc()
        return

    if event == "render_error":
        cybervpn_partner_frontend_render_errors_total.labels(
            surface=normalized_surface,
            route_group=normalized_route_group,
            error_code=normalized_error_code,
        ).inc()


def observe_partner_frontend_web_vital(
    *,
    surface: str,
    route_group: str,
    metric: str,
    rating: str,
    value: float,
) -> None:
    normalized_surface = _sanitize_label(surface, default=PARTNER_PORTAL_FRONTEND_SURFACE)
    normalized_route_group = _sanitize_label(route_group)
    normalized_rating = _sanitize_label(rating, default="unknown")
    normalized_value = max(value, 0.0)

    if metric == "cls":
        cybervpn_partner_frontend_cls_ratio.labels(
            surface=normalized_surface,
            route_group=normalized_route_group,
            rating=normalized_rating,
        ).observe(normalized_value)
        return

    duration_seconds = normalized_value / 1000.0
    if metric == "lcp":
        cybervpn_partner_frontend_lcp_seconds.labels(
            surface=normalized_surface,
            route_group=normalized_route_group,
            rating=normalized_rating,
        ).observe(duration_seconds)
        return

    if metric == "fcp":
        cybervpn_partner_frontend_fcp_seconds.labels(
            surface=normalized_surface,
            route_group=normalized_route_group,
            rating=normalized_rating,
        ).observe(duration_seconds)
        return

    if metric == "inp":
        cybervpn_partner_frontend_inp_seconds.labels(
            surface=normalized_surface,
            route_group=normalized_route_group,
            rating=normalized_rating,
        ).observe(duration_seconds)
        return

    if metric == "ttfb":
        cybervpn_partner_frontend_ttfb_seconds.labels(
            surface=normalized_surface,
            route_group=normalized_route_group,
            rating=normalized_rating,
        ).observe(duration_seconds)


def partner_runtime_timer() -> float:
    return perf_counter()


def observe_partner_auth_login(*, result: str, reason: str = "none") -> None:
    cybervpn_partner_auth_login_attempts_total.labels(
        surface=PARTNER_PORTAL_SURFACE,
        realm_type=PARTNER_REALM_TYPE,
        principal_class=PARTNER_PRINCIPAL_CLASS,
        result=_sanitize_label(result),
        reason=_sanitize_label(reason, default="none"),
    ).inc()


def observe_partner_auth_refresh(*, result: str, reason: str = "none") -> None:
    cybervpn_partner_auth_refresh_attempts_total.labels(
        surface=PARTNER_PORTAL_SURFACE,
        realm_type=PARTNER_REALM_TYPE,
        principal_class=PARTNER_PRINCIPAL_CLASS,
        result=_sanitize_label(result),
        reason=_sanitize_label(reason, default="none"),
    ).inc()


def observe_partner_auth_logout(*, result: str, reason: str = "none") -> None:
    cybervpn_partner_auth_logout_total.labels(
        surface=PARTNER_PORTAL_SURFACE,
        realm_type=PARTNER_REALM_TYPE,
        principal_class=PARTNER_PRINCIPAL_CLASS,
        result=_sanitize_label(result),
        reason=_sanitize_label(reason, default="none"),
    ).inc()


def observe_partner_password_reset_requested(*, result: str = "success") -> None:
    cybervpn_partner_auth_password_reset_requested_total.labels(
        surface=PARTNER_PORTAL_SURFACE,
        realm_type=PARTNER_REALM_TYPE,
        principal_class=PARTNER_PRINCIPAL_CLASS,
        result=_sanitize_label(result),
    ).inc()


def observe_partner_email_verification(*, result: str, reason: str = "none") -> None:
    cybervpn_partner_auth_email_verification_total.labels(
        surface=PARTNER_PORTAL_SURFACE,
        realm_type=PARTNER_REALM_TYPE,
        principal_class=PARTNER_PRINCIPAL_CLASS,
        result=_sanitize_label(result),
        reason=_sanitize_label(reason, default="none"),
    ).inc()


def observe_partner_mfa_challenge(*, result: str, reason: str = "none") -> None:
    cybervpn_partner_auth_mfa_challenges_total.labels(
        surface=PARTNER_PORTAL_SURFACE,
        realm_type=PARTNER_REALM_TYPE,
        principal_class=PARTNER_PRINCIPAL_CLASS,
        result=_sanitize_label(result),
        reason=_sanitize_label(reason, default="none"),
    ).inc()


def observe_partner_mfa_failure(*, reason: str) -> None:
    cybervpn_partner_auth_mfa_failures_total.labels(
        surface=PARTNER_PORTAL_SURFACE,
        realm_type=PARTNER_REALM_TYPE,
        principal_class=PARTNER_PRINCIPAL_CLASS,
        reason=_sanitize_label(reason),
    ).inc()


def observe_partner_cross_realm_denied(*, reason: str) -> None:
    cybervpn_partner_auth_cross_realm_denied_total.labels(
        surface=PARTNER_PORTAL_SURFACE,
        realm_type=PARTNER_REALM_TYPE,
        principal_class=PARTNER_PRINCIPAL_CLASS,
        reason=_sanitize_label(reason),
    ).inc()


def observe_partner_wrong_host_token_rejected(*, reason: str) -> None:
    cybervpn_partner_auth_wrong_host_token_rejected_total.labels(
        surface=PARTNER_PORTAL_SURFACE,
        realm_type=PARTNER_REALM_TYPE,
        principal_class=PARTNER_PRINCIPAL_CLASS,
        reason=_sanitize_label(reason),
    ).inc()


def observe_partner_bootstrap(
    *,
    duration_seconds: float,
    workspace_status: str,
    result: str,
    reason: str | None = None,
) -> None:
    labels = {
        "surface": PARTNER_PORTAL_SURFACE,
        "realm_type": PARTNER_REALM_TYPE,
        "principal_class": PARTNER_PRINCIPAL_CLASS,
        "workspace_status": _sanitize_label(workspace_status, default="none"),
        "result": _sanitize_label(result),
    }
    cybervpn_partner_bootstrap_requests_total.labels(**labels).inc()
    cybervpn_partner_bootstrap_duration_seconds.labels(**labels).observe(duration_seconds)
    if reason:
        cybervpn_partner_bootstrap_failures_total.labels(
            surface=PARTNER_PORTAL_SURFACE,
            realm_type=PARTNER_REALM_TYPE,
            principal_class=PARTNER_PRINCIPAL_CLASS,
            reason=_sanitize_label(reason),
        ).inc()


def _application_lane(lane: str | None) -> str:
    return _sanitize_label(lane, default="unassigned")


def observe_partner_application_draft_created(
    *,
    lane: str | None,
    workspace_status: str,
    result: str = "success",
) -> None:
    cybervpn_partner_application_drafts_created_total.labels(
        surface=PARTNER_PORTAL_SURFACE,
        lane=_application_lane(lane),
        workspace_status=_sanitize_label(workspace_status),
        result=_sanitize_label(result),
    ).inc()


def observe_partner_application_draft_saved(
    *,
    lane: str | None,
    workspace_status: str,
    result: str = "success",
) -> None:
    cybervpn_partner_application_drafts_saved_total.labels(
        surface=PARTNER_PORTAL_SURFACE,
        lane=_application_lane(lane),
        workspace_status=_sanitize_label(workspace_status),
        result=_sanitize_label(result),
    ).inc()


def observe_partner_application_submission(
    *,
    surface: str,
    lane: str | None,
    workspace_status: str,
    result: str,
    duration_seconds: float,
    reason: str = "none",
) -> None:
    labels = {
        "surface": _sanitize_label(surface),
        "lane": _application_lane(lane),
        "workspace_status": _sanitize_label(workspace_status),
        "result": _sanitize_label(result),
    }
    cybervpn_partner_application_submissions_total.labels(
        reason=_sanitize_label(reason, default="none"),
        **labels,
    ).inc()
    cybervpn_partner_application_submit_duration_seconds.labels(**labels).observe(duration_seconds)


def observe_partner_application_requested_info(
    *,
    lane: str | None,
    workspace_status: str,
    review_level: str,
    result: str = "success",
) -> None:
    cybervpn_partner_application_requested_info_total.labels(
        surface=PARTNER_ADMIN_SURFACE,
        lane=_application_lane(lane),
        workspace_status=_sanitize_label(workspace_status),
        review_level=_sanitize_label(review_level),
        result=_sanitize_label(result),
    ).inc()


def observe_partner_application_evidence_upload(
    *,
    lane: str | None,
    workspace_status: str,
    result: str,
    reason: str | None = None,
) -> None:
    if result == "success":
        cybervpn_partner_application_evidence_uploads_total.labels(
            surface=PARTNER_PORTAL_SURFACE,
            lane=_application_lane(lane),
            workspace_status=_sanitize_label(workspace_status),
            result="success",
        ).inc()
        return
    cybervpn_partner_application_evidence_upload_failures_total.labels(
        surface=PARTNER_PORTAL_SURFACE,
        lane=_application_lane(lane),
        workspace_status=_sanitize_label(workspace_status),
        reason=_sanitize_label(reason, default="unknown"),
    ).inc()


def observe_partner_application_decision(
    *,
    decision: str,
    lane: str | None,
    workspace_status: str,
    review_level: str,
    result: str,
    reason: str,
    submitted_at: datetime | None,
    decided_at: datetime | None = None,
) -> None:
    labels = {
        "surface": PARTNER_ADMIN_SURFACE,
        "lane": _application_lane(lane),
        "workspace_status": _sanitize_label(workspace_status),
        "decision": _sanitize_label(decision),
        "review_level": _sanitize_label(review_level),
        "result": _sanitize_label(result),
    }
    cybervpn_partner_application_decisions_total.labels(
        reason=_sanitize_label(reason, default="none"),
        **labels,
    ).inc()
    if submitted_at is None:
        return
    resolved_decided_at = _ensure_aware_utc(decided_at or datetime.now(UTC))
    duration_seconds = max((resolved_decided_at - _ensure_aware_utc(submitted_at)).total_seconds(), 0.0)
    cybervpn_partner_application_decision_duration_seconds.labels(
        surface=labels["surface"],
        lane=labels["lane"],
        decision=labels["decision"],
        review_level=labels["review_level"],
        result=labels["result"],
    ).observe(duration_seconds)


def observe_partner_notification_generated(
    *,
    surface: str,
    notification_type: str,
    result: str = "success",
) -> None:
    cybervpn_partner_notifications_generated_total.labels(
        surface=_sanitize_label(surface),
        notification_type=_sanitize_label(notification_type),
        result=_sanitize_label(result),
    ).inc()


def observe_partner_notification_state_change(
    *,
    surface: str,
    notification_type: str,
    action: str,
    result: str = "success",
) -> None:
    cybervpn_partner_notification_state_changes_total.labels(
        surface=_sanitize_label(surface),
        notification_type=_sanitize_label(notification_type),
        action=_sanitize_label(action),
        result=_sanitize_label(result),
    ).inc()


def observe_partner_case_created(
    *,
    surface: str,
    case_type: str,
    result: str = "success",
) -> None:
    cybervpn_partner_cases_created_total.labels(
        surface=_sanitize_label(surface),
        case_type=_sanitize_label(case_type),
        result=_sanitize_label(result),
    ).inc()


def observe_partner_case_action(
    *,
    surface: str,
    case_type: str,
    action: str,
    result: str = "success",
) -> None:
    cybervpn_partner_case_actions_total.labels(
        surface=_sanitize_label(surface),
        case_type=_sanitize_label(case_type),
        action=_sanitize_label(action),
        result=_sanitize_label(result),
    ).inc()


def observe_partner_admin_ops_overview(
    *,
    workspace_status: str,
    open_cases: int,
    waiting_on_ops_cases: int,
    payout_review_queue: list[Any],
    recent_audit_events: list[Any],
    result: str = "success",
) -> None:
    normalized_surface = PARTNER_ADMIN_SURFACE
    normalized_status = _sanitize_label(workspace_status, default="unknown")
    cybervpn_partner_admin_ops_overview_requests_total.labels(
        surface=normalized_surface,
        workspace_status=normalized_status,
        result=_sanitize_label(result),
    ).inc()
    cybervpn_partner_support_cases_open.labels(
        surface=normalized_surface,
        case_status="open",
    ).set(max(open_cases, 0))
    cybervpn_partner_support_cases_open.labels(
        surface=normalized_surface,
        case_status="waiting_on_ops",
    ).set(max(waiting_on_ops_cases, 0))

    queue_counts: dict[tuple[str, str], int] = {}
    for item in payout_review_queue:
        kind = _sanitize_label(getattr(item, "kind", None), default="unknown")
        status = _sanitize_label(getattr(item, "status", None), default="unknown")
        queue_counts[(kind, status)] = queue_counts.get((kind, status), 0) + 1
    if not queue_counts:
        cybervpn_partner_payout_review_queue_items.labels(
            surface=normalized_surface,
            kind="none",
            status="empty",
        ).set(0)
    for (kind, status), count in queue_counts.items():
        cybervpn_partner_payout_review_queue_items.labels(
            surface=normalized_surface,
            kind=kind,
            status=status,
        ).set(count)

    for item in recent_audit_events:
        action_kind = _sanitize_label(getattr(item, "action_kind", None), default="unknown")
        cybervpn_partner_audit_events_observed_total.labels(
            surface=normalized_surface,
            action_kind=action_kind,
            result="observed",
        ).inc()


def observe_partner_statement_closed(
    *,
    surface: str,
    settlement_state: str,
    result: str,
    opened_at: datetime | None,
    closed_at: datetime | None = None,
) -> None:
    cybervpn_partner_statements_closed_total.labels(
        surface=_sanitize_label(surface),
        settlement_state=_sanitize_label(settlement_state),
        result=_sanitize_label(result),
    ).inc()
    if opened_at is None:
        return
    resolved_closed_at = _ensure_aware_utc(closed_at or datetime.now(UTC))
    duration_seconds = max((resolved_closed_at - _ensure_aware_utc(opened_at)).total_seconds(), 0.0)
    cybervpn_partner_statement_close_duration_seconds.labels(
        surface=_sanitize_label(surface),
        result=_sanitize_label(result),
    ).observe(duration_seconds)


def observe_partner_statement_reopened(
    *,
    surface: str,
    result: str = "success",
) -> None:
    cybervpn_partner_statement_reopen_total.labels(
        surface=_sanitize_label(surface),
        result=_sanitize_label(result),
    ).inc()


def observe_partner_payout_account_created(
    *,
    surface: str,
    payout_rail: str,
    result: str = "success",
) -> None:
    cybervpn_partner_payout_accounts_created_total.labels(
        surface=_sanitize_label(surface),
        payout_rail=_sanitize_label(payout_rail),
        result=_sanitize_label(result),
    ).inc()


def observe_partner_payout_account_verified(
    *,
    surface: str,
    payout_rail: str,
    result: str = "success",
) -> None:
    cybervpn_partner_payout_accounts_verified_total.labels(
        surface=_sanitize_label(surface),
        payout_rail=_sanitize_label(payout_rail),
        result=_sanitize_label(result),
    ).inc()


def observe_partner_payout_instruction_created(
    *,
    surface: str,
    payout_state: str,
    result: str,
) -> None:
    cybervpn_partner_payout_instructions_created_total.labels(
        surface=_sanitize_label(surface),
        payout_state=_sanitize_label(payout_state),
        result=_sanitize_label(result),
    ).inc()


def observe_partner_payout_execution(
    *,
    surface: str,
    payout_state: str,
    result: str,
    started_at: datetime | None,
    finished_at: datetime | None = None,
) -> None:
    labels = {
        "surface": _sanitize_label(surface),
        "payout_state": _sanitize_label(payout_state),
        "result": _sanitize_label(result),
    }
    cybervpn_partner_payout_executions_total.labels(**labels).inc()
    if started_at is None:
        return
    resolved_finished_at = _ensure_aware_utc(finished_at or datetime.now(UTC))
    duration_seconds = max((resolved_finished_at - _ensure_aware_utc(started_at)).total_seconds(), 0.0)
    cybervpn_partner_payout_execution_duration_seconds.labels(**labels).observe(duration_seconds)


def observe_partner_payout_failure(
    *,
    surface: str,
    payout_state: str,
    reason: str,
) -> None:
    cybervpn_partner_payout_failures_total.labels(
        surface=_sanitize_label(surface),
        payout_state=_sanitize_label(payout_state),
        reason=_sanitize_label(reason),
    ).inc()


def observe_partner_touchpoint_recorded(
    *,
    surface: str,
    touchpoint_type: str,
    result: str = "success",
) -> None:
    cybervpn_partner_touchpoints_recorded_total.labels(
        surface=_sanitize_label(surface),
        touchpoint_type=_sanitize_label(touchpoint_type),
        result=_sanitize_label(result),
    ).inc()


def observe_partner_touchpoint_rejected(
    *,
    surface: str,
    touchpoint_type: str,
    reason: str,
) -> None:
    cybervpn_partner_touchpoints_rejected_total.labels(
        surface=_sanitize_label(surface),
        touchpoint_type=_sanitize_label(touchpoint_type),
        reason=_sanitize_label(reason),
    ).inc()


def observe_partner_attribution_resolution(
    *,
    surface: str,
    owner_type: str,
    owner_source: str,
    result: str,
    reason: str,
    duration_seconds: float,
) -> None:
    normalized_surface = _sanitize_label(surface)
    normalized_owner_type = _sanitize_label(owner_type)
    normalized_result = _sanitize_label(result)
    cybervpn_partner_attribution_resolutions_total.labels(
        surface=normalized_surface,
        owner_type=normalized_owner_type,
        owner_source=_sanitize_label(owner_source),
        result=normalized_result,
        reason=_sanitize_label(reason, default="none"),
    ).inc()
    cybervpn_partner_attribution_resolution_duration_seconds.labels(
        surface=normalized_surface,
        owner_type=normalized_owner_type,
        result=normalized_result,
    ).observe(max(duration_seconds, 0.0))
    if normalized_owner_type == "none":
        cybervpn_partner_attribution_no_owner_total.labels(
            surface=normalized_surface,
            result=normalized_result,
        ).inc()


def observe_partner_outbox_event_created(
    *,
    event_type: str,
    aggregate_type: str,
    result: str = "success",
) -> None:
    cybervpn_partner_outbox_events_created_total.labels(
        event_type=_sanitize_label(event_type),
        aggregate_type=_sanitize_label(aggregate_type),
        result=_sanitize_label(result),
    ).inc()


def observe_partner_outbox_event_published(
    *,
    event_type: str,
    consumer_name: str,
    result: str,
    lag_seconds: float | None,
) -> None:
    labels = {
        "event_type": _sanitize_label(event_type),
        "consumer_name": _sanitize_label(consumer_name),
        "result": _sanitize_label(result),
    }
    cybervpn_partner_outbox_events_published_total.labels(**labels).inc()
    if lag_seconds is not None:
        cybervpn_partner_outbox_lag_seconds.labels(**labels).observe(max(lag_seconds, 0.0))


def observe_partner_outbox_publish_failure(
    *,
    event_type: str,
    consumer_name: str,
    result: str = "failure",
    lag_seconds: float | None = None,
) -> None:
    labels = {
        "event_type": _sanitize_label(event_type),
        "consumer_name": _sanitize_label(consumer_name),
        "result": _sanitize_label(result),
    }
    cybervpn_partner_outbox_publish_failures_total.labels(**labels).inc()
    if lag_seconds is not None:
        cybervpn_partner_outbox_lag_seconds.labels(**labels).observe(max(lag_seconds, 0.0))
