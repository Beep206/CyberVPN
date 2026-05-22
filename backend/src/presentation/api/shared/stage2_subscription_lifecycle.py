"""S2 subscription lifecycle contract for public B2C release.

This module is intentionally side-effect free. Runtime endpoints may still use
their existing S1 names internally, but S2 needs one customer/support-safe
contract for active access, trial, grace, expiry, refund and renewal copy.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from src.presentation.api.shared.stage1_contract import (
    JsonScalar,
    Stage1AccessState,
    Stage1FlowStatusResponse,
    Stage1PaymentState,
    Stage1ProvisioningState,
    Stage1SupportState,
)

S2_TRIAL_DURATION_DAYS = 3
S2_TRIAL_TRAFFIC_LIMIT_GB = 2
S2_TRIAL_DEVICE_LIMIT = 1
S2_PAID_GRACE_PERIOD_HOURS = 72

S2_PAID_EXPIRY_REMINDER_OFFSETS_HOURS = (72, 24, 3)
S2_TRIAL_EXPIRY_REMINDER_OFFSETS_HOURS = (24, 3)
S2_GRACE_EXPIRY_REMINDER_OFFSETS_HOURS = (24, 3)

S2_AUTOPROLONGATION_REQUIRED_EVIDENCE = (
    "provider_recurring_support",
    "explicit_user_consent",
    "cancel_flow",
    "failed_renewal_handling",
    "renewal_reminders",
    "refund_policy_alignment",
    "webhook_idempotency",
    "staging_smoke",
    "production_smoke",
)


class S2LifecycleAccessKind(StrEnum):
    """Access source for an S2 subscription lifecycle snapshot."""

    TRIAL = "trial"
    PAID_SUBSCRIPTION = "paid_subscription"
    MANUAL_GRANT = "manual_grant"


class S2RefundImpact(StrEnum):
    """How a refund/dispute state should affect customer access."""

    NONE = "none"
    PENDING_REVIEW = "pending_review"
    PARTIAL_REFUND_REVIEW = "partial_refund_review"
    FULL_REFUND_SUCCEEDED = "full_refund_succeeded"


class S2SubscriptionLifecycleState(StrEnum):
    """Customer/support-facing S2 lifecycle states."""

    TRIAL_AVAILABLE = "trial_available"
    TRIAL_ACTIVE = "trial_active"
    ACTIVE = "active"
    GRACE = "grace"
    EXPIRED = "expired"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_FAILED = "payment_failed"
    PROVISIONING_PENDING = "provisioning_pending"
    CONFIG_UNAVAILABLE = "config_unavailable"
    REFUND_REVIEW = "refund_review"
    REFUNDED_SUSPENDED = "refunded_suspended"
    NO_ACCESS = "no_access"


@dataclass(frozen=True, slots=True)
class S2SubscriptionLifecycleSnapshot:
    """Safe inputs needed to evaluate one customer's S2 lifecycle state."""

    observed_at: datetime
    access_kind: S2LifecycleAccessKind | str | None = None
    access_expires_at: datetime | None = None
    trial_used: bool = False
    payment_state: Stage1PaymentState | str = Stage1PaymentState.NOT_STARTED
    provisioning_state: Stage1ProvisioningState | str = Stage1ProvisioningState.NOT_REQUIRED
    config_available: bool = False
    refund_impact: S2RefundImpact | str = S2RefundImpact.NONE
    renewal_invoice_available: bool = False


@dataclass(frozen=True, slots=True)
class S2SubscriptionLifecycleDecision:
    """Redacted S2 lifecycle decision for UI/support/evidence."""

    state: S2SubscriptionLifecycleState
    access_state: Stage1AccessState
    payment_state: Stage1PaymentState
    provisioning_state: Stage1ProvisioningState
    support_state: Stage1SupportState
    config_available: bool
    manual_renewal_allowed: bool
    renewal_invoice_allowed: bool
    recurring_allowed: bool
    user_message_key: str
    user_action: str
    support_escalation: bool = False
    details: dict[str, JsonScalar] | None = None

    def to_flow_status(self) -> Stage1FlowStatusResponse:
        """Serialize through the existing S1 flow response contract."""

        return Stage1FlowStatusResponse(
            access_state=self.access_state,
            payment_state=self.payment_state,
            provisioning_state=self.provisioning_state,
            support_state=self.support_state,
            user_action=self.user_action,
            support_escalation=self.support_escalation,
            details={
                "s2_lifecycle_state": self.state.value,
                "message_key": self.user_message_key,
                "config_available": self.config_available,
                "manual_renewal_allowed": self.manual_renewal_allowed,
                "renewal_invoice_allowed": self.renewal_invoice_allowed,
                "recurring_allowed": self.recurring_allowed,
                **dict(self.details or {}),
            },
        )


@dataclass(frozen=True, slots=True)
class S2AutoprolongationDecision:
    """Decision for enabling true recurring billing/autoprolongation."""

    allowed: bool
    requested: bool
    missing_evidence: tuple[str, ...]
    runtime_flag: str = "PAYMENT_AUTORENEWAL_ENABLED"

    def to_safe_dict(self) -> dict[str, JsonScalar | list[str]]:
        return {
            "allowed": self.allowed,
            "requested": self.requested,
            "missing_evidence": list(self.missing_evidence),
            "runtime_flag": self.runtime_flag,
        }


def evaluate_s2_subscription_lifecycle(
    snapshot: S2SubscriptionLifecycleSnapshot,
) -> S2SubscriptionLifecycleDecision:
    """Evaluate customer lifecycle state without exposing provider secrets."""

    now = _ensure_aware_utc(snapshot.observed_at)
    payment_state = Stage1PaymentState(snapshot.payment_state)
    provisioning_state = Stage1ProvisioningState(snapshot.provisioning_state)
    refund_impact = S2RefundImpact(snapshot.refund_impact)
    access_kind = S2LifecycleAccessKind(snapshot.access_kind) if snapshot.access_kind else None
    access_expires_at = _ensure_aware_utc(snapshot.access_expires_at) if snapshot.access_expires_at else None

    if refund_impact == S2RefundImpact.FULL_REFUND_SUCCEEDED:
        return _decision(
            state=S2SubscriptionLifecycleState.REFUNDED_SUSPENDED,
            access_state=Stage1AccessState.SUSPENDED,
            payment_state=Stage1PaymentState.REFUNDED,
            provisioning_state=Stage1ProvisioningState.SUSPENDED,
            support_state=Stage1SupportState.SUPPORT_REVIEW,
            config_available=False,
            manual_renewal_allowed=True,
            renewal_invoice_allowed=False,
            user_message_key="subscription.refunded_suspended",
            user_action="Refund is recorded for this billing period. Contact support before expecting access.",
            support_escalation=True,
            details={"refund_impact": refund_impact.value},
        )

    if refund_impact in {S2RefundImpact.PENDING_REVIEW, S2RefundImpact.PARTIAL_REFUND_REVIEW}:
        base = _evaluate_non_refund_lifecycle(
            now=now,
            access_kind=access_kind,
            access_expires_at=access_expires_at,
            trial_used=snapshot.trial_used,
            payment_state=payment_state,
            provisioning_state=provisioning_state,
            config_available=snapshot.config_available,
            renewal_invoice_available=snapshot.renewal_invoice_available,
        )
        return _decision(
            state=S2SubscriptionLifecycleState.REFUND_REVIEW,
            access_state=base.access_state,
            payment_state=Stage1PaymentState.REFUNDED
            if refund_impact == S2RefundImpact.PARTIAL_REFUND_REVIEW
            else base.payment_state,
            provisioning_state=base.provisioning_state,
            support_state=Stage1SupportState.SUPPORT_REVIEW,
            config_available=base.config_available,
            manual_renewal_allowed=base.manual_renewal_allowed,
            renewal_invoice_allowed=False,
            user_message_key="subscription.refund_review",
            user_action="Refund request is under support/finance review; access changes are not automatic.",
            support_escalation=True,
            details={"refund_impact": refund_impact.value},
        )

    return _evaluate_non_refund_lifecycle(
        now=now,
        access_kind=access_kind,
        access_expires_at=access_expires_at,
        trial_used=snapshot.trial_used,
        payment_state=payment_state,
        provisioning_state=provisioning_state,
        config_available=snapshot.config_available,
        renewal_invoice_available=snapshot.renewal_invoice_available,
    )


def build_s2_expiry_reminder_schedule(
    *,
    access_kind: S2LifecycleAccessKind | str,
    access_expires_at: datetime,
) -> tuple[datetime, ...]:
    """Return deterministic reminder times before access expiry."""

    expires_at = _ensure_aware_utc(access_expires_at)
    kind = S2LifecycleAccessKind(access_kind)
    offsets = (
        S2_TRIAL_EXPIRY_REMINDER_OFFSETS_HOURS
        if kind == S2LifecycleAccessKind.TRIAL
        else S2_PAID_EXPIRY_REMINDER_OFFSETS_HOURS
    )
    return tuple(expires_at - timedelta(hours=hours) for hours in offsets)


def build_s2_grace_reminder_schedule(*, access_expires_at: datetime) -> tuple[datetime, ...]:
    """Return reminder times before the paid grace period closes."""

    grace_ends_at = _ensure_aware_utc(access_expires_at) + timedelta(hours=S2_PAID_GRACE_PERIOD_HOURS)
    return tuple(grace_ends_at - timedelta(hours=hours) for hours in S2_GRACE_EXPIRY_REMINDER_OFFSETS_HOURS)


def evaluate_s2_autoprolongation_readiness(
    completed_evidence: Iterable[str],
    *,
    requested: bool,
) -> S2AutoprolongationDecision:
    """Keep true recurring billing closed until every evidence item exists."""

    completed = frozenset(completed_evidence)
    missing = tuple(item for item in S2_AUTOPROLONGATION_REQUIRED_EVIDENCE if item not in completed)
    return S2AutoprolongationDecision(
        allowed=requested and not missing,
        requested=requested,
        missing_evidence=missing,
    )


def build_s2_manual_renewal_steps() -> tuple[str, ...]:
    """Support-safe manual renewal process for S2."""

    return (
        "open_public_catalog_or_mini_app_plans",
        "choose_plan_and_period",
        "create_new_checkout_invoice",
        "wait_for_provider_final_success",
        "run_paid_provisioning_or_extend_existing_access",
        "show_subscription_url_config_and_expiry",
        "record_payment_attempt_and_reconciliation_state",
    )


def _evaluate_non_refund_lifecycle(
    *,
    now: datetime,
    access_kind: S2LifecycleAccessKind | None,
    access_expires_at: datetime | None,
    trial_used: bool,
    payment_state: Stage1PaymentState,
    provisioning_state: Stage1ProvisioningState,
    config_available: bool,
    renewal_invoice_available: bool,
) -> S2SubscriptionLifecycleDecision:
    if payment_state in {Stage1PaymentState.PENDING, Stage1PaymentState.PROCESSING}:
        return _decision(
            state=S2SubscriptionLifecycleState.PAYMENT_PENDING,
            access_state=Stage1AccessState.PAYMENT_PENDING,
            payment_state=payment_state,
            provisioning_state=Stage1ProvisioningState.NOT_REQUIRED,
            support_state=Stage1SupportState.SELF_SERVICE,
            config_available=False,
            manual_renewal_allowed=False,
            renewal_invoice_allowed=False,
            user_message_key="subscription.payment_pending",
            user_action="Wait for payment confirmation or contact support if the provider shows paid.",
        )

    if payment_state in {Stage1PaymentState.FAILED, Stage1PaymentState.CANCELLED, Stage1PaymentState.EXPIRED}:
        return _decision(
            state=S2SubscriptionLifecycleState.PAYMENT_FAILED,
            access_state=Stage1AccessState.NO_ACCESS,
            payment_state=payment_state,
            provisioning_state=Stage1ProvisioningState.NOT_REQUIRED,
            support_state=Stage1SupportState.SELF_SERVICE,
            config_available=False,
            manual_renewal_allowed=True,
            renewal_invoice_allowed=True,
            user_message_key="subscription.payment_failed",
            user_action="Create a new manual renewal invoice or choose another payment method.",
        )

    if provisioning_state in {
        Stage1ProvisioningState.QUEUED,
        Stage1ProvisioningState.PENDING,
        Stage1ProvisioningState.PROVISIONING,
        Stage1ProvisioningState.RETRYING,
    }:
        return _decision(
            state=S2SubscriptionLifecycleState.PROVISIONING_PENDING,
            access_state=Stage1AccessState.PROVISIONING_PENDING,
            payment_state=payment_state,
            provisioning_state=provisioning_state,
            support_state=Stage1SupportState.SELF_SERVICE,
            config_available=False,
            manual_renewal_allowed=False,
            renewal_invoice_allowed=False,
            user_message_key="subscription.provisioning_pending",
            user_action="Wait for VPN provisioning to finish; support can review if it stalls.",
        )

    if provisioning_state in {
        Stage1ProvisioningState.FAILED,
        Stage1ProvisioningState.RECONCILIATION_REQUIRED,
        Stage1ProvisioningState.REMNAWAVE_UNAVAILABLE,
    }:
        return _decision(
            state=S2SubscriptionLifecycleState.CONFIG_UNAVAILABLE,
            access_state=Stage1AccessState.PROVISIONING_PENDING,
            payment_state=payment_state,
            provisioning_state=provisioning_state,
            support_state=Stage1SupportState.SUPPORT_REVIEW,
            config_available=False,
            manual_renewal_allowed=False,
            renewal_invoice_allowed=False,
            user_message_key="subscription.config_unavailable",
            user_action="Support must restore VPN configuration or reconcile provisioning.",
            support_escalation=True,
        )

    if access_expires_at is None:
        if not trial_used:
            return _decision(
                state=S2SubscriptionLifecycleState.TRIAL_AVAILABLE,
                access_state=Stage1AccessState.TRIAL_AVAILABLE,
                payment_state=payment_state,
                provisioning_state=Stage1ProvisioningState.NOT_REQUIRED,
                support_state=Stage1SupportState.SELF_SERVICE,
                config_available=False,
                manual_renewal_allowed=True,
                renewal_invoice_allowed=True,
                user_message_key="subscription.trial_available",
                user_action="Activate the one-time trial or choose a paid plan.",
                details={
                    "trial_days": S2_TRIAL_DURATION_DAYS,
                    "trial_traffic_gb": S2_TRIAL_TRAFFIC_LIMIT_GB,
                    "trial_device_limit": S2_TRIAL_DEVICE_LIMIT,
                },
            )
        return _decision(
            state=S2SubscriptionLifecycleState.NO_ACCESS,
            access_state=Stage1AccessState.NO_ACCESS,
            payment_state=payment_state,
            provisioning_state=Stage1ProvisioningState.NOT_REQUIRED,
            support_state=Stage1SupportState.SELF_SERVICE,
            config_available=False,
            manual_renewal_allowed=True,
            renewal_invoice_allowed=True,
            user_message_key="subscription.no_access",
            user_action="Choose a paid plan or redeem an approved access code.",
        )

    if now < access_expires_at:
        state = (
            S2SubscriptionLifecycleState.TRIAL_ACTIVE
            if access_kind == S2LifecycleAccessKind.TRIAL
            else S2SubscriptionLifecycleState.ACTIVE
        )
        access_state = (
            Stage1AccessState.TRIAL_ACTIVE
            if access_kind == S2LifecycleAccessKind.TRIAL
            else Stage1AccessState.ACTIVE
        )
        return _decision(
            state=state,
            access_state=access_state,
            payment_state=payment_state,
            provisioning_state=Stage1ProvisioningState.READY,
            support_state=Stage1SupportState.NONE,
            config_available=config_available,
            manual_renewal_allowed=True,
            renewal_invoice_allowed=renewal_invoice_available,
            user_message_key=f"subscription.{state.value}",
            user_action="Access is active. Manual renewal is available before expiry.",
            details={"access_expires_at": access_expires_at.isoformat()},
        )

    if access_kind == S2LifecycleAccessKind.TRIAL:
        return _decision(
            state=S2SubscriptionLifecycleState.EXPIRED,
            access_state=Stage1AccessState.EXPIRED,
            payment_state=payment_state,
            provisioning_state=Stage1ProvisioningState.EXPIRED,
            support_state=Stage1SupportState.SELF_SERVICE,
            config_available=False,
            manual_renewal_allowed=True,
            renewal_invoice_allowed=True,
            user_message_key="subscription.expired",
            user_action="Trial ended. Choose a paid plan to continue.",
            details={"trial_repeat_allowed": False},
        )

    grace_ends_at = access_expires_at + timedelta(hours=S2_PAID_GRACE_PERIOD_HOURS)
    if now < grace_ends_at:
        return _decision(
            state=S2SubscriptionLifecycleState.GRACE,
            access_state=Stage1AccessState.GRACE,
            payment_state=payment_state,
            provisioning_state=Stage1ProvisioningState.READY,
            support_state=Stage1SupportState.SELF_SERVICE,
            config_available=config_available,
            manual_renewal_allowed=True,
            renewal_invoice_allowed=True,
            user_message_key="subscription.grace",
            user_action="Renew manually before the 72-hour grace period closes.",
            details={
                "access_expires_at": access_expires_at.isoformat(),
                "grace_ends_at": grace_ends_at.isoformat(),
            },
        )

    return _decision(
        state=S2SubscriptionLifecycleState.EXPIRED,
        access_state=Stage1AccessState.EXPIRED,
        payment_state=payment_state,
        provisioning_state=Stage1ProvisioningState.SUSPENDED,
        support_state=Stage1SupportState.SELF_SERVICE,
        config_available=False,
        manual_renewal_allowed=True,
        renewal_invoice_allowed=True,
        user_message_key="subscription.expired",
        user_action="Renew manually or contact support if payment was already made.",
        details={
            "access_expires_at": access_expires_at.isoformat(),
            "grace_ends_at": grace_ends_at.isoformat(),
        },
    )


def _decision(
    *,
    state: S2SubscriptionLifecycleState,
    access_state: Stage1AccessState,
    payment_state: Stage1PaymentState,
    provisioning_state: Stage1ProvisioningState,
    support_state: Stage1SupportState,
    config_available: bool,
    manual_renewal_allowed: bool,
    renewal_invoice_allowed: bool,
    user_message_key: str,
    user_action: str,
    support_escalation: bool = False,
    details: dict[str, JsonScalar] | None = None,
) -> S2SubscriptionLifecycleDecision:
    return S2SubscriptionLifecycleDecision(
        state=state,
        access_state=access_state,
        payment_state=payment_state,
        provisioning_state=provisioning_state,
        support_state=support_state,
        config_available=config_available,
        manual_renewal_allowed=manual_renewal_allowed,
        renewal_invoice_allowed=renewal_invoice_allowed,
        recurring_allowed=False,
        user_message_key=user_message_key,
        user_action=user_action,
        support_escalation=support_escalation,
        details=details,
    )


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "S2_AUTOPROLONGATION_REQUIRED_EVIDENCE",
    "S2_GRACE_EXPIRY_REMINDER_OFFSETS_HOURS",
    "S2_PAID_EXPIRY_REMINDER_OFFSETS_HOURS",
    "S2_PAID_GRACE_PERIOD_HOURS",
    "S2_TRIAL_DEVICE_LIMIT",
    "S2_TRIAL_DURATION_DAYS",
    "S2_TRIAL_EXPIRY_REMINDER_OFFSETS_HOURS",
    "S2_TRIAL_TRAFFIC_LIMIT_GB",
    "S2AutoprolongationDecision",
    "S2LifecycleAccessKind",
    "S2RefundImpact",
    "S2SubscriptionLifecycleDecision",
    "S2SubscriptionLifecycleSnapshot",
    "S2SubscriptionLifecycleState",
    "build_s2_expiry_reminder_schedule",
    "build_s2_grace_reminder_schedule",
    "build_s2_manual_renewal_steps",
    "evaluate_s2_autoprolongation_readiness",
    "evaluate_s2_subscription_lifecycle",
]
