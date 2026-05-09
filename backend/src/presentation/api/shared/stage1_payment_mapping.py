"""S1 provider payment status mapping for paid-access decisions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from src.presentation.api.shared.stage1_contract import Stage1PaymentState, Stage1SupportState


class Stage1PaymentProvider(StrEnum):
    """Owner-approved S1 payment provider set."""

    PAYRAM = "payram"
    NOWPAYMENTS = "nowpayments"
    CRYPTOBOT = "cryptobot"
    TELEGRAM_STARS = "telegram_stars"
    DIGISELLER = "digiseller"
    YOOKASSA = "yookassa"


class Stage1ProviderEvidenceLevel(StrEnum):
    """Evidence level behind a provider mapping row."""

    OFFICIAL_DOCS = "official_docs"
    REAL_CALLBACK_REQUIRED = "real_callback_required"


@dataclass(frozen=True, slots=True)
class Stage1ProviderStatusSource:
    """Official source used for an S1 provider status mapping."""

    provider: Stage1PaymentProvider
    url: str
    retrieved_on: str
    evidence_level: Stage1ProviderEvidenceLevel = Stage1ProviderEvidenceLevel.OFFICIAL_DOCS


@dataclass(frozen=True, slots=True)
class Stage1ProviderPaymentStatusRule:
    """Mapping from provider-specific status/event to CyberVPN S1 payment behavior."""

    provider: Stage1PaymentProvider
    provider_status: str
    payment_state: Stage1PaymentState
    final: bool
    automatic_paid_access_allowed: bool
    manual_review_required: bool
    support_state: Stage1SupportState
    behavior: str
    evidence_level: Stage1ProviderEvidenceLevel = Stage1ProviderEvidenceLevel.OFFICIAL_DOCS


@dataclass(frozen=True, slots=True)
class Stage1ProviderPaymentStatusDecision:
    """Resolved provider status decision for webhook/polling/reconciliation code."""

    provider: Stage1PaymentProvider
    provider_status: str
    normalized_status: str
    payment_state: Stage1PaymentState
    final: bool
    automatic_paid_access_allowed: bool
    manual_review_required: bool
    support_state: Stage1SupportState
    behavior: str
    evidence_level: Stage1ProviderEvidenceLevel

    def to_api_dict(self) -> dict[str, str | bool]:
        """Serialize decision with enum values for API/tests/evidence."""

        return {
            "provider": self.provider.value,
            "provider_status": self.provider_status,
            "normalized_status": self.normalized_status,
            "payment_state": self.payment_state.value,
            "final": self.final,
            "automatic_paid_access_allowed": self.automatic_paid_access_allowed,
            "manual_review_required": self.manual_review_required,
            "support_state": self.support_state.value,
            "behavior": self.behavior,
            "evidence_level": self.evidence_level.value,
        }


STAGE1_PROVIDER_STATUS_SOURCES: dict[Stage1PaymentProvider, Stage1ProviderStatusSource] = {
    Stage1PaymentProvider.PAYRAM: Stage1ProviderStatusSource(
        provider=Stage1PaymentProvider.PAYRAM,
        url="https://docs.payram.com/api-integration/payments-api/payment-status",
        retrieved_on="2026-05-08",
    ),
    Stage1PaymentProvider.NOWPAYMENTS: Stage1ProviderStatusSource(
        provider=Stage1PaymentProvider.NOWPAYMENTS,
        url="https://nowpayments.zendesk.com/hc/en-us/articles/18395434917149-Payment-statuses",
        retrieved_on="2026-05-08",
    ),
    Stage1PaymentProvider.CRYPTOBOT: Stage1ProviderStatusSource(
        provider=Stage1PaymentProvider.CRYPTOBOT,
        url="https://help.send.tg/en/articles/10279948-crypto-pay-api",
        retrieved_on="2026-05-08",
    ),
    Stage1PaymentProvider.TELEGRAM_STARS: Stage1ProviderStatusSource(
        provider=Stage1PaymentProvider.TELEGRAM_STARS,
        url="https://core.telegram.org/bots/payments-stars",
        retrieved_on="2026-05-08",
    ),
    Stage1PaymentProvider.DIGISELLER: Stage1ProviderStatusSource(
        provider=Stage1PaymentProvider.DIGISELLER,
        url="https://my.digiseller.com/inside/api_payment.asp",
        retrieved_on="2026-05-08",
    ),
    Stage1PaymentProvider.YOOKASSA: Stage1ProviderStatusSource(
        provider=Stage1PaymentProvider.YOOKASSA,
        url="https://yookassa.ru/developers/payment-acceptance/getting-started/payment-process",
        retrieved_on="2026-05-08",
    ),
}


def _rule(
    provider: Stage1PaymentProvider,
    provider_status: str,
    payment_state: Stage1PaymentState,
    *,
    final: bool,
    automatic_paid_access_allowed: bool = False,
    manual_review_required: bool = False,
    support_state: Stage1SupportState = Stage1SupportState.NONE,
    behavior: str,
) -> Stage1ProviderPaymentStatusRule:
    return Stage1ProviderPaymentStatusRule(
        provider=provider,
        provider_status=provider_status,
        payment_state=payment_state,
        final=final,
        automatic_paid_access_allowed=automatic_paid_access_allowed,
        manual_review_required=manual_review_required,
        support_state=support_state,
        behavior=behavior,
    )


STAGE1_PROVIDER_STATUS_RULES: dict[Stage1PaymentProvider, dict[str, Stage1ProviderPaymentStatusRule]] = {
    Stage1PaymentProvider.PAYRAM: {
        "open": _rule(
            Stage1PaymentProvider.PAYRAM,
            "OPEN",
            Stage1PaymentState.PENDING,
            final=False,
            behavior="Poll/reconcile PayRam; do not grant paid access.",
        ),
        "filled": _rule(
            Stage1PaymentProvider.PAYRAM,
            "FILLED",
            Stage1PaymentState.PAID,
            final=True,
            automatic_paid_access_allowed=True,
            behavior="Verify API-Key, reference, amount and currency; then paid access may be provisioned.",
        ),
        "over_filled": _rule(
            Stage1PaymentProvider.PAYRAM,
            "OVER_FILLED",
            Stage1PaymentState.RECONCILIATION_REQUIRED,
            final=True,
            manual_review_required=True,
            support_state=Stage1SupportState.SUPPORT_REVIEW,
            behavior="Overpayment requires finance/support review; no automatic access unless explicitly accepted.",
        ),
        "partially_filled": _rule(
            Stage1PaymentProvider.PAYRAM,
            "PARTIALLY_FILLED",
            Stage1PaymentState.RECONCILIATION_REQUIRED,
            final=False,
            manual_review_required=True,
            support_state=Stage1SupportState.SUPPORT_REVIEW,
            behavior="Partial payment is underpaid; do not grant paid access by default.",
        ),
        "cancelled": _rule(
            Stage1PaymentProvider.PAYRAM,
            "CANCELLED",
            Stage1PaymentState.EXPIRED,
            final=True,
            behavior="Payment link expired or was cancelled; user may retry.",
        ),
        "canceled": _rule(
            Stage1PaymentProvider.PAYRAM,
            "CANCELED",
            Stage1PaymentState.EXPIRED,
            final=True,
            behavior="Payment link expired or was canceled; user may retry.",
        ),
    },
    Stage1PaymentProvider.NOWPAYMENTS: {
        "waiting": _rule(
            Stage1PaymentProvider.NOWPAYMENTS,
            "waiting",
            Stage1PaymentState.PENDING,
            final=False,
            behavior="Await deposit; no paid access.",
        ),
        "confirming": _rule(
            Stage1PaymentProvider.NOWPAYMENTS,
            "confirming",
            Stage1PaymentState.PENDING,
            final=False,
            behavior="Await blockchain confirmations; no paid access.",
        ),
        "confirmed": _rule(
            Stage1PaymentProvider.NOWPAYMENTS,
            "confirmed",
            Stage1PaymentState.PENDING,
            final=False,
            behavior="Await finished status; no paid access.",
        ),
        "sending": _rule(
            Stage1PaymentProvider.NOWPAYMENTS,
            "sending",
            Stage1PaymentState.PROCESSING,
            final=False,
            behavior="Provider is sending funds; no paid access until finished.",
        ),
        "finished": _rule(
            Stage1PaymentProvider.NOWPAYMENTS,
            "finished",
            Stage1PaymentState.PAID,
            final=True,
            automatic_paid_access_allowed=True,
            behavior="Verify IPN signature, amount and currency; then paid access may be provisioned.",
        ),
        "partially_paid": _rule(
            Stage1PaymentProvider.NOWPAYMENTS,
            "partially_paid",
            Stage1PaymentState.RECONCILIATION_REQUIRED,
            final=True,
            manual_review_required=True,
            support_state=Stage1SupportState.SUPPORT_REVIEW,
            behavior="Funds were received but underpaid; do not grant paid access by default.",
        ),
        "wrong_asset_confirmed": _rule(
            Stage1PaymentProvider.NOWPAYMENTS,
            "wrong_asset_confirmed",
            Stage1PaymentState.RECONCILIATION_REQUIRED,
            final=True,
            manual_review_required=True,
            support_state=Stage1SupportState.SUPPORT_REVIEW,
            behavior="Wrong asset/network deposit requires manual resolution; no automatic access.",
        ),
        "failed": _rule(
            Stage1PaymentProvider.NOWPAYMENTS,
            "failed",
            Stage1PaymentState.FAILED,
            final=True,
            behavior="Payment failed; no paid access.",
        ),
        "expired": _rule(
            Stage1PaymentProvider.NOWPAYMENTS,
            "expired",
            Stage1PaymentState.EXPIRED,
            final=True,
            behavior="Payment expired; user may retry.",
        ),
        "cancelled": _rule(
            Stage1PaymentProvider.NOWPAYMENTS,
            "cancelled",
            Stage1PaymentState.CANCELLED,
            final=True,
            behavior="Payment was cancelled; no paid access.",
        ),
        "canceled": _rule(
            Stage1PaymentProvider.NOWPAYMENTS,
            "canceled",
            Stage1PaymentState.CANCELLED,
            final=True,
            behavior="Payment was canceled; no paid access.",
        ),
        "refunded": _rule(
            Stage1PaymentProvider.NOWPAYMENTS,
            "refunded",
            Stage1PaymentState.REFUNDED,
            final=True,
            manual_review_required=True,
            support_state=Stage1SupportState.SUPPORT_REVIEW,
            behavior="Refund detected; revoke or adjust access according to refund policy.",
        ),
    },
    Stage1PaymentProvider.CRYPTOBOT: {
        "active": _rule(
            Stage1PaymentProvider.CRYPTOBOT,
            "active",
            Stage1PaymentState.PENDING,
            final=False,
            behavior="Invoice is active; no paid access.",
        ),
        "paid": _rule(
            Stage1PaymentProvider.CRYPTOBOT,
            "paid",
            Stage1PaymentState.PAID,
            final=True,
            automatic_paid_access_allowed=True,
            behavior="Verify Crypto Pay signature and invoice payload; then paid access may be provisioned.",
        ),
        "invoice_paid": _rule(
            Stage1PaymentProvider.CRYPTOBOT,
            "invoice_paid",
            Stage1PaymentState.PAID,
            final=True,
            automatic_paid_access_allowed=True,
            behavior="Webhook update indicates the invoice was paid after signature verification.",
        ),
        "expired": _rule(
            Stage1PaymentProvider.CRYPTOBOT,
            "expired",
            Stage1PaymentState.EXPIRED,
            final=True,
            behavior="Invoice expired; user may retry.",
        ),
    },
    Stage1PaymentProvider.TELEGRAM_STARS: {
        "invoice_sent": _rule(
            Stage1PaymentProvider.TELEGRAM_STARS,
            "invoice_sent",
            Stage1PaymentState.PENDING,
            final=False,
            behavior="Telegram Stars invoice was sent; do not deliver access yet.",
        ),
        "pre_checkout_query": _rule(
            Stage1PaymentProvider.TELEGRAM_STARS,
            "pre_checkout_query",
            Stage1PaymentState.PROCESSING,
            final=False,
            behavior="Answer pre-checkout within 10 seconds; do not deliver access yet.",
        ),
        "successful_payment": _rule(
            Stage1PaymentProvider.TELEGRAM_STARS,
            "successful_payment",
            Stage1PaymentState.PAID,
            final=True,
            automatic_paid_access_allowed=True,
            behavior="Store telegram_payment_charge_id; then paid access may be provisioned.",
        ),
        "payment_timeout": _rule(
            Stage1PaymentProvider.TELEGRAM_STARS,
            "payment_timeout",
            Stage1PaymentState.EXPIRED,
            final=True,
            behavior="No successful_payment was received before timeout; no paid access.",
        ),
        "refund_succeeded": _rule(
            Stage1PaymentProvider.TELEGRAM_STARS,
            "refund_succeeded",
            Stage1PaymentState.REFUNDED,
            final=True,
            manual_review_required=True,
            support_state=Stage1SupportState.SUPPORT_REVIEW,
            behavior="Stars refund succeeded; revoke or adjust access according to refund policy.",
        ),
    },
    Stage1PaymentProvider.DIGISELLER: {
        "wait": _rule(
            Stage1PaymentProvider.DIGISELLER,
            "wait",
            Stage1PaymentState.PENDING,
            final=False,
            behavior="Payment is waiting; no paid access.",
        ),
        "paid": _rule(
            Stage1PaymentProvider.DIGISELLER,
            "paid",
            Stage1PaymentState.PAID,
            final=True,
            automatic_paid_access_allowed=True,
            behavior="Verify signature, amount, currency and invoice id; then paid access may be provisioned.",
        ),
        "canceled": _rule(
            Stage1PaymentProvider.DIGISELLER,
            "canceled",
            Stage1PaymentState.CANCELLED,
            final=True,
            behavior="Payment was canceled; no paid access.",
        ),
        "refunded": _rule(
            Stage1PaymentProvider.DIGISELLER,
            "refunded",
            Stage1PaymentState.REFUNDED,
            final=True,
            manual_review_required=True,
            support_state=Stage1SupportState.SUPPORT_REVIEW,
            behavior="Refund detected; revoke or adjust access according to refund policy.",
        ),
        "error": _rule(
            Stage1PaymentProvider.DIGISELLER,
            "error",
            Stage1PaymentState.FAILED,
            final=True,
            behavior="Provider returned an error; no paid access.",
        ),
    },
    Stage1PaymentProvider.YOOKASSA: {
        "pending": _rule(
            Stage1PaymentProvider.YOOKASSA,
            "pending",
            Stage1PaymentState.PENDING,
            final=False,
            behavior="Payment was created and awaits user/provider action; no paid access.",
        ),
        "waiting_for_capture": _rule(
            Stage1PaymentProvider.YOOKASSA,
            "waiting_for_capture",
            Stage1PaymentState.PROCESSING,
            final=False,
            manual_review_required=True,
            support_state=Stage1SupportState.SUPPORT_REVIEW,
            behavior="Two-stage payment is authorized but not captured; capture before access in S1.",
        ),
        "payment_waiting_for_capture": _rule(
            Stage1PaymentProvider.YOOKASSA,
            "payment.waiting_for_capture",
            Stage1PaymentState.PROCESSING,
            final=False,
            manual_review_required=True,
            support_state=Stage1SupportState.SUPPORT_REVIEW,
            behavior="Webhook event indicates a two-stage payment awaits capture; no access before capture.",
        ),
        "succeeded": _rule(
            Stage1PaymentProvider.YOOKASSA,
            "succeeded",
            Stage1PaymentState.PAID,
            final=True,
            automatic_paid_access_allowed=True,
            behavior="Verify webhook/API state, amount, currency and metadata; then paid access may be provisioned.",
        ),
        "payment_succeeded": _rule(
            Stage1PaymentProvider.YOOKASSA,
            "payment.succeeded",
            Stage1PaymentState.PAID,
            final=True,
            automatic_paid_access_allowed=True,
            behavior="Payment webhook event indicates succeeded after verification.",
        ),
        "canceled": _rule(
            Stage1PaymentProvider.YOOKASSA,
            "canceled",
            Stage1PaymentState.CANCELLED,
            final=True,
            behavior="Payment was canceled; no paid access.",
        ),
        "payment_canceled": _rule(
            Stage1PaymentProvider.YOOKASSA,
            "payment.canceled",
            Stage1PaymentState.CANCELLED,
            final=True,
            behavior="Payment webhook event indicates canceled; no paid access.",
        ),
        "refund_succeeded": _rule(
            Stage1PaymentProvider.YOOKASSA,
            "refund.succeeded",
            Stage1PaymentState.REFUNDED,
            final=True,
            manual_review_required=True,
            support_state=Stage1SupportState.SUPPORT_REVIEW,
            behavior="Refund webhook event indicates succeeded; revoke or adjust access according to refund policy.",
        ),
    },
}


def normalize_provider_status(raw_status: str) -> str:
    """Normalize provider-specific status/event names without accepting empty input."""

    normalized = raw_status.strip().replace("-", "_").replace(" ", "_").replace(".", "_").lower()
    return "_".join(part for part in normalized.split("_") if part)


def _unknown_rule(provider: Stage1PaymentProvider, provider_status: str) -> Stage1ProviderPaymentStatusRule:
    return _rule(
        provider,
        provider_status or "unknown",
        Stage1PaymentState.RECONCILIATION_REQUIRED,
        final=False,
        manual_review_required=True,
        support_state=Stage1SupportState.OPS_ESCALATION,
        behavior="Unknown provider status; block automatic access and escalate for reconciliation.",
    )


def _decimal_or_none(value: Decimal | int | str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def resolve_stage1_provider_payment_status(
    provider: Stage1PaymentProvider | str,
    raw_status: str,
    *,
    amount_expected: Decimal | int | str | None = None,
    amount_received: Decimal | int | str | None = None,
    allow_overpaid_auto_access: bool = False,
) -> Stage1ProviderPaymentStatusDecision:
    """Resolve provider status into the S1 paid-access decision.

    `allow_overpaid_auto_access` is intentionally false by default. S1 should
    not provision overpaid or underpaid flows unless an explicit provider policy
    and amount evidence permit it.
    """

    provider_enum = Stage1PaymentProvider(provider)
    normalized_status = normalize_provider_status(raw_status)
    rule = STAGE1_PROVIDER_STATUS_RULES[provider_enum].get(normalized_status) or _unknown_rule(
        provider_enum,
        raw_status,
    )

    if provider_enum is Stage1PaymentProvider.PAYRAM and normalized_status == "over_filled":
        expected = _decimal_or_none(amount_expected)
        received = _decimal_or_none(amount_received)
        if allow_overpaid_auto_access and expected is not None and received is not None and received >= expected:
            rule = replace(
                rule,
                payment_state=Stage1PaymentState.PAID,
                automatic_paid_access_allowed=True,
                manual_review_required=True,
                support_state=Stage1SupportState.SUPPORT_REVIEW,
                behavior=(
                    "Overpayment amount evidence satisfies expected amount and policy accepted overpaid auto access; "
                    "provision access and keep finance/support review open."
                ),
            )

    return Stage1ProviderPaymentStatusDecision(
        provider=provider_enum,
        provider_status=rule.provider_status,
        normalized_status=normalized_status,
        payment_state=rule.payment_state,
        final=rule.final,
        automatic_paid_access_allowed=rule.automatic_paid_access_allowed,
        manual_review_required=rule.manual_review_required,
        support_state=rule.support_state,
        behavior=rule.behavior,
        evidence_level=rule.evidence_level,
    )


def stage1_provider_status_values(provider: Stage1PaymentProvider | str) -> set[str]:
    """Return normalized statuses covered for a provider."""

    return set(STAGE1_PROVIDER_STATUS_RULES[Stage1PaymentProvider(provider)])


__all__ = [
    "STAGE1_PROVIDER_STATUS_RULES",
    "STAGE1_PROVIDER_STATUS_SOURCES",
    "Stage1PaymentProvider",
    "Stage1ProviderEvidenceLevel",
    "Stage1ProviderPaymentStatusDecision",
    "Stage1ProviderPaymentStatusRule",
    "Stage1ProviderStatusSource",
    "normalize_provider_status",
    "resolve_stage1_provider_payment_status",
    "stage1_provider_status_values",
]
