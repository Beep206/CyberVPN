from __future__ import annotations

import pytest

from src.presentation.api.shared import (
    STAGE1_PRIVACY_EMAIL,
    STAGE1_REFUND_EMAIL,
    STAGE1_SUPPORT_EMAIL,
    STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
    STAGE1_SUPPORT_P0_ACK_MINUTES,
    STAGE1_SUPPORT_P1_ACK_MINUTES,
    Stage1SupportChannel,
    Stage1SupportState,
    Stage1SupportTicketCategory,
    Stage1SupportTicketInput,
    Stage1SupportTicketPriority,
    build_stage1_support_ticket,
    redact_stage1_support_text,
)


def test_stage1_web_paid_no_access_ticket_routes_to_p1_without_sensitive_values() -> None:
    ticket = build_stage1_support_ticket(
        Stage1SupportTicketInput(
            channel=Stage1SupportChannel.WEB_CONTACT_FORM,
            category=Stage1SupportTicketCategory.PAID_NO_ACCESS,
            summary=(
                "I paid but got no access. My config is vless://raw-config-secret "
                "and dashboard URL is https://cyber-vpn.net/user/config"
            ),
            customer_reference="customer-safe-ref",
            payment_reference="payment-safe-ref",
            email="customer@example.com",
        )
    )

    assert ticket.reference.startswith("s1sup-web-p1-")
    assert ticket.priority == Stage1SupportTicketPriority.P1
    assert ticket.target_queue == "s1_paid_no_access_review"
    assert ticket.target_contact == STAGE1_SUPPORT_EMAIL
    assert ticket.support_state == Stage1SupportState.SUPPORT_REVIEW
    assert ticket.ack_sla_minutes == STAGE1_SUPPORT_P1_ACK_MINUTES
    assert ticket.customer_response_sla_minutes == STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES
    assert "vless://" not in ticket.safe_summary
    assert "https://cyber-vpn.net" not in ticket.safe_summary
    assert "[vpn-config-url]" in ticket.safe_summary
    assert "[url]" in ticket.safe_summary
    assert "route_ops_if_access_missing" in ticket.actions


@pytest.mark.parametrize(
    ("channel", "category"),
    [
        (Stage1SupportChannel.SUPPORT_EMAIL, Stage1SupportTicketCategory.FAILED_PAYMENT),
        (Stage1SupportChannel.REFUND_EMAIL, Stage1SupportTicketCategory.REFUND_REQUEST),
    ],
)
def test_stage1_payment_and_refund_ticket_routes_to_finance_review(
    channel: Stage1SupportChannel,
    category: Stage1SupportTicketCategory,
) -> None:
    ticket = build_stage1_support_ticket(
        Stage1SupportTicketInput(
            channel=channel,
            category=category,
            summary="Money was debited but provider is still pending. Contact customer@example.com",
            payment_reference="provider-safe-ref",
        )
    )

    assert ticket.priority == Stage1SupportTicketPriority.P1
    assert ticket.target_queue == "s1_payment_finance_review"
    assert ticket.target_contact == STAGE1_REFUND_EMAIL
    assert ticket.ack_sla_minutes == STAGE1_SUPPORT_P1_ACK_MINUTES
    assert "customer@example.com" not in ticket.safe_summary
    assert "[email]" in ticket.safe_summary
    assert "reconcile_provider_dashboard" in ticket.actions
    assert "route_finance_review" in ticket.actions


@pytest.mark.parametrize(
    "channel",
    [Stage1SupportChannel.TELEGRAM_BOT, Stage1SupportChannel.TELEGRAM_MINI_APP],
)
def test_stage1_telegram_support_paths_create_stable_safe_references(channel: Stage1SupportChannel) -> None:
    payload = Stage1SupportTicketInput(
        channel=channel,
        category=Stage1SupportTicketCategory.VPN_NOT_CONNECTING,
        summary="Android cannot connect after renewal.",
        telegram_id=123456,
    )

    first = build_stage1_support_ticket(payload)
    second = build_stage1_support_ticket(payload)

    assert first.reference == second.reference
    assert first.reference.startswith("s1sup-")
    assert first.priority == Stage1SupportTicketPriority.P2
    assert first.target_queue == "s1_vpn_connectivity_support"
    assert first.ack_sla_minutes is None
    assert first.customer_response_sla_minutes == STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES
    assert "collect_platform_and_error_time" in first.actions


def test_stage1_legal_abuse_ticket_is_p0_owner_escalation() -> None:
    ticket = build_stage1_support_ticket(
        Stage1SupportTicketInput(
            channel="support_email",
            category="legal_abuse",
            summary="Legal request received. Do not disclose account data.",
            external_reference="external-case-ref",
        )
    )

    assert ticket.priority == Stage1SupportTicketPriority.P0
    assert ticket.target_queue == "s1_owner_legal_abuse"
    assert ticket.support_state == Stage1SupportState.OPS_ESCALATION
    assert ticket.ack_sla_minutes == STAGE1_SUPPORT_P0_ACK_MINUTES
    assert "send_p0_alert" in ticket.actions
    assert "do_not_disclose_private_data_without_approval" in ticket.actions


@pytest.mark.parametrize(
    ("category", "expected_action"),
    [
        (Stage1SupportTicketCategory.ACCOUNT_DELETION, "verify_identity_before_deletion"),
        (Stage1SupportTicketCategory.DATA_EXPORT, "verify_identity_before_export"),
    ],
)
def test_stage1_privacy_rights_tickets_route_to_privacy_review_without_raw_values(
    category: Stage1SupportTicketCategory,
    expected_action: str,
) -> None:
    ticket = build_stage1_support_ticket(
        Stage1SupportTicketInput(
            channel=Stage1SupportChannel.WEB_CONTACT_FORM,
            category=category,
            summary=(
                "Please process my privacy request. Email customer@example.com, "
                "config vless://secret-config and token 123456789:AAAA_BBBBBBBBBBBBBBBBBBBBBBBB"
            ),
            customer_reference="customer-safe-ref",
            email="customer@example.com",
        )
    )

    assert ticket.priority == Stage1SupportTicketPriority.P1
    assert ticket.target_queue == "s1_privacy_rights_review"
    assert ticket.target_contact == STAGE1_PRIVACY_EMAIL
    assert ticket.ack_sla_minutes == STAGE1_SUPPORT_P1_ACK_MINUTES
    assert "customer@example.com" not in ticket.safe_summary
    assert "vless://" not in ticket.safe_summary
    assert "123456789:" not in ticket.safe_summary
    assert "[email]" in ticket.safe_summary
    assert "[vpn-config-url]" in ticket.safe_summary
    assert "[telegram-token]" in ticket.safe_summary
    assert expected_action in ticket.actions


def test_stage1_support_staff_note_and_api_dict_are_redacted() -> None:
    fake_telegram_token = "123456789:" + "AAAA_BBBBBBBBBBBBBBBBBBBBBBBB"
    fake_long_secret = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" + "abcdefghijklmnopqrstuvwxyz"
    ticket = build_stage1_support_ticket(
        Stage1SupportTicketInput(
            channel=Stage1SupportChannel.ADMIN_MANUAL,
            category=Stage1SupportTicketCategory.ACCOUNT_ACCESS,
            summary=(
                f"User pasted token {fake_telegram_token} "
                f"and secret {fake_long_secret}"
            ),
        )
    )
    serialized = str(ticket.to_api_dict())
    staff_note = ticket.to_staff_note()

    assert "123456789:" not in serialized
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in serialized
    assert "123456789:" not in staff_note
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in staff_note
    assert "[telegram-token]" in ticket.safe_summary
    assert "[secret]" in ticket.safe_summary


def test_stage1_support_ticket_requires_non_empty_summary() -> None:
    with pytest.raises(ValueError, match="summary is required"):
        build_stage1_support_ticket(
            Stage1SupportTicketInput(
                channel=Stage1SupportChannel.WEB_CONTACT_FORM,
                category=Stage1SupportTicketCategory.GENERAL,
                summary="   ",
            )
        )


def test_stage1_support_redaction_truncates_long_user_input() -> None:
    redacted = redact_stage1_support_text("word " * 200, max_chars=32)

    assert len(redacted) == 32
    assert redacted.endswith("...")
