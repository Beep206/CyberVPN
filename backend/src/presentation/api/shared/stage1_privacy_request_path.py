"""S1 privacy request routing contract for account deletion and data export.

The S1 beta keeps privacy rights handling deliberately controlled. Users can
submit a request, support verifies ownership, and owner/support complete the
manual action through an auditable path. This module does not perform the
destructive action or generate a raw data export.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from src.presentation.api.shared.stage1_support_escalation import (
    Stage1SupportEscalationDecision,
    build_stage1_support_escalation_decision,
)
from src.presentation.api.shared.stage1_support_ticket_path import (
    STAGE1_PRIVACY_EMAIL,
    Stage1SupportChannel,
    Stage1SupportTicketCategory,
    Stage1SupportTicketDecision,
    Stage1SupportTicketInput,
    build_stage1_support_ticket,
)

STAGE1_PRIVACY_MANUAL_FULFILLMENT_TARGET_DAYS = 30


class Stage1PrivacyRequestKind(StrEnum):
    """S1 privacy request kinds exposed to web, Telegram and support surfaces."""

    ACCOUNT_DELETION = "account_deletion"
    DATA_EXPORT = "data_export"


@dataclass(frozen=True, slots=True)
class Stage1PrivacyRequestInput:
    """Input for a user privacy request without raw sensitive payloads."""

    request_kind: Stage1PrivacyRequestKind | str
    channel: Stage1SupportChannel | str
    user_reference: str
    contact: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class Stage1PrivacyRequestDecision:
    """Safe privacy request routing decision for API responses and runbooks."""

    request_kind: Stage1PrivacyRequestKind
    ticket: Stage1SupportTicketDecision
    escalation: Stage1SupportEscalationDecision
    manual_fulfillment_target_days: int = STAGE1_PRIVACY_MANUAL_FULFILLMENT_TARGET_DAYS

    def to_api_dict(self) -> dict[str, object]:
        """Serialize only the safe request metadata returned to a user/client."""

        return {
            "request_type": self.request_kind.value,
            "message": _message_for_kind(self.request_kind),
            "ticket_reference": self.ticket.reference,
            "target_contact": self.ticket.target_contact,
            "priority": self.ticket.priority.value,
            "support_state": self.ticket.support_state.value,
            "ack_sla_minutes": self.ticket.ack_sla_minutes,
            "customer_response_sla_minutes": self.ticket.customer_response_sla_minutes,
            "manual_fulfillment_target_days": self.manual_fulfillment_target_days,
            "required_actions": list(self.escalation.rule.required_actions),
            "forbidden_actions": list(self.escalation.rule.forbidden_actions),
            "audit_required": self.escalation.rule.audit_required,
        }

    def to_staff_note(self) -> str:
        """Render a support-safe staff note without user-provided raw text."""

        return "\n".join(
            [
                "S1 privacy request",
                f"Request type: {self.request_kind.value}",
                f"Ticket: {self.ticket.reference}",
                f"Queue: {self.ticket.target_queue}",
                f"Contact: {self.ticket.target_contact}",
                f"Escalation owner: {self.escalation.rule.target_owner.value}",
                f"Manual fulfillment target days: {self.manual_fulfillment_target_days}",
            ]
        )


def build_stage1_privacy_request(
    request_input: Stage1PrivacyRequestInput,
) -> Stage1PrivacyRequestDecision:
    """Build the S1 delete/export privacy request path."""

    request_kind = _coerce_request_kind(request_input.request_kind)
    category = _category_for_kind(request_kind)
    summary = _build_safe_request_summary(request_input, request_kind)
    ticket = build_stage1_support_ticket(
        Stage1SupportTicketInput(
            channel=request_input.channel,
            category=category,
            summary=summary,
            customer_reference=request_input.user_reference,
            email=request_input.contact,
        )
    )
    escalation = build_stage1_support_escalation_decision(ticket)

    return Stage1PrivacyRequestDecision(
        request_kind=request_kind,
        ticket=ticket,
        escalation=escalation,
    )


def _coerce_request_kind(value: Stage1PrivacyRequestKind | str) -> Stage1PrivacyRequestKind:
    if isinstance(value, Stage1PrivacyRequestKind):
        return value
    try:
        return Stage1PrivacyRequestKind(str(value))
    except ValueError as exc:
        raise ValueError(f"Unsupported Stage1PrivacyRequestKind: {value}") from exc


def _category_for_kind(request_kind: Stage1PrivacyRequestKind) -> Stage1SupportTicketCategory:
    if request_kind == Stage1PrivacyRequestKind.ACCOUNT_DELETION:
        return Stage1SupportTicketCategory.ACCOUNT_DELETION
    return Stage1SupportTicketCategory.DATA_EXPORT


def _build_safe_request_summary(
    request_input: Stage1PrivacyRequestInput,
    request_kind: Stage1PrivacyRequestKind,
) -> str:
    notes = request_input.notes.strip() if request_input.notes else "no optional notes"
    return (
        f"S1 privacy request: {request_kind.value}. "
        f"User reference: {request_input.user_reference}. "
        f"Privacy contact: {request_input.contact or STAGE1_PRIVACY_EMAIL}. "
        f"Notes: {notes}"
    )


def _message_for_kind(request_kind: Stage1PrivacyRequestKind) -> str:
    if request_kind == Stage1PrivacyRequestKind.ACCOUNT_DELETION:
        return "Account deletion request accepted for manual privacy review."
    return "Data export request accepted for manual privacy review."
