"""S1 support escalation runbook contract.

This module keeps the Controlled Public Beta escalation path machine-readable:
AI/bot and first-line support can route incidents to finance, ops or owner
without exposing secrets or relying only on prose in launch docs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from src.presentation.api.shared.stage1_support_ticket_path import (
    STAGE1_PRIVACY_EMAIL,
    STAGE1_REFUND_EMAIL,
    STAGE1_SUPPORT_EMAIL,
    STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
    STAGE1_SUPPORT_P0_ACK_MINUTES,
    STAGE1_SUPPORT_P1_ACK_MINUTES,
    Stage1SupportTicketCategory,
    Stage1SupportTicketDecision,
    Stage1SupportTicketPriority,
)

STAGE1_PRIMARY_ONCALL_OWNER = "@Sasha_Beep"
STAGE1_BACKUP_ONCALL_OWNER = "@Sasha_Beep"
STAGE1_PRIVATE_TELEGRAM_ALERT_CHANNEL = "-5173727789"
STAGE1_BACKUP_ALERT_EMAIL = "backup@cyber-vpn.net"


class Stage1SupportEscalationOwner(StrEnum):
    """Human or system owner for the next escalation step."""

    AI_FIRST_LINE = "ai_first_line"
    SUPPORT = "support"
    FINANCE = "finance"
    OPS = "ops"
    OWNER = "owner"


class Stage1SupportEscalationTrigger(StrEnum):
    """Stable S1 escalation triggers for support/admin/runbook use."""

    GENERAL_SUPPORT = "general_support"
    FAILED_PAYMENT = "failed_payment"
    REFUND_REQUEST = "refund_request"
    PAID_NO_ACCESS = "paid_no_access"
    PAID_NO_ACCESS_OVER_24H = "paid_no_access_over_24h"
    PROVISIONING_FAILURE = "provisioning_failure"
    REMNAWAVE_OR_NODE_OUTAGE = "remnawave_or_node_outage"
    VPN_CONNECTIVITY_INCIDENT = "vpn_connectivity_incident"
    EXPIRED_SUBSCRIPTION_STUCK = "expired_subscription_stuck"
    ACCOUNT_ACCESS_CONFLICT = "account_access_conflict"
    ACCOUNT_DELETION_REQUEST = "account_deletion_request"
    DATA_EXPORT_REQUEST = "data_export_request"
    LEGAL_ABUSE_REQUEST = "legal_abuse_request"
    EMERGENCY_KILL_SWITCH = "emergency_kill_switch"


@dataclass(frozen=True, slots=True)
class Stage1SupportEscalationRule:
    """Runbook row for a single S1 support escalation trigger."""

    trigger: Stage1SupportEscalationTrigger
    category: Stage1SupportTicketCategory
    path: tuple[Stage1SupportEscalationOwner, ...]
    target_owner: Stage1SupportEscalationOwner
    priority: Stage1SupportTicketPriority
    queue: str
    contact: str
    ack_sla_minutes: int | None
    customer_response_sla_minutes: int
    required_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    audit_required: bool = True
    alert_required: bool = False
    p0_if_unresolved_after_minutes: int | None = None
    kill_switch_allowed: bool = False

    def to_runbook_dict(self) -> dict[str, object]:
        """Serialize a safe runbook row for admin/support UI and docs."""

        return {
            "trigger": self.trigger.value,
            "category": self.category.value,
            "path": [owner.value for owner in self.path],
            "target_owner": self.target_owner.value,
            "priority": self.priority.value,
            "queue": self.queue,
            "contact": self.contact,
            "ack_sla_minutes": self.ack_sla_minutes,
            "customer_response_sla_minutes": self.customer_response_sla_minutes,
            "required_actions": list(self.required_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "audit_required": self.audit_required,
            "alert_required": self.alert_required,
            "p0_if_unresolved_after_minutes": self.p0_if_unresolved_after_minutes,
            "kill_switch_allowed": self.kill_switch_allowed,
        }


@dataclass(frozen=True, slots=True)
class Stage1SupportEscalationDecision:
    """Escalation decision tied to a support ticket reference."""

    ticket_reference: str
    rule: Stage1SupportEscalationRule

    def to_staff_note(self) -> str:
        """Render a support-safe note for admin timelines and manual queues."""

        return "\n".join(
            [
                "S1 support escalation",
                f"Ticket: {self.ticket_reference}",
                f"Trigger: {self.rule.trigger.value}",
                f"Priority: {self.rule.priority.value}",
                f"Queue: {self.rule.queue}",
                f"Target owner: {self.rule.target_owner.value}",
                f"Path: {' -> '.join(owner.value for owner in self.rule.path)}",
                f"Ack SLA minutes: {self.rule.ack_sla_minutes or 'n/a'}",
                f"Customer response SLA minutes: {self.rule.customer_response_sla_minutes}",
            ]
        )

    def to_api_dict(self) -> dict[str, object]:
        """Serialize the decision without user-provided text or provider payloads."""

        return {
            "ticket_reference": self.ticket_reference,
            **self.rule.to_runbook_dict(),
        }


COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS = (
    "do_not_request_password_or_2fa_totp",
    "do_not_request_full_card_or_cvv",
    "do_not_request_raw_qr_subscription_url_or_config",
    "do_not_disclose_provider_or_user_secrets",
)

REQUIRED_STAGE1_SUPPORT_ESCALATION_TRIGGERS = tuple(Stage1SupportEscalationTrigger)


def _base_required_actions(*extra_actions: str) -> tuple[str, ...]:
    return (
        "create_ticket_or_staff_note",
        "preserve_safe_reference",
        "use_safe_summary_only",
        "record_owner_and_next_action",
        *extra_actions,
    )


STAGE1_SUPPORT_ESCALATION_RULES: dict[Stage1SupportEscalationTrigger, Stage1SupportEscalationRule] = {
    Stage1SupportEscalationTrigger.GENERAL_SUPPORT: Stage1SupportEscalationRule(
        trigger=Stage1SupportEscalationTrigger.GENERAL_SUPPORT,
        category=Stage1SupportTicketCategory.GENERAL,
        path=(Stage1SupportEscalationOwner.AI_FIRST_LINE, Stage1SupportEscalationOwner.SUPPORT),
        target_owner=Stage1SupportEscalationOwner.SUPPORT,
        priority=Stage1SupportTicketPriority.P3,
        queue="s1_customer_support",
        contact=STAGE1_SUPPORT_EMAIL,
        ack_sla_minutes=None,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        required_actions=_base_required_actions("answer_or_route_to_specific_s1_category"),
        forbidden_actions=COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
    ),
    Stage1SupportEscalationTrigger.FAILED_PAYMENT: Stage1SupportEscalationRule(
        trigger=Stage1SupportEscalationTrigger.FAILED_PAYMENT,
        category=Stage1SupportTicketCategory.FAILED_PAYMENT,
        path=(
            Stage1SupportEscalationOwner.AI_FIRST_LINE,
            Stage1SupportEscalationOwner.SUPPORT,
            Stage1SupportEscalationOwner.FINANCE,
        ),
        target_owner=Stage1SupportEscalationOwner.FINANCE,
        priority=Stage1SupportTicketPriority.P1,
        queue="s1_payment_finance_review",
        contact=STAGE1_REFUND_EMAIL,
        ack_sla_minutes=STAGE1_SUPPORT_P1_ACK_MINUTES,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        required_actions=_base_required_actions(
            "reconcile_provider_dashboard",
            "verify_provider_final_status",
            "update_payment_attempt_review_state",
            "notify_customer_after_finance_decision",
        ),
        forbidden_actions=(
            *COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
            "do_not_mark_paid_without_provider_final_success",
            "do_not_create_vpn_access_from_user_screenshot_only",
        ),
        alert_required=True,
    ),
    Stage1SupportEscalationTrigger.REFUND_REQUEST: Stage1SupportEscalationRule(
        trigger=Stage1SupportEscalationTrigger.REFUND_REQUEST,
        category=Stage1SupportTicketCategory.REFUND_REQUEST,
        path=(
            Stage1SupportEscalationOwner.AI_FIRST_LINE,
            Stage1SupportEscalationOwner.SUPPORT,
            Stage1SupportEscalationOwner.FINANCE,
        ),
        target_owner=Stage1SupportEscalationOwner.FINANCE,
        priority=Stage1SupportTicketPriority.P1,
        queue="s1_payment_finance_review",
        contact=STAGE1_REFUND_EMAIL,
        ack_sla_minutes=STAGE1_SUPPORT_P1_ACK_MINUTES,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        required_actions=_base_required_actions(
            "check_final_refund_policy",
            "verify_payment_and_provider_refund_capability",
            "record_finance_decision",
            "notify_customer_without_guaranteeing_refund",
        ),
        forbidden_actions=(
            *COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
            "do_not_promise_guaranteed_or_automatic_refund",
            "do_not_refund_without_finance_or_owner_approval",
        ),
        alert_required=True,
    ),
    Stage1SupportEscalationTrigger.PAID_NO_ACCESS: Stage1SupportEscalationRule(
        trigger=Stage1SupportEscalationTrigger.PAID_NO_ACCESS,
        category=Stage1SupportTicketCategory.PAID_NO_ACCESS,
        path=(
            Stage1SupportEscalationOwner.AI_FIRST_LINE,
            Stage1SupportEscalationOwner.SUPPORT,
            Stage1SupportEscalationOwner.OPS,
        ),
        target_owner=Stage1SupportEscalationOwner.OPS,
        priority=Stage1SupportTicketPriority.P1,
        queue="s1_paid_no_access_review",
        contact=STAGE1_SUPPORT_EMAIL,
        ack_sla_minutes=STAGE1_SUPPORT_P1_ACK_MINUTES,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        required_actions=_base_required_actions(
            "verify_payment_is_final_success",
            "check_provisioning_state",
            "check_remnawave_user_and_subscription",
            "queue_or_retry_provisioning",
            "update_customer_until_access_or_resolution",
        ),
        forbidden_actions=(
            *COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
            "do_not_close_paid_without_access_until_resolved",
            "do_not_erase_paid_state_during_retry",
        ),
        alert_required=True,
        p0_if_unresolved_after_minutes=24 * 60,
    ),
    Stage1SupportEscalationTrigger.PAID_NO_ACCESS_OVER_24H: Stage1SupportEscalationRule(
        trigger=Stage1SupportEscalationTrigger.PAID_NO_ACCESS_OVER_24H,
        category=Stage1SupportTicketCategory.PAID_NO_ACCESS,
        path=(
            Stage1SupportEscalationOwner.SUPPORT,
            Stage1SupportEscalationOwner.OPS,
            Stage1SupportEscalationOwner.OWNER,
        ),
        target_owner=Stage1SupportEscalationOwner.OWNER,
        priority=Stage1SupportTicketPriority.P0,
        queue="s1_paid_no_access_review",
        contact=STAGE1_SUPPORT_EMAIL,
        ack_sla_minutes=STAGE1_SUPPORT_P0_ACK_MINUTES,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        required_actions=_base_required_actions(
            "open_p0_incident",
            "resolve_access_refund_or_manual_grant",
            "consider_pausing_payments_or_provisioning_if_systemic",
            "write_post_incident_note",
        ),
        forbidden_actions=(
            *COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
            "do_not_allow_unresolved_paid_no_access_older_than_24h",
        ),
        alert_required=True,
        kill_switch_allowed=True,
    ),
    Stage1SupportEscalationTrigger.PROVISIONING_FAILURE: Stage1SupportEscalationRule(
        trigger=Stage1SupportEscalationTrigger.PROVISIONING_FAILURE,
        category=Stage1SupportTicketCategory.PAID_NO_ACCESS,
        path=(
            Stage1SupportEscalationOwner.SUPPORT,
            Stage1SupportEscalationOwner.OPS,
        ),
        target_owner=Stage1SupportEscalationOwner.OPS,
        priority=Stage1SupportTicketPriority.P1,
        queue="s1_paid_no_access_review",
        contact=STAGE1_SUPPORT_EMAIL,
        ack_sla_minutes=STAGE1_SUPPORT_P1_ACK_MINUTES,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        required_actions=_base_required_actions(
            "inspect_worker_retry_state",
            "inspect_remnawave_api_status",
            "retry_or_manual_recover_after_safe_verification",
        ),
        forbidden_actions=(
            *COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
            "do_not_expose_raw_remnawave_errors_to_customer",
        ),
        alert_required=True,
        p0_if_unresolved_after_minutes=24 * 60,
    ),
    Stage1SupportEscalationTrigger.REMNAWAVE_OR_NODE_OUTAGE: Stage1SupportEscalationRule(
        trigger=Stage1SupportEscalationTrigger.REMNAWAVE_OR_NODE_OUTAGE,
        category=Stage1SupportTicketCategory.VPN_NOT_CONNECTING,
        path=(
            Stage1SupportEscalationOwner.SUPPORT,
            Stage1SupportEscalationOwner.OPS,
            Stage1SupportEscalationOwner.OWNER,
        ),
        target_owner=Stage1SupportEscalationOwner.OPS,
        priority=Stage1SupportTicketPriority.P0,
        queue="s1_ops_incident",
        contact=STAGE1_SUPPORT_EMAIL,
        ack_sla_minutes=STAGE1_SUPPORT_P0_ACK_MINUTES,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        required_actions=_base_required_actions(
            "open_p0_incident",
            "check_remnawave_control_plane_and_nodes",
            "pause_trial_payment_or_provisioning_if_needed",
            "prepare_customer_status_update",
        ),
        forbidden_actions=(
            *COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
            "do_not_claim_customer_device_issue_until_node_health_checked",
        ),
        alert_required=True,
        kill_switch_allowed=True,
    ),
    Stage1SupportEscalationTrigger.VPN_CONNECTIVITY_INCIDENT: Stage1SupportEscalationRule(
        trigger=Stage1SupportEscalationTrigger.VPN_CONNECTIVITY_INCIDENT,
        category=Stage1SupportTicketCategory.VPN_NOT_CONNECTING,
        path=(
            Stage1SupportEscalationOwner.AI_FIRST_LINE,
            Stage1SupportEscalationOwner.SUPPORT,
            Stage1SupportEscalationOwner.OPS,
        ),
        target_owner=Stage1SupportEscalationOwner.OPS,
        priority=Stage1SupportTicketPriority.P2,
        queue="s1_vpn_connectivity_support",
        contact=STAGE1_SUPPORT_EMAIL,
        ack_sla_minutes=None,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        required_actions=_base_required_actions(
            "verify_subscription_and_device_limit",
            "collect_platform_client_region_and_time",
            "check_node_health_if_multiple_reports",
            "route_to_ops_when_node_or_protocol_issue_is_suspected",
        ),
        forbidden_actions=(
            *COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
            "do_not_request_raw_config_file",
        ),
    ),
    Stage1SupportEscalationTrigger.EXPIRED_SUBSCRIPTION_STUCK: Stage1SupportEscalationRule(
        trigger=Stage1SupportEscalationTrigger.EXPIRED_SUBSCRIPTION_STUCK,
        category=Stage1SupportTicketCategory.EXPIRED_SUBSCRIPTION,
        path=(Stage1SupportEscalationOwner.AI_FIRST_LINE, Stage1SupportEscalationOwner.SUPPORT),
        target_owner=Stage1SupportEscalationOwner.SUPPORT,
        priority=Stage1SupportTicketPriority.P2,
        queue="s1_customer_support",
        contact=STAGE1_SUPPORT_EMAIL,
        ack_sla_minutes=None,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        required_actions=_base_required_actions(
            "confirm_subscription_state",
            "send_manual_renewal_path",
            "escalate_to_finance_if_payment_was_made",
            "escalate_to_ops_if_access_state_is_inconsistent",
        ),
        forbidden_actions=(
            *COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
            "do_not_promise_autoprolongation_in_s1",
        ),
    ),
    Stage1SupportEscalationTrigger.ACCOUNT_ACCESS_CONFLICT: Stage1SupportEscalationRule(
        trigger=Stage1SupportEscalationTrigger.ACCOUNT_ACCESS_CONFLICT,
        category=Stage1SupportTicketCategory.ACCOUNT_ACCESS,
        path=(
            Stage1SupportEscalationOwner.AI_FIRST_LINE,
            Stage1SupportEscalationOwner.SUPPORT,
            Stage1SupportEscalationOwner.OWNER,
        ),
        target_owner=Stage1SupportEscalationOwner.OWNER,
        priority=Stage1SupportTicketPriority.P1,
        queue="s1_owner_account_access",
        contact=STAGE1_SUPPORT_EMAIL,
        ack_sla_minutes=STAGE1_SUPPORT_P1_ACK_MINUTES,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        required_actions=_base_required_actions(
            "verify_identity_before_account_action",
            "preserve_account_link_conflict_audit",
            "block_silent_merge",
            "owner_review_before_manual_merge_or_unlink",
        ),
        forbidden_actions=(
            *COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
            "do_not_merge_accounts_silently",
        ),
        alert_required=True,
    ),
    Stage1SupportEscalationTrigger.ACCOUNT_DELETION_REQUEST: Stage1SupportEscalationRule(
        trigger=Stage1SupportEscalationTrigger.ACCOUNT_DELETION_REQUEST,
        category=Stage1SupportTicketCategory.ACCOUNT_DELETION,
        path=(
            Stage1SupportEscalationOwner.AI_FIRST_LINE,
            Stage1SupportEscalationOwner.SUPPORT,
            Stage1SupportEscalationOwner.OWNER,
        ),
        target_owner=Stage1SupportEscalationOwner.OWNER,
        priority=Stage1SupportTicketPriority.P1,
        queue="s1_privacy_rights_review",
        contact=STAGE1_PRIVACY_EMAIL,
        ack_sla_minutes=STAGE1_SUPPORT_P1_ACK_MINUTES,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        required_actions=_base_required_actions(
            "verify_identity_before_deletion",
            "check_active_subscription_payment_and_legal_hold_state",
            "preserve_required_billing_security_and_legal_records",
            "owner_review_before_destructive_action",
            "record_manual_fulfillment_or_denial_reason",
        ),
        forbidden_actions=(
            *COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
            "do_not_delete_required_billing_security_or_legal_records",
            "do_not_process_deletion_from_unverified_contact",
        ),
        alert_required=True,
    ),
    Stage1SupportEscalationTrigger.DATA_EXPORT_REQUEST: Stage1SupportEscalationRule(
        trigger=Stage1SupportEscalationTrigger.DATA_EXPORT_REQUEST,
        category=Stage1SupportTicketCategory.DATA_EXPORT,
        path=(
            Stage1SupportEscalationOwner.AI_FIRST_LINE,
            Stage1SupportEscalationOwner.SUPPORT,
            Stage1SupportEscalationOwner.OWNER,
        ),
        target_owner=Stage1SupportEscalationOwner.OWNER,
        priority=Stage1SupportTicketPriority.P1,
        queue="s1_privacy_rights_review",
        contact=STAGE1_PRIVACY_EMAIL,
        ack_sla_minutes=STAGE1_SUPPORT_P1_ACK_MINUTES,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        required_actions=_base_required_actions(
            "verify_identity_before_export",
            "export_only_portable_account_data",
            "redact_internal_security_provider_fields",
            "deliver_export_through_approved_channel",
            "record_manual_fulfillment_or_denial_reason",
        ),
        forbidden_actions=(
            *COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
            "do_not_export_password_hashes_tokens_totp_secrets_or_internal_ids",
            "do_not_send_export_to_unverified_contact",
            "do_not_include_raw_qr_subscription_url_or_config",
        ),
        alert_required=True,
    ),
    Stage1SupportEscalationTrigger.LEGAL_ABUSE_REQUEST: Stage1SupportEscalationRule(
        trigger=Stage1SupportEscalationTrigger.LEGAL_ABUSE_REQUEST,
        category=Stage1SupportTicketCategory.LEGAL_ABUSE,
        path=(Stage1SupportEscalationOwner.SUPPORT, Stage1SupportEscalationOwner.OWNER),
        target_owner=Stage1SupportEscalationOwner.OWNER,
        priority=Stage1SupportTicketPriority.P0,
        queue="s1_owner_legal_abuse",
        contact=STAGE1_SUPPORT_EMAIL,
        ack_sla_minutes=STAGE1_SUPPORT_P0_ACK_MINUTES,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        required_actions=_base_required_actions(
            "open_p0_incident",
            "preserve_audit_trail",
            "owner_review_before_response",
            "do_not_process_without_final_legal_policy",
        ),
        forbidden_actions=(
            *COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
            "do_not_disclose_private_data_without_owner_approval",
            "do_not_delete_or_mutate_evidence_without_owner_approval",
        ),
        alert_required=True,
    ),
    Stage1SupportEscalationTrigger.EMERGENCY_KILL_SWITCH: Stage1SupportEscalationRule(
        trigger=Stage1SupportEscalationTrigger.EMERGENCY_KILL_SWITCH,
        category=Stage1SupportTicketCategory.LEGAL_ABUSE,
        path=(Stage1SupportEscalationOwner.OPS, Stage1SupportEscalationOwner.OWNER),
        target_owner=Stage1SupportEscalationOwner.OWNER,
        priority=Stage1SupportTicketPriority.P0,
        queue="s1_owner_emergency",
        contact=STAGE1_SUPPORT_EMAIL,
        ack_sla_minutes=STAGE1_SUPPORT_P0_ACK_MINUTES,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        required_actions=_base_required_actions(
            "pause_registration_payments_trial_or_provisioning_when_needed",
            "initiate_rollback_if_release_caused_incident",
            "record_owner_decision_and_time",
            "prepare_customer_or_status_update_if_public_impact",
        ),
        forbidden_actions=(
            *COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
            "do_not_resume_flow_without_owner_decision",
        ),
        alert_required=True,
        kill_switch_allowed=True,
    ),
}

_DEFAULT_TRIGGER_BY_CATEGORY: dict[Stage1SupportTicketCategory, Stage1SupportEscalationTrigger] = {
    Stage1SupportTicketCategory.FAILED_PAYMENT: Stage1SupportEscalationTrigger.FAILED_PAYMENT,
    Stage1SupportTicketCategory.PAID_NO_ACCESS: Stage1SupportEscalationTrigger.PAID_NO_ACCESS,
    Stage1SupportTicketCategory.VPN_NOT_CONNECTING: Stage1SupportEscalationTrigger.VPN_CONNECTIVITY_INCIDENT,
    Stage1SupportTicketCategory.REFUND_REQUEST: Stage1SupportEscalationTrigger.REFUND_REQUEST,
    Stage1SupportTicketCategory.EXPIRED_SUBSCRIPTION: Stage1SupportEscalationTrigger.EXPIRED_SUBSCRIPTION_STUCK,
    Stage1SupportTicketCategory.ACCOUNT_ACCESS: Stage1SupportEscalationTrigger.ACCOUNT_ACCESS_CONFLICT,
    Stage1SupportTicketCategory.ACCOUNT_DELETION: Stage1SupportEscalationTrigger.ACCOUNT_DELETION_REQUEST,
    Stage1SupportTicketCategory.DATA_EXPORT: Stage1SupportEscalationTrigger.DATA_EXPORT_REQUEST,
    Stage1SupportTicketCategory.LEGAL_ABUSE: Stage1SupportEscalationTrigger.LEGAL_ABUSE_REQUEST,
    Stage1SupportTicketCategory.GENERAL: Stage1SupportEscalationTrigger.GENERAL_SUPPORT,
}


def list_stage1_support_escalation_rules() -> tuple[Stage1SupportEscalationRule, ...]:
    """Return escalation rules in stable runbook order."""

    return tuple(STAGE1_SUPPORT_ESCALATION_RULES[trigger] for trigger in REQUIRED_STAGE1_SUPPORT_ESCALATION_TRIGGERS)


def get_stage1_support_escalation_rule(
    trigger: Stage1SupportEscalationTrigger | str,
) -> Stage1SupportEscalationRule:
    """Resolve an escalation rule by stable trigger id."""

    resolved_trigger = (
        trigger if isinstance(trigger, Stage1SupportEscalationTrigger) else Stage1SupportEscalationTrigger(str(trigger))
    )
    return STAGE1_SUPPORT_ESCALATION_RULES[resolved_trigger]


def get_stage1_support_escalation_rule_for_category(
    category: Stage1SupportTicketCategory | str,
) -> Stage1SupportEscalationRule:
    """Resolve the default escalation rule for an S1 support category."""

    resolved_category = (
        category if isinstance(category, Stage1SupportTicketCategory) else Stage1SupportTicketCategory(str(category))
    )
    return get_stage1_support_escalation_rule(_DEFAULT_TRIGGER_BY_CATEGORY[resolved_category])


def build_stage1_support_escalation_decision(
    ticket: Stage1SupportTicketDecision,
    *,
    trigger: Stage1SupportEscalationTrigger | str | None = None,
) -> Stage1SupportEscalationDecision:
    """Build the runbook escalation decision for an already sanitized support ticket."""

    rule = (
        get_stage1_support_escalation_rule(trigger)
        if trigger is not None
        else get_stage1_support_escalation_rule_for_category(ticket.category)
    )
    return Stage1SupportEscalationDecision(ticket_reference=ticket.reference, rule=rule)
