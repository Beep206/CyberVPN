from __future__ import annotations

import pytest

from src.presentation.api.shared import (
    COMMON_FORBIDDEN_DATA,
    REQUIRED_STAGE1_SUPPORT_TEMPLATE_IDS,
    STAGE1_REFUND_EMAIL,
    STAGE1_SUPPORT_EMAIL,
    Stage1SupportTemplateId,
    Stage1SupportTicketCategory,
    get_stage1_support_template,
    get_stage1_support_template_for_category,
    list_stage1_support_templates,
)


def test_stage1_support_templates_cover_required_s1_cases() -> None:
    templates = list_stage1_support_templates()

    assert [template.template_id for template in templates] == list(REQUIRED_STAGE1_SUPPORT_TEMPLATE_IDS)
    assert {template.category for template in templates} == {
        Stage1SupportTicketCategory.FAILED_PAYMENT,
        Stage1SupportTicketCategory.PAID_NO_ACCESS,
        Stage1SupportTicketCategory.VPN_NOT_CONNECTING,
        Stage1SupportTicketCategory.EXPIRED_SUBSCRIPTION,
        Stage1SupportTicketCategory.REFUND_REQUEST,
    }


@pytest.mark.parametrize(
    ("template_id", "expected_category", "expected_contact", "expected_queue"),
    [
        (
            Stage1SupportTemplateId.FAILED_PAYMENT,
            Stage1SupportTicketCategory.FAILED_PAYMENT,
            STAGE1_REFUND_EMAIL,
            "s1_payment_finance_review",
        ),
        (
            Stage1SupportTemplateId.PAID_NO_ACCESS,
            Stage1SupportTicketCategory.PAID_NO_ACCESS,
            STAGE1_SUPPORT_EMAIL,
            "s1_paid_no_access_review",
        ),
        (
            Stage1SupportTemplateId.VPN_NOT_CONNECTING,
            Stage1SupportTicketCategory.VPN_NOT_CONNECTING,
            STAGE1_SUPPORT_EMAIL,
            "s1_vpn_connectivity_support",
        ),
        (
            Stage1SupportTemplateId.EXPIRED_SUBSCRIPTION,
            Stage1SupportTicketCategory.EXPIRED_SUBSCRIPTION,
            STAGE1_SUPPORT_EMAIL,
            "s1_customer_support",
        ),
        (
            Stage1SupportTemplateId.REFUND_REQUEST,
            Stage1SupportTicketCategory.REFUND_REQUEST,
            STAGE1_REFUND_EMAIL,
            "s1_payment_finance_review",
        ),
    ],
)
def test_stage1_support_templates_route_to_expected_queues(
    template_id: Stage1SupportTemplateId,
    expected_category: Stage1SupportTicketCategory,
    expected_contact: str,
    expected_queue: str,
) -> None:
    template = get_stage1_support_template(template_id)

    assert template.category == expected_category
    assert template.contact == expected_contact
    assert template.escalation_queue == expected_queue
    assert template.customer_message_ru.strip()
    assert template.safe_data_to_request
    assert template.escalation_triggers


def test_stage1_support_templates_forbid_sensitive_customer_data() -> None:
    templates = list_stage1_support_templates()

    for template in templates:
        assert set(COMMON_FORBIDDEN_DATA).issubset(template.forbidden_data)
        body = template.customer_message_ru.casefold()
        assert "отправьте пароль" not in body
        assert "пришлите пароль" not in body
        assert "cvv" in body or template.template_id not in {
            Stage1SupportTemplateId.FAILED_PAYMENT,
            Stage1SupportTemplateId.REFUND_REQUEST,
        }
        assert "seed" not in body
        assert "private key" not in body


def test_stage1_support_templates_do_not_overpromise_payment_or_subscription_outcomes() -> None:
    serialized = "\n".join(template.customer_message_ru.casefold() for template in list_stage1_support_templates())

    unsafe_phrases = (
        "гарантируем возврат",
        "вернем деньги автоматически",
        "вернём деньги автоматически",
        "автоматическое списание включено",
        "renews automatically",
    )
    for phrase in unsafe_phrases:
        assert phrase not in serialized

    expired = get_stage1_support_template(Stage1SupportTemplateId.EXPIRED_SUBSCRIPTION)
    assert "не обещаем автоматическое" in expired.customer_message_ru.casefold()

    refund = get_stage1_support_template(Stage1SupportTemplateId.REFUND_REQUEST)
    assert "не обещаем автоматический или гарантированный возврат" in refund.customer_message_ru.casefold()
    assert "refund policy" in refund.customer_message_ru.casefold()


def test_stage1_paid_no_access_and_vpn_templates_warn_not_to_share_configs() -> None:
    paid_no_access = get_stage1_support_template(Stage1SupportTemplateId.PAID_NO_ACCESS)
    vpn_not_connecting = get_stage1_support_template(Stage1SupportTemplateId.VPN_NOT_CONNECTING)

    for template in (paid_no_access, vpn_not_connecting):
        body = template.customer_message_ru.casefold()
        assert "qr" in body
        assert "subscription url" in body
        assert "config" in body


def test_stage1_support_template_lookup_by_category() -> None:
    template = get_stage1_support_template_for_category(Stage1SupportTicketCategory.REFUND_REQUEST)

    assert template is not None
    assert template.template_id == Stage1SupportTemplateId.REFUND_REQUEST
    assert template.to_api_dict()["template_id"] == "SUP-S1-005"


def test_stage1_support_template_lookup_returns_none_for_untemplated_categories() -> None:
    assert get_stage1_support_template_for_category(Stage1SupportTicketCategory.GENERAL) is None
