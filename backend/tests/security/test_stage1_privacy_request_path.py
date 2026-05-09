from __future__ import annotations

import pytest

from src.presentation.api.shared import (
    STAGE1_PRIVACY_EMAIL,
    STAGE1_PRIVACY_MANUAL_FULFILLMENT_TARGET_DAYS,
    Stage1PrivacyRequestInput,
    Stage1PrivacyRequestKind,
    Stage1SupportChannel,
    Stage1SupportEscalationTrigger,
    Stage1SupportTicketPriority,
    build_stage1_privacy_request,
)


@pytest.mark.parametrize(
    ("request_kind", "expected_trigger", "expected_required_action", "expected_forbidden_action"),
    [
        (
            Stage1PrivacyRequestKind.ACCOUNT_DELETION,
            Stage1SupportEscalationTrigger.ACCOUNT_DELETION_REQUEST,
            "verify_identity_before_deletion",
            "do_not_delete_required_billing_security_or_legal_records",
        ),
        (
            Stage1PrivacyRequestKind.DATA_EXPORT,
            Stage1SupportEscalationTrigger.DATA_EXPORT_REQUEST,
            "verify_identity_before_export",
            "do_not_export_password_hashes_tokens_totp_secrets_or_internal_ids",
        ),
    ],
)
def test_stage1_privacy_request_builds_safe_manual_review_path(
    request_kind: Stage1PrivacyRequestKind,
    expected_trigger: Stage1SupportEscalationTrigger,
    expected_required_action: str,
    expected_forbidden_action: str,
) -> None:
    decision = build_stage1_privacy_request(
        Stage1PrivacyRequestInput(
            request_kind=request_kind,
            channel=Stage1SupportChannel.WEB_CONTACT_FORM,
            user_reference="user-safe-ref",
            contact="customer@example.com",
            notes=(
                "Here is my subscription URL https://cyber-vpn.net/config/secret "
                "and raw config vless://secret"
            ),
        )
    )

    payload = decision.to_api_dict()
    staff_note = decision.to_staff_note()

    assert decision.ticket.priority == Stage1SupportTicketPriority.P1
    assert decision.ticket.target_queue == "s1_privacy_rights_review"
    assert decision.ticket.target_contact == STAGE1_PRIVACY_EMAIL
    assert decision.escalation.rule.trigger == expected_trigger
    assert decision.manual_fulfillment_target_days == STAGE1_PRIVACY_MANUAL_FULFILLMENT_TARGET_DAYS
    assert expected_required_action in decision.escalation.rule.required_actions
    assert expected_forbidden_action in decision.escalation.rule.forbidden_actions
    assert payload["target_contact"] == STAGE1_PRIVACY_EMAIL
    assert payload["audit_required"] is True
    assert payload["manual_fulfillment_target_days"] == 30
    assert "customer@example.com" not in str(payload)
    assert "cyber-vpn.net/config/secret" not in str(payload)
    assert "vless://" not in str(payload)
    assert "customer@example.com" not in staff_note
    assert "vless://" not in staff_note


def test_stage1_privacy_request_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="Unsupported Stage1PrivacyRequestKind"):
        build_stage1_privacy_request(
            Stage1PrivacyRequestInput(
                request_kind="raw_database_dump",
                channel=Stage1SupportChannel.WEB_CONTACT_FORM,
                user_reference="user-safe-ref",
            )
        )
