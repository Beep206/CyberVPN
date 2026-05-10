"""S1 support response templates.

Templates are intentionally conservative: they tell support what can be asked
from a beta user, what must not be requested, and which queue owns escalation.
They do not replace final legal policy or a live helpdesk.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from src.presentation.api.shared.stage1_support_ticket_path import (
    STAGE1_PRIVACY_EMAIL,
    STAGE1_REFUND_EMAIL,
    STAGE1_SUPPORT_EMAIL,
    Stage1SupportTicketCategory,
)


class Stage1SupportTemplateId(StrEnum):
    """Stable template identifiers used in S1 support docs and tests."""

    FAILED_PAYMENT = "SUP-S1-001"
    PAID_NO_ACCESS = "SUP-S1-002"
    VPN_NOT_CONNECTING = "SUP-S1-003"
    EXPIRED_SUBSCRIPTION = "SUP-S1-004"
    REFUND_REQUEST = "SUP-S1-005"
    ACCOUNT_DELETION = "SUP-S1-006"
    DATA_EXPORT = "SUP-S1-007"


@dataclass(frozen=True, slots=True)
class Stage1SupportTemplate:
    """Support template with safety and escalation metadata."""

    template_id: Stage1SupportTemplateId
    category: Stage1SupportTicketCategory
    title: str
    customer_message_ru: str
    safe_data_to_request: tuple[str, ...]
    forbidden_data: tuple[str, ...]
    escalation_queue: str
    contact: str
    escalation_triggers: tuple[str, ...]

    def to_api_dict(self) -> dict[str, object]:
        return {
            "template_id": self.template_id.value,
            "category": self.category.value,
            "title": self.title,
            "customer_message_ru": self.customer_message_ru,
            "safe_data_to_request": list(self.safe_data_to_request),
            "forbidden_data": list(self.forbidden_data),
            "escalation_queue": self.escalation_queue,
            "contact": self.contact,
            "escalation_triggers": list(self.escalation_triggers),
        }


COMMON_FORBIDDEN_DATA = (
    "password",
    "2fa_or_totp_code",
    "full_card_number",
    "cvv_or_cvc",
    "raw_qr_code",
    "raw_subscription_url",
    "raw_config_file",
    "seed_phrase_or_private_key",
)

STAGE1_SUPPORT_TEMPLATES: dict[Stage1SupportTemplateId, Stage1SupportTemplate] = {
    Stage1SupportTemplateId.FAILED_PAYMENT: Stage1SupportTemplate(
        template_id=Stage1SupportTemplateId.FAILED_PAYMENT,
        category=Stage1SupportTicketCategory.FAILED_PAYMENT,
        title="Failed or pending payment",
        customer_message_ru=(
            "Мы видим, что оплата не завершилась или ожидает подтверждения. "
            "Проверьте статус платежа в кабинете или Telegram Mini App. "
            "Если деньги списались, отправьте ID платежа, дату, способ оплаты "
            "или скрин без номера карты, CVV/CVC, QR-кода, subscription URL и config. "
            "Мы сверим статус у провайдера и обновим доступ только после подтверждения платежа."
        ),
        safe_data_to_request=(
            "payment_id_or_invoice_id",
            "payment_date",
            "payment_provider_name",
            "redacted_screenshot",
            "account_email_or_telegram_handle",
        ),
        forbidden_data=COMMON_FORBIDDEN_DATA,
        escalation_queue="s1_payment_finance_review",
        contact=STAGE1_REFUND_EMAIL,
        escalation_triggers=(
            "user_reports_debit_but_provider_non_final",
            "amount_or_currency_mismatch",
            "provider_dashboard_disagrees_with_backend",
        ),
    ),
    Stage1SupportTemplateId.PAID_NO_ACCESS: Stage1SupportTemplate(
        template_id=Stage1SupportTemplateId.PAID_NO_ACCESS,
        category=Stage1SupportTicketCategory.PAID_NO_ACCESS,
        title="Paid but VPN access is not ready",
        customer_message_ru=(
            "Оплата найдена или проверяется. Если платеж подтвержден, доступ должен быть выдан "
            "автоматически. Если доступ не появился, мы проверим payment status, provisioning "
            "status и Remnawave-состояние, затем повторим выдачу доступа или передадим заявку "
            "технической команде. Не отправляйте публично QR-код, subscription URL или config file."
        ),
        safe_data_to_request=(
            "payment_id_or_invoice_id",
            "account_email_or_telegram_handle",
            "approximate_payment_time",
            "device_platform",
        ),
        forbidden_data=COMMON_FORBIDDEN_DATA,
        escalation_queue="s1_paid_no_access_review",
        contact=STAGE1_SUPPORT_EMAIL,
        escalation_triggers=(
            "provider_final_success_without_access",
            "provisioning_failed_or_retrying",
            "paid_no_access_older_than_24h",
        ),
    ),
    Stage1SupportTemplateId.VPN_NOT_CONNECTING: Stage1SupportTemplate(
        template_id=Stage1SupportTemplateId.VPN_NOT_CONNECTING,
        category=Stage1SupportTicketCategory.VPN_NOT_CONNECTING,
        title="VPN does not connect",
        customer_message_ru=(
            "Проверьте срок подписки, лимит устройств, правильную инструкцию для вашей платформы "
            "и что используется актуальный QR/subscription URL/config. Если подключение все равно "
            "не работает, отправьте платформу, приложение/клиент, страну подключения, примерное "
            "время ошибки и скрин сообщения без QR-кода, subscription URL и config file."
        ),
        safe_data_to_request=(
            "device_platform",
            "vpn_client_name",
            "country_or_region",
            "approximate_error_time",
            "redacted_error_screenshot",
        ),
        forbidden_data=COMMON_FORBIDDEN_DATA,
        escalation_queue="s1_vpn_connectivity_support",
        contact=STAGE1_SUPPORT_EMAIL,
        escalation_triggers=(
            "many_users_same_node",
            "subscription_active_but_all_devices_fail",
            "remnawave_or_node_health_warning",
        ),
    ),
    Stage1SupportTemplateId.EXPIRED_SUBSCRIPTION: Stage1SupportTemplate(
        template_id=Stage1SupportTemplateId.EXPIRED_SUBSCRIPTION,
        category=Stage1SupportTicketCategory.EXPIRED_SUBSCRIPTION,
        title="Expired subscription",
        customer_message_ru=(
            "Подписка истекла или находится в grace period. Для восстановления доступа продлите "
            "тариф в кабинете или Telegram Mini App. В Stage 1 мы не обещаем автоматическое "
            "списание или автопродление: продление выполняется вручную пользователем. Если оплата "
            "уже была выполнена, отправьте ID платежа или дату оплаты, и мы проверим статус."
        ),
        safe_data_to_request=(
            "account_email_or_telegram_handle",
            "payment_id_or_invoice_id_if_paid",
            "payment_date_if_paid",
        ),
        forbidden_data=COMMON_FORBIDDEN_DATA,
        escalation_queue="s1_customer_support",
        contact=STAGE1_SUPPORT_EMAIL,
        escalation_triggers=(
            "user_paid_renewal_but_expired_state_remains",
            "grace_period_state_mismatch",
            "manual_grant_needed_after_verified_payment",
        ),
    ),
    Stage1SupportTemplateId.REFUND_REQUEST: Stage1SupportTemplate(
        template_id=Stage1SupportTemplateId.REFUND_REQUEST,
        category=Stage1SupportTicketCategory.REFUND_REQUEST,
        title="Refund request",
        customer_message_ru=(
            "Мы приняли запрос на возврат. Для проверки укажите ID платежа, дату оплаты, способ "
            "оплаты и причину обращения. Решение зависит от статуса платежа, использованного "
            "провайдера и финальной Refund Policy. Не отправляйте номер карты, CVV/CVC, пароль, "
            "QR-код, subscription URL или config file. До проверки мы не обещаем автоматический "
            "или гарантированный возврат."
        ),
        safe_data_to_request=(
            "payment_id_or_invoice_id",
            "payment_date",
            "payment_provider_name",
            "refund_reason",
            "account_email_or_telegram_handle",
        ),
        forbidden_data=COMMON_FORBIDDEN_DATA,
        escalation_queue="s1_payment_finance_review",
        contact=STAGE1_REFUND_EMAIL,
        escalation_triggers=(
            "provider_refund_requested",
            "duplicate_payment_or_wrong_amount",
            "chargeback_or_dispute_risk",
        ),
    ),
    Stage1SupportTemplateId.ACCOUNT_DELETION: Stage1SupportTemplate(
        template_id=Stage1SupportTemplateId.ACCOUNT_DELETION,
        category=Stage1SupportTicketCategory.ACCOUNT_DELETION,
        title="Account deletion request",
        customer_message_ru=(
            "Мы приняли запрос на удаление аккаунта. Перед выполнением действия support проверит "
            "владение аккаунтом и активные платежи/подписки. В S1 удаление выполняется управляемо: "
            "мы не удаляем обязательные billing, security, audit или legal records, если их нужно "
            "сохранить по политике или для защиты от споров. Не отправляйте пароль, 2FA-код, QR-код, "
            "subscription URL или config file."
        ),
        safe_data_to_request=(
            "account_email_or_telegram_handle",
            "deletion_reason_optional",
            "last_successful_payment_id_if_relevant",
        ),
        forbidden_data=COMMON_FORBIDDEN_DATA,
        escalation_queue="s1_privacy_rights_review",
        contact=STAGE1_PRIVACY_EMAIL,
        escalation_triggers=(
            "user_requests_account_deletion",
            "active_subscription_or_payment_history_exists",
            "identity_verification_or_legal_hold_review_needed",
        ),
    ),
    Stage1SupportTemplateId.DATA_EXPORT: Stage1SupportTemplate(
        template_id=Stage1SupportTemplateId.DATA_EXPORT,
        category=Stage1SupportTicketCategory.DATA_EXPORT,
        title="Data export request",
        customer_message_ru=(
            "Мы приняли запрос на экспорт данных аккаунта. Перед подготовкой выгрузки support "
            "проверит владение аккаунтом. В S1 экспорт ограничен переносимыми account/payment/"
            "subscription/support metadata, которые можно безопасно раскрыть пользователю; internal "
            "security fields, password hashes, tokens, TOTP secrets, raw provider payloads, QR-коды, "
            "subscription URLs и config files не включаются."
        ),
        safe_data_to_request=(
            "account_email_or_telegram_handle",
            "preferred_contact_channel",
            "export_scope_question_optional",
        ),
        forbidden_data=COMMON_FORBIDDEN_DATA,
        escalation_queue="s1_privacy_rights_review",
        contact=STAGE1_PRIVACY_EMAIL,
        escalation_triggers=(
            "user_requests_data_export",
            "support_must_verify_identity",
            "owner_review_needed_for_sensitive_or_conflicting_account_state",
        ),
    ),
}

REQUIRED_STAGE1_SUPPORT_TEMPLATE_IDS = (
    Stage1SupportTemplateId.FAILED_PAYMENT,
    Stage1SupportTemplateId.PAID_NO_ACCESS,
    Stage1SupportTemplateId.VPN_NOT_CONNECTING,
    Stage1SupportTemplateId.EXPIRED_SUBSCRIPTION,
    Stage1SupportTemplateId.REFUND_REQUEST,
)


def list_stage1_support_templates() -> tuple[Stage1SupportTemplate, ...]:
    """Return templates in stable operator-facing order."""

    return tuple(STAGE1_SUPPORT_TEMPLATES[template_id] for template_id in REQUIRED_STAGE1_SUPPORT_TEMPLATE_IDS)


def get_stage1_support_template(template_id: Stage1SupportTemplateId | str) -> Stage1SupportTemplate:
    """Resolve a support template by stable `SUP-S1-*` id."""

    resolved_id = (
        template_id if isinstance(template_id, Stage1SupportTemplateId) else Stage1SupportTemplateId(str(template_id))
    )
    return STAGE1_SUPPORT_TEMPLATES[resolved_id]


def get_stage1_support_template_for_category(
    category: Stage1SupportTicketCategory | str,
) -> Stage1SupportTemplate | None:
    """Resolve the default support template for an S1 support category."""

    resolved_category = (
        category if isinstance(category, Stage1SupportTicketCategory) else Stage1SupportTicketCategory(str(category))
    )
    for template in STAGE1_SUPPORT_TEMPLATES.values():
        if template.category == resolved_category:
            return template
    return None
