"""Prometheus metrics for customer growth codes and rewards."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

cybervpn_growth_code_resolution_total = Counter(
    "cybervpn_growth_code_resolution_total",
    "Growth code resolution attempts by type, context, and result.",
    ("code_type", "action_context", "surface", "result", "reject_reason"),
)

cybervpn_growth_code_resolution_duration_seconds = Histogram(
    "cybervpn_growth_code_resolution_duration_seconds",
    "Growth code resolution latency in seconds.",
    ("code_type", "action_context", "surface", "result"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

cybervpn_growth_code_redemptions_total = Counter(
    "cybervpn_growth_code_redemptions_total",
    "Growth code redemption transitions.",
    ("code_type", "surface", "result"),
)

cybervpn_growth_code_redemption_duration_seconds = Histogram(
    "cybervpn_growth_code_redemption_duration_seconds",
    "Growth code redemption latency in seconds.",
    ("code_type", "surface", "result"),
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

cybervpn_growth_code_reservations_active = Gauge(
    "cybervpn_growth_code_reservations_active",
    "Current active growth code reservations observed by this process.",
    ("code_type", "surface"),
)

cybervpn_growth_code_reservation_expirations_total = Counter(
    "cybervpn_growth_code_reservation_expirations_total",
    "Expired growth code reservations.",
    ("code_type", "surface", "reason_code"),
)

cybervpn_invites_issued_total = Counter(
    "cybervpn_invites_issued_total",
    "Issued invite codes observed in the customer growth lifecycle.",
    ("source_type", "surface", "result"),
)

cybervpn_invites_redeemed_total = Counter(
    "cybervpn_invites_redeemed_total",
    "Redeemed invite codes.",
    ("source_type", "surface", "result"),
)

cybervpn_referral_rewards_created_total = Counter(
    "cybervpn_referral_rewards_created_total",
    "Referral reward allocations created.",
    ("reward_status", "surface", "result"),
)

cybervpn_referral_rewards_available_transitions_total = Counter(
    "cybervpn_referral_rewards_available_transitions_total",
    "Referral reward allocations that became available.",
    ("surface", "result"),
)

cybervpn_referral_rewards_reversed_total = Counter(
    "cybervpn_referral_rewards_reversed_total",
    "Referral reward allocations reversed.",
    ("surface", "reason_code"),
)

cybervpn_referral_available_credit_usd = Gauge(
    "cybervpn_referral_available_credit_usd",
    "Referral credit amount created as immediately available USD credit by this process.",
    ("surface",),
)

cybervpn_promo_codes_applied_total = Counter(
    "cybervpn_promo_codes_applied_total",
    "Promo codes applied to committed orders.",
    ("surface", "result"),
)

cybervpn_promo_rejections_total = Counter(
    "cybervpn_promo_rejections_total",
    "Rejected or conflicted promo attempts.",
    ("surface", "reject_reason"),
)

cybervpn_gift_codes_issued_total = Counter(
    "cybervpn_gift_codes_issued_total",
    "Gift codes issued through purchase or admin flows.",
    ("issuer_type", "surface", "result"),
)

cybervpn_gift_codes_redeemed_total = Counter(
    "cybervpn_gift_codes_redeemed_total",
    "Redeemed gift codes.",
    ("surface", "result"),
)

cybervpn_gift_redemption_failures_total = Counter(
    "cybervpn_gift_redemption_failures_total",
    "Gift redemption failures.",
    ("surface", "reason_code"),
)

cybervpn_growth_admin_code_grants_total = Counter(
    "cybervpn_growth_admin_code_grants_total",
    "Admin-issued growth code grants.",
    ("code_type", "admin_action_type", "reason_code", "result"),
)

cybervpn_growth_admin_code_lookup_total = Counter(
    "cybervpn_growth_admin_code_lookup_total",
    "Admin growth code lookup requests.",
    ("action_context", "code_type", "result"),
)

cybervpn_growth_notification_customer_recovery_requests_total = Counter(
    "cybervpn_growth_notification_customer_recovery_requests_total",
    "Customer-triggered recovery requests for growth notification deliveries.",
    ("delivery_channel", "troubleshooting_state", "surface", "result"),
)

cybervpn_growth_notification_support_escalations_total = Counter(
    "cybervpn_growth_notification_support_escalations_total",
    "Customer-triggered support escalations for growth notification deliveries.",
    ("delivery_channel", "troubleshooting_state", "escalation_channel", "surface", "result"),
)

cybervpn_growth_notification_repairs_completed_total = Counter(
    "cybervpn_growth_notification_repairs_completed_total",
    "Repair actions that completed for blocked growth notification deliveries.",
    ("delivery_channel", "repair_trigger", "surface", "result"),
)

cybervpn_growth_notification_support_resolutions_total = Counter(
    "cybervpn_growth_notification_support_resolutions_total",
    "Admin or support resolutions that closed growth notification escalations.",
    ("delivery_channel", "reason_code", "surface", "result"),
)

cybervpn_growth_notification_deliveries_recovered_total = Counter(
    "cybervpn_growth_notification_deliveries_recovered_total",
    "Growth notification deliveries re-armed or restored after repair.",
    ("delivery_channel", "recovery_kind", "surface", "result"),
)

cybervpn_growth_reporting_refresh_runs_total = Counter(
    "cybervpn_growth_reporting_refresh_runs_total",
    "Growth reporting refresh attempts by trigger and result.",
    ("trigger_kind", "result"),
)

cybervpn_growth_reporting_refresh_duration_seconds = Histogram(
    "cybervpn_growth_reporting_refresh_duration_seconds",
    "Growth reporting refresh duration in seconds.",
    ("trigger_kind", "result"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

cybervpn_growth_reporting_refresh_age_seconds = Gauge(
    "cybervpn_growth_reporting_refresh_age_seconds",
    "Age in seconds since the latest successful growth reporting refresh.",
)

cybervpn_growth_reporting_last_attempt_unixtime = Gauge(
    "cybervpn_growth_reporting_last_attempt_unixtime",
    "Unix timestamp of the latest growth reporting refresh attempt.",
)

cybervpn_growth_reporting_last_success_unixtime = Gauge(
    "cybervpn_growth_reporting_last_success_unixtime",
    "Unix timestamp of the latest successful growth reporting refresh.",
)

cybervpn_growth_reporting_rows_written = Gauge(
    "cybervpn_growth_reporting_rows_written",
    "Rows written during the latest successful growth reporting refresh.",
)

cybervpn_growth_reporting_freshness = Gauge(
    "cybervpn_growth_reporting_freshness",
    "Growth reporting freshness state exposed as a one-hot gauge.",
    ("freshness_status",),
)

cybervpn_growth_reporting_governance_decisions_total = Counter(
    "cybervpn_growth_reporting_governance_decisions_total",
    "Growth reporting governance decisions by decision kind and result.",
    ("decision_kind", "result"),
)

cybervpn_growth_reporting_governance_subscription_coverage = Gauge(
    "cybervpn_growth_reporting_governance_subscription_coverage",
    "Current growth reporting subscription coverage posture by governance state.",
    ("coverage_state",),
)

cybervpn_growth_reporting_governance_gap_subscriptions = Gauge(
    "cybervpn_growth_reporting_governance_gap_subscriptions",
    "Current count of active growth reporting subscriptions with silent governance coverage gaps.",
)

cybervpn_growth_reporting_governance_followup_subscriptions = Gauge(
    "cybervpn_growth_reporting_governance_followup_subscriptions",
    "Current count of growth reporting subscriptions with open governance follow-up work by reason.",
    ("followup_kind",),
)

cybervpn_growth_reporting_governance_followup_overdue_subscriptions = Gauge(
    "cybervpn_growth_reporting_governance_followup_overdue_subscriptions",
    "Current count of open growth reporting governance follow-up items that are overdue.",
)

cybervpn_growth_reporting_governance_followup_actions_total = Counter(
    "cybervpn_growth_reporting_governance_followup_actions_total",
    "Growth reporting governance follow-up actions by action kind and result.",
    ("action_kind", "result"),
)
