"""S2-STAGE-09 support/admin operations checks."""

from __future__ import annotations

from uuid import UUID

from src.domain.enums import AdminRole
from src.presentation.api.shared.stage1_support_templates import Stage1SupportTemplateId
from src.presentation.api.shared.stage2_support_admin_ops import (
    S2_PAID_NO_ACCESS_MAX_AGE_HOURS,
    S2_SUPPORT_FORBIDDEN_OUTPUT_FIELDS,
    S2_SUPPORT_REQUIRED_AUDIT_ACTIONS,
    S2SupportAction,
    S2SupportAdminReadinessSnapshot,
    S2SupportIssueType,
    S2SupportLookup,
    S2SupportReadinessState,
    decide_s2_support_action,
    evaluate_s2_support_admin_readiness,
    get_s2_support_issue_contract,
    list_s2_support_issue_contracts,
    redact_s2_support_payload,
)
from src.presentation.api.v1.admin import customer_support
from src.presentation.api.v1.admin.customer_support_schemas import AdminCustomerSubscriptionResyncResponse


def test_s2_support_contract_covers_required_public_release_cases() -> None:
    contracts = list_s2_support_issue_contracts()

    assert [contract.issue_type for contract in contracts] == list(S2SupportIssueType)
    assert get_s2_support_issue_contract(S2SupportIssueType.PAYMENT_SUCCEEDED_NO_ACCESS).template_id == (
        Stage1SupportTemplateId.PAID_NO_ACCESS
    )
    assert get_s2_support_issue_contract(S2SupportIssueType.VPN_DOES_NOT_CONNECT).template_id == (
        Stage1SupportTemplateId.VPN_NOT_CONNECTING
    )
    assert get_s2_support_issue_contract(S2SupportIssueType.REFUND_REQUEST).template_id == (
        Stage1SupportTemplateId.REFUND_REQUEST
    )
    assert get_s2_support_issue_contract(S2SupportIssueType.SUBSCRIPTION_EXPIRED).template_id == (
        Stage1SupportTemplateId.EXPIRED_SUBSCRIPTION
    )


def test_s2_paid_no_access_contract_has_p0_sla_and_all_required_lookups() -> None:
    contract = get_s2_support_issue_contract(S2SupportIssueType.PAYMENT_SUCCEEDED_NO_ACCESS)

    assert contract.priority == "P0"
    assert contract.ack_minutes == 15
    assert S2_PAID_NO_ACCESS_MAX_AGE_HOURS == 24
    assert {
        S2SupportLookup.CUSTOMER,
        S2SupportLookup.PAYMENT,
        S2SupportLookup.SUBSCRIPTION,
        S2SupportLookup.PROVISIONING,
        S2SupportLookup.AUDIT_TIMELINE,
    }.issubset(contract.required_lookups)
    assert S2SupportAction.MANUAL_SUPPORT_GRANT in contract.allowed_actions
    assert S2SupportAction.REPROVISION_OR_RESYNC in contract.allowed_actions


def test_s2_support_action_role_contract_separates_support_finance_and_admin() -> None:
    assert decide_s2_support_action(AdminRole.SUPPORT, S2SupportAction.READ_DIAGNOSTICS).allowed is True
    assert decide_s2_support_action(AdminRole.SUPPORT, S2SupportAction.VPN_CREDENTIAL_REGENERATION).allowed is True
    assert decide_s2_support_action(AdminRole.SUPPORT, S2SupportAction.MANUAL_SUPPORT_GRANT).allowed is False
    assert decide_s2_support_action(AdminRole.FINANCE, S2SupportAction.REFUND_REVIEW).allowed is True
    assert decide_s2_support_action(AdminRole.FINANCE, S2SupportAction.VPN_CREDENTIAL_REGENERATION).allowed is False
    assert decide_s2_support_action(AdminRole.OPERATOR, S2SupportAction.MANUAL_SUPPORT_GRANT).allowed is True
    assert decide_s2_support_action(AdminRole.ADMIN, S2SupportAction.GROWTH_REVERSAL).allowed is True

    for action in (
        S2SupportAction.ADD_STAFF_NOTE,
        S2SupportAction.REFUND_REVIEW,
        S2SupportAction.MANUAL_SUPPORT_GRANT,
        S2SupportAction.REPROVISION_OR_RESYNC,
        S2SupportAction.VPN_CREDENTIAL_REGENERATION,
        S2SupportAction.GROWTH_REVERSAL,
    ):
        assert decide_s2_support_action(AdminRole.ADMIN, action).audit_required is True


def test_s2_support_admin_readiness_blocks_missing_operational_surfaces() -> None:
    decision = evaluate_s2_support_admin_readiness(
        S2SupportAdminReadinessSnapshot(
            support_queue_available=True,
            customer_lookup_available=True,
            payment_lookup_available=False,
            subscription_lookup_available=True,
            provisioning_lookup_available=True,
            audit_log_available=True,
            manual_grants_audited=True,
            dangerous_actions_protected=True,
            support_email_configured=True,
            refund_email_configured=True,
            abuse_email_configured=True,
            primary_on_call_set=True,
            backup_on_call_set=True,
        )
    )

    assert decision.state == S2SupportReadinessState.BLOCKED
    assert decision.ready_for_public_release is False
    assert "payment_lookup_unavailable" in decision.issues


def test_s2_support_admin_readiness_allows_public_release_with_oncall_split_recommendation() -> None:
    decision = evaluate_s2_support_admin_readiness(
        S2SupportAdminReadinessSnapshot(
            support_queue_available=True,
            customer_lookup_available=True,
            payment_lookup_available=True,
            subscription_lookup_available=True,
            provisioning_lookup_available=True,
            audit_log_available=True,
            manual_grants_audited=True,
            dangerous_actions_protected=True,
            support_email_configured=True,
            refund_email_configured=True,
            abuse_email_configured=True,
            primary_on_call_set=True,
            backup_on_call_set=True,
            primary_and_backup_split=False,
        )
    )

    assert decision.state == S2SupportReadinessState.READY_WITH_LIMITS
    assert decision.ready_for_public_release is True
    assert decision.issues == ()
    assert decision.recommendations == ("split_primary_and_backup_support_on_call_before_unrestricted_s2_opening",)


def test_s2_support_redaction_removes_raw_config_tokens_and_provider_secrets() -> None:
    redacted = redact_s2_support_payload(
        {
            "email": "user@example.test",
            "subscription_url": "https://cyber-vpn.org/api/sub/secret-token",
            "nested": {
                "raw_config": "vless://uuid@de-1.cyber-vpn.org:443",
                "refresh_token": "refresh-secret",
                "safe_status": "active",
            },
            "provider_payload": {
                "webhook_signature": "sha256=secret",
                "amount": 10,
            },
        }
    )

    serialized = str(redacted).lower()
    assert redacted["email"] == "user@example.test"
    assert redacted["subscription_url"] == "[REDACTED]"
    assert redacted["nested"]["raw_config"] == "[REDACTED]"
    assert redacted["nested"]["refresh_token"] == "[REDACTED]"
    assert redacted["nested"]["safe_status"] == "active"
    assert redacted["provider_payload"]["webhook_signature"] == "[REDACTED]"
    assert "vless://" not in serialized
    assert "secret-token" not in serialized
    assert "refresh-secret" not in serialized
    assert {"password", "subscription_url", "vless"}.issubset(S2_SUPPORT_FORBIDDEN_OUTPUT_FIELDS)


def test_s2_required_audit_actions_cover_existing_customer_support_dangerous_routes() -> None:
    assert {
        "customer_subscription_manual_granted",
        "customer_vpn_credentials_regenerated",
        "customer_subscription_resynced",
        "customer_password_reset",
        "customer_operations.approve_payout_instruction",
        "customer_operations.reject_payout_instruction",
    }.issubset(S2_SUPPORT_REQUIRED_AUDIT_ACTIONS)


def test_s2_subscription_resync_response_is_redacted_for_admin_support_outputs() -> None:
    response = AdminCustomerSubscriptionResyncResponse(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        previous_subscription_url=customer_support._redact_admin_url("https://cyber-vpn.org/api/sub/old-secret"),
        stored_subscription_url=customer_support._redact_admin_url("https://cyber-vpn.org/api/sub/new-secret"),
        upstream_subscription_url=customer_support._redact_admin_url("https://cyber-vpn.org/api/sub/new-secret")
        or customer_support.REDACTED_ADMIN_URL,
        previous_subscription_url_present=True,
        stored_subscription_url_present=True,
        upstream_subscription_url_present=True,
    )

    dumped = response.model_dump()
    serialized = str(dumped).lower()
    assert dumped["previous_subscription_url"] == "[REDACTED]"
    assert dumped["stored_subscription_url"] == "[REDACTED]"
    assert dumped["upstream_subscription_url"] == "[REDACTED]"
    assert dumped["previous_subscription_url_present"] is True
    assert dumped["stored_subscription_url_present"] is True
    assert dumped["upstream_subscription_url_present"] is True
    assert "/api/sub/" not in serialized
    assert "old-secret" not in serialized
