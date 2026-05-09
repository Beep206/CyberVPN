from __future__ import annotations

import pytest

from src.presentation.api.shared import (
    COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS,
    REQUIRED_STAGE1_SUPPORT_ESCALATION_TRIGGERS,
    STAGE1_BACKUP_ALERT_EMAIL,
    STAGE1_PRIMARY_ONCALL_OWNER,
    STAGE1_PRIVACY_EMAIL,
    STAGE1_REFUND_EMAIL,
    STAGE1_SUPPORT_EMAIL,
    STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
    STAGE1_SUPPORT_P0_ACK_MINUTES,
    STAGE1_SUPPORT_P1_ACK_MINUTES,
    Stage1SupportChannel,
    Stage1SupportEscalationOwner,
    Stage1SupportEscalationTrigger,
    Stage1SupportTicketCategory,
    Stage1SupportTicketInput,
    Stage1SupportTicketPriority,
    build_stage1_support_escalation_decision,
    build_stage1_support_ticket,
    get_stage1_support_escalation_rule,
    get_stage1_support_escalation_rule_for_category,
    get_stage1_support_template_for_category,
    list_stage1_support_escalation_rules,
    list_stage1_support_templates,
)


def test_stage1_support_escalation_rules_cover_required_triggers_and_categories() -> None:
    rules = list_stage1_support_escalation_rules()

    assert [rule.trigger for rule in rules] == list(REQUIRED_STAGE1_SUPPORT_ESCALATION_TRIGGERS)
    assert {rule.category for rule in rules}.issuperset(set(Stage1SupportTicketCategory))

    for rule in rules:
        assert rule.target_owner in rule.path
        assert rule.customer_response_sla_minutes == STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES
        assert "create_ticket_or_staff_note" in rule.required_actions
        assert "preserve_safe_reference" in rule.required_actions
        assert set(COMMON_STAGE1_ESCALATION_FORBIDDEN_ACTIONS).issubset(rule.forbidden_actions)
        assert rule.contact in {STAGE1_SUPPORT_EMAIL, STAGE1_REFUND_EMAIL, STAGE1_PRIVACY_EMAIL}


@pytest.mark.parametrize(
    ("trigger", "expected_owner", "expected_contact"),
    [
        (
            Stage1SupportEscalationTrigger.FAILED_PAYMENT,
            Stage1SupportEscalationOwner.FINANCE,
            STAGE1_REFUND_EMAIL,
        ),
        (
            Stage1SupportEscalationTrigger.REFUND_REQUEST,
            Stage1SupportEscalationOwner.FINANCE,
            STAGE1_REFUND_EMAIL,
        ),
    ],
)
def test_stage1_payment_and_refund_escalations_route_to_finance_with_guardrails(
    trigger: Stage1SupportEscalationTrigger,
    expected_owner: Stage1SupportEscalationOwner,
    expected_contact: str,
) -> None:
    rule = get_stage1_support_escalation_rule(trigger)

    assert rule.target_owner == expected_owner
    assert rule.queue == "s1_payment_finance_review"
    assert rule.contact == expected_contact
    assert rule.priority == Stage1SupportTicketPriority.P1
    assert rule.ack_sla_minutes == STAGE1_SUPPORT_P1_ACK_MINUTES
    assert rule.alert_required is True
    assert "do_not_request_full_card_or_cvv" in rule.forbidden_actions

    if trigger == Stage1SupportEscalationTrigger.REFUND_REQUEST:
        assert "do_not_promise_guaranteed_or_automatic_refund" in rule.forbidden_actions
        assert "do_not_refund_without_finance_or_owner_approval" in rule.forbidden_actions
    else:
        assert "do_not_mark_paid_without_provider_final_success" in rule.forbidden_actions
        assert "verify_provider_final_status" in rule.required_actions


def test_stage1_paid_no_access_escalates_to_ops_and_becomes_p0_after_24h() -> None:
    rule = get_stage1_support_escalation_rule_for_category(Stage1SupportTicketCategory.PAID_NO_ACCESS)
    p0_rule = get_stage1_support_escalation_rule(Stage1SupportEscalationTrigger.PAID_NO_ACCESS_OVER_24H)

    assert rule.trigger == Stage1SupportEscalationTrigger.PAID_NO_ACCESS
    assert rule.target_owner == Stage1SupportEscalationOwner.OPS
    assert rule.priority == Stage1SupportTicketPriority.P1
    assert rule.ack_sla_minutes == STAGE1_SUPPORT_P1_ACK_MINUTES
    assert rule.p0_if_unresolved_after_minutes == 24 * 60
    assert "queue_or_retry_provisioning" in rule.required_actions
    assert "check_remnawave_user_and_subscription" in rule.required_actions
    assert "do_not_close_paid_without_access_until_resolved" in rule.forbidden_actions

    assert p0_rule.target_owner == Stage1SupportEscalationOwner.OWNER
    assert p0_rule.priority == Stage1SupportTicketPriority.P0
    assert p0_rule.ack_sla_minutes == STAGE1_SUPPORT_P0_ACK_MINUTES
    assert p0_rule.kill_switch_allowed is True
    assert "do_not_allow_unresolved_paid_no_access_older_than_24h" in p0_rule.forbidden_actions


def test_stage1_remnawave_outage_is_p0_ops_incident_with_owner_path_and_kill_switch() -> None:
    rule = get_stage1_support_escalation_rule(Stage1SupportEscalationTrigger.REMNAWAVE_OR_NODE_OUTAGE)

    assert rule.target_owner == Stage1SupportEscalationOwner.OPS
    assert rule.path[-1] == Stage1SupportEscalationOwner.OWNER
    assert rule.priority == Stage1SupportTicketPriority.P0
    assert rule.ack_sla_minutes == STAGE1_SUPPORT_P0_ACK_MINUTES
    assert rule.queue == "s1_ops_incident"
    assert rule.alert_required is True
    assert rule.kill_switch_allowed is True
    assert "pause_trial_payment_or_provisioning_if_needed" in rule.required_actions


def test_stage1_account_and_legal_escalations_require_owner_review_and_audit() -> None:
    account_rule = get_stage1_support_escalation_rule_for_category(Stage1SupportTicketCategory.ACCOUNT_ACCESS)
    legal_rule = get_stage1_support_escalation_rule_for_category(Stage1SupportTicketCategory.LEGAL_ABUSE)

    assert account_rule.target_owner == Stage1SupportEscalationOwner.OWNER
    assert account_rule.priority == Stage1SupportTicketPriority.P1
    assert account_rule.audit_required is True
    assert "block_silent_merge" in account_rule.required_actions
    assert "do_not_merge_accounts_silently" in account_rule.forbidden_actions

    assert legal_rule.target_owner == Stage1SupportEscalationOwner.OWNER
    assert legal_rule.priority == Stage1SupportTicketPriority.P0
    assert legal_rule.ack_sla_minutes == STAGE1_SUPPORT_P0_ACK_MINUTES
    assert legal_rule.audit_required is True
    assert legal_rule.alert_required is True
    assert "do_not_disclose_private_data_without_owner_approval" in legal_rule.forbidden_actions


def test_stage1_delete_and_export_privacy_escalations_require_owner_review_and_redaction() -> None:
    delete_rule = get_stage1_support_escalation_rule_for_category(Stage1SupportTicketCategory.ACCOUNT_DELETION)
    export_rule = get_stage1_support_escalation_rule_for_category(Stage1SupportTicketCategory.DATA_EXPORT)

    assert delete_rule.trigger == Stage1SupportEscalationTrigger.ACCOUNT_DELETION_REQUEST
    assert delete_rule.target_owner == Stage1SupportEscalationOwner.OWNER
    assert delete_rule.priority == Stage1SupportTicketPriority.P1
    assert delete_rule.queue == "s1_privacy_rights_review"
    assert delete_rule.contact == STAGE1_PRIVACY_EMAIL
    assert delete_rule.audit_required is True
    assert delete_rule.alert_required is True
    assert "verify_identity_before_deletion" in delete_rule.required_actions
    assert "owner_review_before_destructive_action" in delete_rule.required_actions
    assert "do_not_delete_required_billing_security_or_legal_records" in delete_rule.forbidden_actions

    assert export_rule.trigger == Stage1SupportEscalationTrigger.DATA_EXPORT_REQUEST
    assert export_rule.target_owner == Stage1SupportEscalationOwner.OWNER
    assert export_rule.priority == Stage1SupportTicketPriority.P1
    assert export_rule.queue == "s1_privacy_rights_review"
    assert export_rule.contact == STAGE1_PRIVACY_EMAIL
    assert export_rule.audit_required is True
    assert export_rule.alert_required is True
    assert "verify_identity_before_export" in export_rule.required_actions
    assert "export_only_portable_account_data" in export_rule.required_actions
    assert "do_not_export_password_hashes_tokens_totp_secrets_or_internal_ids" in export_rule.forbidden_actions


def test_stage1_support_templates_match_default_escalation_rules() -> None:
    for template in list_stage1_support_templates():
        rule = get_stage1_support_escalation_rule_for_category(template.category)

        assert rule.queue == template.escalation_queue
        assert rule.contact == template.contact
        assert template.escalation_triggers
        assert get_stage1_support_template_for_category(template.category) == template


def test_stage1_privacy_support_templates_use_privacy_contact_and_forbid_secret_data() -> None:
    deletion = get_stage1_support_template_for_category(Stage1SupportTicketCategory.ACCOUNT_DELETION)
    export = get_stage1_support_template_for_category(Stage1SupportTicketCategory.DATA_EXPORT)

    assert deletion is not None
    assert deletion.contact == STAGE1_PRIVACY_EMAIL
    assert deletion.escalation_queue == "s1_privacy_rights_review"
    assert "password" in deletion.forbidden_data
    assert "raw_subscription_url" in deletion.forbidden_data

    assert export is not None
    assert export.contact == STAGE1_PRIVACY_EMAIL
    assert export.escalation_queue == "s1_privacy_rights_review"
    assert "raw_config_file" in export.forbidden_data
    assert "2fa_or_totp_code" in export.forbidden_data


def test_stage1_support_escalation_decision_uses_ticket_reference_without_user_text() -> None:
    ticket = build_stage1_support_ticket(
        Stage1SupportTicketInput(
            channel=Stage1SupportChannel.TELEGRAM_BOT,
            category=Stage1SupportTicketCategory.PAID_NO_ACCESS,
            summary=(
                "I paid but have no VPN. Raw config vless://secret and "
                "provider URL https://provider.example/payments/secret"
            ),
            telegram_id=123456,
        )
    )

    decision = build_stage1_support_escalation_decision(ticket)
    serialized = str(decision.to_api_dict())
    staff_note = decision.to_staff_note()

    assert decision.ticket_reference == ticket.reference
    assert decision.rule.trigger == Stage1SupportEscalationTrigger.PAID_NO_ACCESS
    assert "vless://" not in serialized
    assert "provider.example" not in serialized
    assert "vless://" not in staff_note
    assert "provider.example" not in staff_note
    assert ticket.safe_summary not in serialized


def test_stage1_emergency_kill_switch_has_named_s1_alert_owners_without_credentials() -> None:
    rule = get_stage1_support_escalation_rule(Stage1SupportEscalationTrigger.EMERGENCY_KILL_SWITCH)

    assert STAGE1_PRIMARY_ONCALL_OWNER == "@Sasha_Beep"
    assert STAGE1_BACKUP_ALERT_EMAIL == "backup@cyber-vpn.net"
    assert rule.target_owner == Stage1SupportEscalationOwner.OWNER
    assert rule.priority == Stage1SupportTicketPriority.P0
    assert rule.kill_switch_allowed is True
    assert "pause_registration_payments_trial_or_provisioning_when_needed" in rule.required_actions
    assert "do_not_resume_flow_without_owner_decision" in rule.forbidden_actions
