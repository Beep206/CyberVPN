"""Growth-code observability helpers."""

from __future__ import annotations

from typing import Any

import structlog
from opentelemetry import trace

from src.infrastructure.monitoring.growth_code_metrics import (
    cybervpn_gift_codes_issued_total,
    cybervpn_gift_codes_redeemed_total,
    cybervpn_gift_redemption_failures_total,
    cybervpn_growth_admin_code_grants_total,
    cybervpn_growth_admin_code_lookup_total,
    cybervpn_growth_code_redemption_duration_seconds,
    cybervpn_growth_code_redemptions_total,
    cybervpn_growth_code_reservation_expirations_total,
    cybervpn_growth_code_reservations_active,
    cybervpn_growth_code_resolution_duration_seconds,
    cybervpn_growth_code_resolution_total,
    cybervpn_growth_notification_customer_recovery_requests_total,
    cybervpn_growth_notification_deliveries_recovered_total,
    cybervpn_growth_notification_repairs_completed_total,
    cybervpn_growth_notification_support_escalations_total,
    cybervpn_growth_notification_support_resolutions_total,
    cybervpn_growth_reporting_freshness,
    cybervpn_growth_reporting_governance_decisions_total,
    cybervpn_growth_reporting_governance_followup_actions_total,
    cybervpn_growth_reporting_governance_followup_overdue_subscriptions,
    cybervpn_growth_reporting_governance_followup_subscriptions,
    cybervpn_growth_reporting_governance_gap_subscriptions,
    cybervpn_growth_reporting_governance_subscription_coverage,
    cybervpn_growth_reporting_last_attempt_unixtime,
    cybervpn_growth_reporting_last_success_unixtime,
    cybervpn_growth_reporting_refresh_age_seconds,
    cybervpn_growth_reporting_refresh_duration_seconds,
    cybervpn_growth_reporting_refresh_runs_total,
    cybervpn_growth_reporting_rows_written,
    cybervpn_invites_issued_total,
    cybervpn_invites_redeemed_total,
    cybervpn_promo_codes_applied_total,
    cybervpn_promo_rejections_total,
    cybervpn_referral_available_credit_usd,
    cybervpn_referral_rewards_available_transitions_total,
    cybervpn_referral_rewards_created_total,
    cybervpn_referral_rewards_reversed_total,
)

logger = structlog.get_logger("cybervpn.growth.codes")

CUSTOMER_COMMERCE_SURFACE = "customer_commerce"
CUSTOMER_REDEEM_SURFACE = "customer_redeem"
CUSTOMER_ACCOUNT_SURFACE = "customer_account"
ADMIN_GROWTH_SURFACE = "admin_growth"
GROWTH_WORKER_SURFACE = "growth_worker"


def _sanitize_label(value: str | None, *, default: str = "none") -> str:
    if value is None:
        return default
    normalized = value.strip().lower().replace(" ", "_")
    return normalized or default


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


def log_growth_code_event(
    event_name: str,
    *,
    surface: str,
    code_type: str | None = None,
    action_context: str | None = None,
    result: str | None = None,
    reject_reason: str | None = None,
    reward_type: str | None = None,
    admin_action_type: str | None = None,
    **fields: Any,
) -> None:
    payload = {
        "surface": _sanitize_label(surface, default=CUSTOMER_COMMERCE_SURFACE),
        "code_type": _sanitize_label(code_type),
        "action_context": _sanitize_label(action_context),
        "result": _sanitize_label(result),
        "reject_reason": _sanitize_label(reject_reason),
        "reward_type": _sanitize_label(reward_type),
        "admin_action_type": _sanitize_label(admin_action_type),
    }
    payload.update(_current_trace_fields())
    payload.update({key: value for key, value in fields.items() if value is not None})
    _set_span_attributes(
        {
            "cybervpn.growth.surface": payload["surface"],
            "cybervpn.growth.code_type": payload["code_type"],
            "cybervpn.growth.action_context": payload["action_context"],
            "cybervpn.growth.result": payload["result"],
            "cybervpn.growth.reject_reason": payload["reject_reason"],
            "cybervpn.growth.reward_type": payload["reward_type"],
            "cybervpn.growth.admin_action_type": payload["admin_action_type"],
        }
    )
    logger.info(event_name, **payload)


def observe_growth_code_resolution(
    *,
    code_type: str | None,
    action_context: str,
    surface: str,
    result: str,
    reject_reason: str | None = None,
) -> None:
    normalized_code_type = _sanitize_label(code_type)
    normalized_action_context = _sanitize_label(action_context)
    normalized_surface = _sanitize_label(surface, default=CUSTOMER_COMMERCE_SURFACE)
    normalized_result = _sanitize_label(result)
    normalized_reason = _sanitize_label(reject_reason)
    cybervpn_growth_code_resolution_total.labels(
        code_type=normalized_code_type,
        action_context=normalized_action_context,
        surface=normalized_surface,
        result=normalized_result,
        reject_reason=normalized_reason,
    ).inc()
    if normalized_code_type == "promo" and normalized_result in {"rejected", "conflicted", "blocked_by_risk"}:
        cybervpn_promo_rejections_total.labels(
            surface=normalized_surface,
            reject_reason=normalized_reason,
        ).inc()


def observe_growth_code_resolution_duration(
    *,
    code_type: str | None,
    action_context: str,
    surface: str,
    result: str,
    duration_seconds: float,
) -> None:
    cybervpn_growth_code_resolution_duration_seconds.labels(
        code_type=_sanitize_label(code_type),
        action_context=_sanitize_label(action_context),
        surface=_sanitize_label(surface, default=CUSTOMER_COMMERCE_SURFACE),
        result=_sanitize_label(result),
    ).observe(max(duration_seconds, 0.0))


def observe_growth_code_redemption(
    *,
    code_type: str,
    surface: str,
    result: str,
) -> None:
    normalized_code_type = _sanitize_label(code_type)
    normalized_surface = _sanitize_label(surface, default=CUSTOMER_REDEEM_SURFACE)
    normalized_result = _sanitize_label(result)
    cybervpn_growth_code_redemptions_total.labels(
        code_type=normalized_code_type,
        surface=normalized_surface,
        result=normalized_result,
    ).inc()
    if normalized_code_type == "gift":
        cybervpn_gift_codes_redeemed_total.labels(surface=normalized_surface, result=normalized_result).inc()


def observe_growth_code_redemption_duration(
    *,
    code_type: str,
    surface: str,
    result: str,
    duration_seconds: float,
) -> None:
    cybervpn_growth_code_redemption_duration_seconds.labels(
        code_type=_sanitize_label(code_type),
        surface=_sanitize_label(surface, default=CUSTOMER_REDEEM_SURFACE),
        result=_sanitize_label(result),
    ).observe(max(duration_seconds, 0.0))


def adjust_growth_code_reservations_active(
    *,
    code_type: str,
    surface: str,
    delta: int,
) -> None:
    metric = cybervpn_growth_code_reservations_active.labels(
        code_type=_sanitize_label(code_type),
        surface=_sanitize_label(surface, default=CUSTOMER_COMMERCE_SURFACE),
    )
    if delta > 0:
        metric.inc(delta)
    elif delta < 0:
        metric.dec(abs(delta))


def observe_growth_code_reservation_expiration(
    *,
    code_type: str,
    surface: str,
    reason_code: str,
) -> None:
    cybervpn_growth_code_reservation_expirations_total.labels(
        code_type=_sanitize_label(code_type),
        surface=_sanitize_label(surface, default=CUSTOMER_COMMERCE_SURFACE),
        reason_code=_sanitize_label(reason_code),
    ).inc()


def observe_growth_code_issue(
    *,
    code_type: str,
    issuer_type: str,
    surface: str,
    result: str,
    source_type: str | None = None,
) -> None:
    normalized_code_type = _sanitize_label(code_type)
    normalized_issuer_type = _sanitize_label(issuer_type)
    normalized_surface = _sanitize_label(surface)
    normalized_result = _sanitize_label(result)
    if normalized_code_type == "gift":
        cybervpn_gift_codes_issued_total.labels(
            issuer_type=normalized_issuer_type,
            surface=normalized_surface,
            result=normalized_result,
        ).inc()
    if normalized_code_type == "invite":
        cybervpn_invites_issued_total.labels(
            source_type=_sanitize_label(source_type or issuer_type),
            surface=normalized_surface,
            result=normalized_result,
        ).inc()


def observe_invite_redeemed(
    *,
    source_type: str,
    surface: str,
    result: str,
) -> None:
    cybervpn_invites_redeemed_total.labels(
        source_type=_sanitize_label(source_type),
        surface=_sanitize_label(surface, default=CUSTOMER_REDEEM_SURFACE),
        result=_sanitize_label(result),
    ).inc()


def observe_promo_applied(*, surface: str, result: str) -> None:
    cybervpn_promo_codes_applied_total.labels(
        surface=_sanitize_label(surface, default=CUSTOMER_COMMERCE_SURFACE),
        result=_sanitize_label(result),
    ).inc()


def observe_gift_redemption_failure(*, surface: str, reason_code: str) -> None:
    cybervpn_gift_redemption_failures_total.labels(
        surface=_sanitize_label(surface, default=CUSTOMER_REDEEM_SURFACE),
        reason_code=_sanitize_label(reason_code),
    ).inc()


def observe_growth_reward_created(
    *,
    reward_type: str,
    reward_status: str,
    surface: str,
    quantity: float | int,
    currency_code: str | None = None,
) -> None:
    normalized_reward_type = _sanitize_label(reward_type)
    normalized_status = _sanitize_label(reward_status)
    normalized_surface = _sanitize_label(surface, default=GROWTH_WORKER_SURFACE)
    if normalized_reward_type == "referral_credit":
        cybervpn_referral_rewards_created_total.labels(
            reward_status=normalized_status,
            surface=normalized_surface,
            result="success",
        ).inc()
        if normalized_status == "available":
            cybervpn_referral_rewards_available_transitions_total.labels(
                surface=normalized_surface,
                result="success",
            ).inc()
            if _sanitize_label(currency_code, default="usd") == "usd":
                cybervpn_referral_available_credit_usd.labels(surface=normalized_surface).inc(float(quantity))


def observe_growth_reward_reversed(
    *,
    reward_type: str,
    surface: str,
    reason_code: str,
    quantity: float | int | None = None,
    currency_code: str | None = None,
) -> None:
    if _sanitize_label(reward_type) != "referral_credit":
        return
    normalized_surface = _sanitize_label(surface, default=GROWTH_WORKER_SURFACE)
    cybervpn_referral_rewards_reversed_total.labels(
        surface=normalized_surface,
        reason_code=_sanitize_label(reason_code),
    ).inc()
    if quantity is not None and _sanitize_label(currency_code, default="usd") == "usd":
        cybervpn_referral_available_credit_usd.labels(surface=normalized_surface).dec(float(quantity))


def observe_growth_admin_lookup(
    *,
    action_context: str,
    code_type: str | None,
    result: str,
) -> None:
    cybervpn_growth_admin_code_lookup_total.labels(
        action_context=_sanitize_label(action_context),
        code_type=_sanitize_label(code_type),
        result=_sanitize_label(result),
    ).inc()


def observe_growth_admin_grant(
    *,
    code_type: str,
    admin_action_type: str,
    reason_code: str | None,
    result: str,
) -> None:
    cybervpn_growth_admin_code_grants_total.labels(
        code_type=_sanitize_label(code_type),
        admin_action_type=_sanitize_label(admin_action_type),
        reason_code=_sanitize_label(reason_code),
        result=_sanitize_label(result),
    ).inc()


def observe_growth_notification_customer_recovery_request(
    *,
    delivery_channel: str,
    troubleshooting_state: str,
    surface: str,
    result: str,
) -> None:
    cybervpn_growth_notification_customer_recovery_requests_total.labels(
        delivery_channel=_sanitize_label(delivery_channel),
        troubleshooting_state=_sanitize_label(troubleshooting_state),
        surface=_sanitize_label(surface, default=CUSTOMER_REDEEM_SURFACE),
        result=_sanitize_label(result),
    ).inc()


def observe_growth_notification_support_escalation(
    *,
    delivery_channel: str,
    troubleshooting_state: str,
    escalation_channel: str,
    surface: str,
    result: str,
) -> None:
    cybervpn_growth_notification_support_escalations_total.labels(
        delivery_channel=_sanitize_label(delivery_channel),
        troubleshooting_state=_sanitize_label(troubleshooting_state),
        escalation_channel=_sanitize_label(escalation_channel),
        surface=_sanitize_label(surface, default=CUSTOMER_REDEEM_SURFACE),
        result=_sanitize_label(result),
    ).inc()


def observe_growth_notification_repair_completed(
    *,
    delivery_channel: str,
    repair_trigger: str,
    surface: str,
    result: str,
) -> None:
    cybervpn_growth_notification_repairs_completed_total.labels(
        delivery_channel=_sanitize_label(delivery_channel),
        repair_trigger=_sanitize_label(repair_trigger),
        surface=_sanitize_label(surface, default=CUSTOMER_ACCOUNT_SURFACE),
        result=_sanitize_label(result),
    ).inc()


def observe_growth_notification_support_resolution(
    *,
    delivery_channel: str,
    reason_code: str | None,
    surface: str,
    result: str,
) -> None:
    cybervpn_growth_notification_support_resolutions_total.labels(
        delivery_channel=_sanitize_label(delivery_channel),
        reason_code=_sanitize_label(reason_code),
        surface=_sanitize_label(surface, default=ADMIN_GROWTH_SURFACE),
        result=_sanitize_label(result),
    ).inc()


def observe_growth_notification_delivery_recovered(
    *,
    delivery_channel: str,
    recovery_kind: str,
    surface: str,
    result: str,
) -> None:
    cybervpn_growth_notification_deliveries_recovered_total.labels(
        delivery_channel=_sanitize_label(delivery_channel),
        recovery_kind=_sanitize_label(recovery_kind),
        surface=_sanitize_label(surface, default=CUSTOMER_ACCOUNT_SURFACE),
        result=_sanitize_label(result),
    ).inc()


def observe_growth_reporting_refresh(
    *,
    trigger_kind: str,
    result: str,
    duration_seconds: float,
) -> None:
    normalized_trigger = _sanitize_label(trigger_kind, default="manual")
    normalized_result = _sanitize_label(result, default="unknown")
    cybervpn_growth_reporting_refresh_runs_total.labels(
        trigger_kind=normalized_trigger,
        result=normalized_result,
    ).inc()
    cybervpn_growth_reporting_refresh_duration_seconds.labels(
        trigger_kind=normalized_trigger,
        result=normalized_result,
    ).observe(max(duration_seconds, 0.0))


def update_growth_reporting_health_metrics(
    *,
    freshness_status: str,
    refresh_age_seconds: int | None,
    latest_attempt_at: float | None,
    latest_success_at: float | None,
    rows_written: int | None,
) -> None:
    normalized_freshness = _sanitize_label(freshness_status, default="unknown")
    for candidate in ("fresh", "stale", "failed", "never_refreshed"):
        cybervpn_growth_reporting_freshness.labels(freshness_status=candidate).set(
            1.0 if candidate == normalized_freshness else 0.0,
        )
    cybervpn_growth_reporting_refresh_age_seconds.set(float(max(refresh_age_seconds or 0, 0)))
    if latest_attempt_at is not None:
        cybervpn_growth_reporting_last_attempt_unixtime.set(float(latest_attempt_at))
    if latest_success_at is not None:
        cybervpn_growth_reporting_last_success_unixtime.set(float(latest_success_at))
    if rows_written is not None:
        cybervpn_growth_reporting_rows_written.set(float(max(rows_written, 0)))


def observe_growth_reporting_governance_decision(
    *,
    decision_kind: str,
    result: str,
) -> None:
    cybervpn_growth_reporting_governance_decisions_total.labels(
        decision_kind=_sanitize_label(decision_kind, default="unknown"),
        result=_sanitize_label(result, default="unknown"),
    ).inc()


def observe_growth_reporting_governance_followup_action(
    *,
    action_kind: str,
    result: str,
) -> None:
    cybervpn_growth_reporting_governance_followup_actions_total.labels(
        action_kind=_sanitize_label(action_kind, default="unknown"),
        result=_sanitize_label(result, default="unknown"),
    ).inc()


def update_growth_reporting_governance_metrics(
    *,
    active_healthy: int,
    delivery_suppressed: int,
    recipient_domain_blocked: int,
    failed: int,
    overdue: int,
    paused: int,
    followup_open: int = 0,
    followup_overdue: int = 0,
    followup_delivery_suppressed: int = 0,
    followup_recipient_domain_blocked: int = 0,
) -> None:
    counts = {
        "active_healthy": max(active_healthy, 0),
        "delivery_suppressed": max(delivery_suppressed, 0),
        "recipient_domain_blocked": max(recipient_domain_blocked, 0),
        "failed": max(failed, 0),
        "overdue": max(overdue, 0),
        "paused": max(paused, 0),
    }
    for coverage_state in (
        "active_healthy",
        "delivery_suppressed",
        "recipient_domain_blocked",
        "failed",
        "overdue",
        "paused",
    ):
        cybervpn_growth_reporting_governance_subscription_coverage.labels(
            coverage_state=coverage_state
        ).set(float(counts[coverage_state]))
    cybervpn_growth_reporting_governance_gap_subscriptions.set(
        float(counts["delivery_suppressed"] + counts["recipient_domain_blocked"])
    )
    for followup_kind, count in (
        ("open", max(followup_open, 0)),
        ("delivery_suppressed", max(followup_delivery_suppressed, 0)),
        ("recipient_domain_blocked", max(followup_recipient_domain_blocked, 0)),
    ):
        cybervpn_growth_reporting_governance_followup_subscriptions.labels(
            followup_kind=followup_kind,
        ).set(float(count))
    cybervpn_growth_reporting_governance_followup_overdue_subscriptions.set(
        float(max(followup_overdue, 0))
    )
