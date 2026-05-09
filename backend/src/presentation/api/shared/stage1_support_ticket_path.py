"""S1 support ticket routing contract.

The S1 beta support path is deliberately lightweight: Telegram bot escalations,
web contact handoff, support email and refund email must all produce the same
safe reference, queue target and SLA classification without requiring a paid
ticketing system before go-live.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum

from src.presentation.api.shared.stage1_contract import Stage1SupportState

STAGE1_SUPPORT_EMAIL = "support@cyber-vpn.net"
STAGE1_REFUND_EMAIL = "refund@cyber-vpn.net"
STAGE1_PRIVACY_EMAIL = "privacy@cyber-vpn.net"
STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES = 12 * 60
STAGE1_SUPPORT_P1_ACK_MINUTES = 60
STAGE1_SUPPORT_P0_ACK_MINUTES = 15


class Stage1SupportChannel(StrEnum):
    """Approved S1 support intake channels."""

    TELEGRAM_BOT = "telegram_bot"
    TELEGRAM_MINI_APP = "telegram_mini_app"
    WEB_CONTACT_FORM = "web_contact_form"
    SUPPORT_EMAIL = "support_email"
    REFUND_EMAIL = "refund_email"
    ADMIN_MANUAL = "admin_manual"


class Stage1SupportTicketCategory(StrEnum):
    """Support categories used by S1 user-facing and admin flows."""

    FAILED_PAYMENT = "failed_payment"
    PAID_NO_ACCESS = "paid_no_access"
    VPN_NOT_CONNECTING = "vpn_not_connecting"
    REFUND_REQUEST = "refund_request"
    EXPIRED_SUBSCRIPTION = "expired_subscription"
    ACCOUNT_ACCESS = "account_access"
    ACCOUNT_DELETION = "account_deletion"
    DATA_EXPORT = "data_export"
    LEGAL_ABUSE = "legal_abuse"
    GENERAL = "general"


class Stage1SupportTicketPriority(StrEnum):
    """Operational support priority for S1 ticket triage."""

    P0 = "p0"
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"


@dataclass(frozen=True, slots=True)
class Stage1SupportTicketInput:
    """Input from any approved S1 support intake channel."""

    channel: Stage1SupportChannel | str
    category: Stage1SupportTicketCategory | str
    summary: str
    customer_reference: str | None = None
    payment_reference: str | None = None
    telegram_id: int | str | None = None
    email: str | None = None
    external_reference: str | None = None


@dataclass(frozen=True, slots=True)
class Stage1SupportTicketDecision:
    """Support routing decision safe for admin notes, docs and API responses."""

    reference: str
    channel: Stage1SupportChannel
    category: Stage1SupportTicketCategory
    priority: Stage1SupportTicketPriority
    target_queue: str
    target_contact: str
    support_state: Stage1SupportState
    ack_sla_minutes: int | None
    customer_response_sla_minutes: int
    safe_summary: str
    actions: tuple[str, ...]

    def to_staff_note(self) -> str:
        """Render a support-safe staff note without raw URLs, configs or tokens."""

        return "\n".join(
            [
                "S1 support ticket",
                f"Reference: {self.reference}",
                f"Channel: {self.channel.value}",
                f"Category: {self.category.value}",
                f"Priority: {self.priority.value}",
                f"Queue: {self.target_queue}",
                f"Contact: {self.target_contact}",
                f"Ack SLA minutes: {self.ack_sla_minutes or 'n/a'}",
                f"Customer response SLA minutes: {self.customer_response_sla_minutes}",
                f"Safe summary: {self.safe_summary}",
            ]
        )

    def to_api_dict(self) -> dict[str, object]:
        """Serialize the ticket decision without raw customer or provider ids."""

        return {
            "reference": self.reference,
            "channel": self.channel.value,
            "category": self.category.value,
            "priority": self.priority.value,
            "target_queue": self.target_queue,
            "target_contact": self.target_contact,
            "support_state": self.support_state.value,
            "ack_sla_minutes": self.ack_sla_minutes,
            "customer_response_sla_minutes": self.customer_response_sla_minutes,
            "safe_summary": self.safe_summary,
            "actions": list(self.actions),
        }


_CONFIG_URL_PATTERN = re.compile(r"\b(?:vless|vmess|trojan|ss|wireguard)://[^\s<>]+", re.IGNORECASE)
_HTTP_URL_PATTERN = re.compile(r"\bhttps?://[^\s<>]+", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_TELEGRAM_BOT_TOKEN_PATTERN = re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b")
_LONG_SECRET_PATTERN = re.compile(r"\b[A-Za-z0-9_-]{40,}\b")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def redact_stage1_support_text(value: str, *, max_chars: int = 700) -> str:
    """Return a compact support-safe summary from user-provided support text."""

    redacted = _CONFIG_URL_PATTERN.sub("[vpn-config-url]", value)
    redacted = _TELEGRAM_BOT_TOKEN_PATTERN.sub("[telegram-token]", redacted)
    redacted = _HTTP_URL_PATTERN.sub("[url]", redacted)
    redacted = _EMAIL_PATTERN.sub("[email]", redacted)
    redacted = _LONG_SECRET_PATTERN.sub("[secret]", redacted)
    redacted = _WHITESPACE_PATTERN.sub(" ", redacted).strip()
    if len(redacted) <= max_chars:
        return redacted
    return f"{redacted[: max_chars - 3].rstrip()}..."


def build_stage1_support_ticket(ticket_input: Stage1SupportTicketInput) -> Stage1SupportTicketDecision:
    """Build the S1 support ticket path decision for Telegram, email and web."""

    channel = _coerce_channel(ticket_input.channel)
    category = _coerce_category(ticket_input.category)
    safe_summary = redact_stage1_support_text(ticket_input.summary)
    if not safe_summary:
        raise ValueError("S1 support ticket summary is required")

    priority = _priority_for_category(category)
    target_queue = _target_queue_for_category(category)
    target_contact = _target_contact_for_category(category)
    support_state = (
        Stage1SupportState.OPS_ESCALATION
        if priority == Stage1SupportTicketPriority.P0
        else Stage1SupportState.SUPPORT_REVIEW
    )
    ack_sla_minutes = _ack_sla_for_priority(priority)
    actions = _actions_for_category(category, priority)

    return Stage1SupportTicketDecision(
        reference=_support_ticket_reference(ticket_input, channel, category, priority, safe_summary),
        channel=channel,
        category=category,
        priority=priority,
        target_queue=target_queue,
        target_contact=target_contact,
        support_state=support_state,
        ack_sla_minutes=ack_sla_minutes,
        customer_response_sla_minutes=STAGE1_SUPPORT_FIRST_RESPONSE_MINUTES,
        safe_summary=safe_summary,
        actions=actions,
    )


def _coerce_channel(value: Stage1SupportChannel | str) -> Stage1SupportChannel:
    return _coerce_enum(Stage1SupportChannel, value)


def _coerce_category(value: Stage1SupportTicketCategory | str) -> Stage1SupportTicketCategory:
    return _coerce_enum(Stage1SupportTicketCategory, value)


def _coerce_enum[T: StrEnum](enum_type: type[T], value: T | str) -> T:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except ValueError as exc:
        raise ValueError(f"Unsupported {enum_type.__name__}: {value}") from exc


def _priority_for_category(category: Stage1SupportTicketCategory) -> Stage1SupportTicketPriority:
    if category == Stage1SupportTicketCategory.LEGAL_ABUSE:
        return Stage1SupportTicketPriority.P0
    if category in {
        Stage1SupportTicketCategory.FAILED_PAYMENT,
        Stage1SupportTicketCategory.PAID_NO_ACCESS,
        Stage1SupportTicketCategory.REFUND_REQUEST,
        Stage1SupportTicketCategory.ACCOUNT_DELETION,
        Stage1SupportTicketCategory.DATA_EXPORT,
    }:
        return Stage1SupportTicketPriority.P1
    if category in {
        Stage1SupportTicketCategory.VPN_NOT_CONNECTING,
        Stage1SupportTicketCategory.EXPIRED_SUBSCRIPTION,
        Stage1SupportTicketCategory.ACCOUNT_ACCESS,
    }:
        return Stage1SupportTicketPriority.P2
    return Stage1SupportTicketPriority.P3


def _target_queue_for_category(category: Stage1SupportTicketCategory) -> str:
    if category == Stage1SupportTicketCategory.LEGAL_ABUSE:
        return "s1_owner_legal_abuse"
    if category in {
        Stage1SupportTicketCategory.FAILED_PAYMENT,
        Stage1SupportTicketCategory.REFUND_REQUEST,
    }:
        return "s1_payment_finance_review"
    if category == Stage1SupportTicketCategory.PAID_NO_ACCESS:
        return "s1_paid_no_access_review"
    if category == Stage1SupportTicketCategory.VPN_NOT_CONNECTING:
        return "s1_vpn_connectivity_support"
    if category in {
        Stage1SupportTicketCategory.ACCOUNT_DELETION,
        Stage1SupportTicketCategory.DATA_EXPORT,
    }:
        return "s1_privacy_rights_review"
    return "s1_customer_support"


def _target_contact_for_category(category: Stage1SupportTicketCategory) -> str:
    if category in {
        Stage1SupportTicketCategory.FAILED_PAYMENT,
        Stage1SupportTicketCategory.REFUND_REQUEST,
    }:
        return STAGE1_REFUND_EMAIL
    if category in {
        Stage1SupportTicketCategory.ACCOUNT_DELETION,
        Stage1SupportTicketCategory.DATA_EXPORT,
    }:
        return STAGE1_PRIVACY_EMAIL
    return STAGE1_SUPPORT_EMAIL


def _ack_sla_for_priority(priority: Stage1SupportTicketPriority) -> int | None:
    if priority == Stage1SupportTicketPriority.P0:
        return STAGE1_SUPPORT_P0_ACK_MINUTES
    if priority == Stage1SupportTicketPriority.P1:
        return STAGE1_SUPPORT_P1_ACK_MINUTES
    return None


def _actions_for_category(
    category: Stage1SupportTicketCategory,
    priority: Stage1SupportTicketPriority,
) -> tuple[str, ...]:
    actions = ["create_support_ticket", "acknowledge_customer", "use_safe_summary_only"]
    if priority == Stage1SupportTicketPriority.P0:
        actions.extend(["escalate_owner", "send_p0_alert"])
    elif priority == Stage1SupportTicketPriority.P1:
        actions.append("send_p1_alert")

    if category in {
        Stage1SupportTicketCategory.FAILED_PAYMENT,
        Stage1SupportTicketCategory.REFUND_REQUEST,
    }:
        actions.extend(["reconcile_provider_dashboard", "route_finance_review"])
    elif category == Stage1SupportTicketCategory.PAID_NO_ACCESS:
        actions.extend(["check_payment_state", "check_provisioning_state", "route_ops_if_access_missing"])
    elif category == Stage1SupportTicketCategory.VPN_NOT_CONNECTING:
        actions.extend(["collect_platform_and_error_time", "verify_subscription_and_device_limit"])
    elif category == Stage1SupportTicketCategory.EXPIRED_SUBSCRIPTION:
        actions.extend(["check_grace_period", "send_renewal_path"])
    elif category == Stage1SupportTicketCategory.ACCOUNT_ACCESS:
        actions.extend(["verify_identity_before_account_action", "do_not_merge_accounts_silently"])
    elif category == Stage1SupportTicketCategory.ACCOUNT_DELETION:
        actions.extend(
            [
                "verify_identity_before_deletion",
                "preserve_required_billing_security_and_legal_records",
                "owner_review_before_destructive_action",
                "record_manual_fulfillment_or_denial_reason",
            ]
        )
    elif category == Stage1SupportTicketCategory.DATA_EXPORT:
        actions.extend(
            [
                "verify_identity_before_export",
                "export_only_portable_account_data",
                "redact_internal_security_provider_fields",
                "deliver_export_through_approved_channel",
            ]
        )
    elif category == Stage1SupportTicketCategory.LEGAL_ABUSE:
        actions.extend(["preserve_audit_trail", "do_not_disclose_private_data_without_approval"])

    return tuple(actions)


def _support_ticket_reference(
    ticket_input: Stage1SupportTicketInput,
    channel: Stage1SupportChannel,
    category: Stage1SupportTicketCategory,
    priority: Stage1SupportTicketPriority,
    safe_summary: str,
) -> str:
    reference_payload = {
        "channel": channel.value,
        "category": category.value,
        "priority": priority.value,
        "safe_summary": safe_summary,
        "customer_reference": ticket_input.customer_reference,
        "payment_reference": ticket_input.payment_reference,
        "telegram_id": str(ticket_input.telegram_id) if ticket_input.telegram_id is not None else None,
        "email": ticket_input.email.casefold().strip() if ticket_input.email else None,
        "external_reference": ticket_input.external_reference,
    }
    digest = hashlib.sha256(
        json.dumps(reference_payload, sort_keys=True, separators=(",", ":")).encode(),
    ).hexdigest()
    channel_prefix = {
        Stage1SupportChannel.TELEGRAM_BOT: "tg",
        Stage1SupportChannel.TELEGRAM_MINI_APP: "tma",
        Stage1SupportChannel.WEB_CONTACT_FORM: "web",
        Stage1SupportChannel.SUPPORT_EMAIL: "email",
        Stage1SupportChannel.REFUND_EMAIL: "refund",
        Stage1SupportChannel.ADMIN_MANUAL: "admin",
    }[channel]
    return f"s1sup-{channel_prefix}-{priority.value}-{digest[:12]}"
