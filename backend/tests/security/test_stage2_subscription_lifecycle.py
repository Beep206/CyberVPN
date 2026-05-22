"""S2-STAGE-07 subscription lifecycle contract checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.application.use_cases.subscriptions.stage1_expiry_grace_disable import STAGE1_PAID_GRACE_PERIOD_HOURS
from src.presentation.api.shared.stage1_contract import (
    Stage1AccessState,
    Stage1PaymentState,
    Stage1ProvisioningState,
    Stage1SupportState,
)
from src.presentation.api.shared.stage2_subscription_lifecycle import (
    S2_AUTOPROLONGATION_REQUIRED_EVIDENCE,
    S2_PAID_GRACE_PERIOD_HOURS,
    S2_TRIAL_DEVICE_LIMIT,
    S2_TRIAL_DURATION_DAYS,
    S2_TRIAL_TRAFFIC_LIMIT_GB,
    S2LifecycleAccessKind,
    S2RefundImpact,
    S2SubscriptionLifecycleSnapshot,
    S2SubscriptionLifecycleState,
    build_s2_expiry_reminder_schedule,
    build_s2_grace_reminder_schedule,
    build_s2_manual_renewal_steps,
    evaluate_s2_autoprolongation_readiness,
    evaluate_s2_subscription_lifecycle,
)


def test_s2_trial_contract_is_one_time_three_days_two_gb_one_device() -> None:
    now = datetime(2026, 5, 22, 9, 0, tzinfo=UTC)

    available = evaluate_s2_subscription_lifecycle(S2SubscriptionLifecycleSnapshot(observed_at=now))
    spent = evaluate_s2_subscription_lifecycle(
        S2SubscriptionLifecycleSnapshot(observed_at=now, trial_used=True)
    )

    assert S2_TRIAL_DURATION_DAYS == 3
    assert S2_TRIAL_TRAFFIC_LIMIT_GB == 2
    assert S2_TRIAL_DEVICE_LIMIT == 1
    assert available.state == S2SubscriptionLifecycleState.TRIAL_AVAILABLE
    assert available.access_state == Stage1AccessState.TRIAL_AVAILABLE
    assert available.details == {
        "trial_days": 3,
        "trial_traffic_gb": 2,
        "trial_device_limit": 1,
    }
    assert spent.state == S2SubscriptionLifecycleState.NO_ACCESS
    assert spent.manual_renewal_allowed is True


def test_s2_paid_access_grace_matches_s1_72h_policy_and_expires_after_boundary() -> None:
    expires_at = datetime(2026, 5, 22, 9, 0, tzinfo=UTC)

    grace = evaluate_s2_subscription_lifecycle(
        S2SubscriptionLifecycleSnapshot(
            observed_at=expires_at + timedelta(hours=72, seconds=-1),
            access_kind=S2LifecycleAccessKind.PAID_SUBSCRIPTION,
            access_expires_at=expires_at,
            payment_state=Stage1PaymentState.PAID,
            provisioning_state=Stage1ProvisioningState.READY,
            config_available=True,
            renewal_invoice_available=True,
        )
    )
    expired = evaluate_s2_subscription_lifecycle(
        S2SubscriptionLifecycleSnapshot(
            observed_at=expires_at + timedelta(hours=72),
            access_kind=S2LifecycleAccessKind.PAID_SUBSCRIPTION,
            access_expires_at=expires_at,
            payment_state=Stage1PaymentState.PAID,
            provisioning_state=Stage1ProvisioningState.READY,
            config_available=True,
        )
    )

    assert S2_PAID_GRACE_PERIOD_HOURS == STAGE1_PAID_GRACE_PERIOD_HOURS == 72
    assert grace.state == S2SubscriptionLifecycleState.GRACE
    assert grace.access_state == Stage1AccessState.GRACE
    assert grace.provisioning_state == Stage1ProvisioningState.READY
    assert grace.config_available is True
    assert grace.renewal_invoice_allowed is True
    assert expired.state == S2SubscriptionLifecycleState.EXPIRED
    assert expired.access_state == Stage1AccessState.EXPIRED
    assert expired.provisioning_state == Stage1ProvisioningState.SUSPENDED
    assert expired.config_available is False


def test_s2_trial_has_no_grace_and_no_repeat_trial_after_expiry() -> None:
    expires_at = datetime(2026, 5, 22, 9, 0, tzinfo=UTC)

    decision = evaluate_s2_subscription_lifecycle(
        S2SubscriptionLifecycleSnapshot(
            observed_at=expires_at,
            access_kind=S2LifecycleAccessKind.TRIAL,
            access_expires_at=expires_at,
            payment_state=Stage1PaymentState.NOT_STARTED,
            provisioning_state=Stage1ProvisioningState.READY,
            config_available=True,
        )
    )

    assert decision.state == S2SubscriptionLifecycleState.EXPIRED
    assert decision.access_state == Stage1AccessState.EXPIRED
    assert decision.provisioning_state == Stage1ProvisioningState.EXPIRED
    assert decision.config_available is False
    assert decision.details == {"trial_repeat_allowed": False}


def test_s2_payment_pending_and_failed_states_are_customer_visible() -> None:
    now = datetime(2026, 5, 22, 9, 0, tzinfo=UTC)

    pending = evaluate_s2_subscription_lifecycle(
        S2SubscriptionLifecycleSnapshot(
            observed_at=now,
            payment_state=Stage1PaymentState.PENDING,
        )
    )
    failed = evaluate_s2_subscription_lifecycle(
        S2SubscriptionLifecycleSnapshot(
            observed_at=now,
            payment_state=Stage1PaymentState.FAILED,
        )
    )

    assert pending.state == S2SubscriptionLifecycleState.PAYMENT_PENDING
    assert pending.access_state == Stage1AccessState.PAYMENT_PENDING
    assert pending.support_state == Stage1SupportState.SELF_SERVICE
    assert pending.renewal_invoice_allowed is False
    assert failed.state == S2SubscriptionLifecycleState.PAYMENT_FAILED
    assert failed.access_state == Stage1AccessState.NO_ACCESS
    assert failed.manual_renewal_allowed is True
    assert failed.renewal_invoice_allowed is True


def test_s2_provisioning_and_config_unavailable_states_are_distinct() -> None:
    now = datetime(2026, 5, 22, 9, 0, tzinfo=UTC)

    queued = evaluate_s2_subscription_lifecycle(
        S2SubscriptionLifecycleSnapshot(
            observed_at=now,
            payment_state=Stage1PaymentState.PAID,
            provisioning_state=Stage1ProvisioningState.QUEUED,
        )
    )
    failed = evaluate_s2_subscription_lifecycle(
        S2SubscriptionLifecycleSnapshot(
            observed_at=now,
            payment_state=Stage1PaymentState.PAID,
            provisioning_state=Stage1ProvisioningState.FAILED,
        )
    )

    assert queued.state == S2SubscriptionLifecycleState.PROVISIONING_PENDING
    assert queued.access_state == Stage1AccessState.PROVISIONING_PENDING
    assert queued.config_available is False
    assert failed.state == S2SubscriptionLifecycleState.CONFIG_UNAVAILABLE
    assert failed.support_state == Stage1SupportState.SUPPORT_REVIEW
    assert failed.support_escalation is True
    assert failed.config_available is False


def test_s2_refund_states_do_not_promise_automatic_refund_or_silent_access_loss() -> None:
    now = datetime(2026, 5, 22, 9, 0, tzinfo=UTC)
    expires_at = now + timedelta(days=20)

    pending = evaluate_s2_subscription_lifecycle(
        S2SubscriptionLifecycleSnapshot(
            observed_at=now,
            access_kind=S2LifecycleAccessKind.PAID_SUBSCRIPTION,
            access_expires_at=expires_at,
            payment_state=Stage1PaymentState.PAID,
            provisioning_state=Stage1ProvisioningState.READY,
            config_available=True,
            refund_impact=S2RefundImpact.PENDING_REVIEW,
        )
    )
    full = evaluate_s2_subscription_lifecycle(
        S2SubscriptionLifecycleSnapshot(
            observed_at=now,
            access_kind=S2LifecycleAccessKind.PAID_SUBSCRIPTION,
            access_expires_at=expires_at,
            payment_state=Stage1PaymentState.PAID,
            provisioning_state=Stage1ProvisioningState.READY,
            config_available=True,
            refund_impact=S2RefundImpact.FULL_REFUND_SUCCEEDED,
        )
    )

    assert pending.state == S2SubscriptionLifecycleState.REFUND_REVIEW
    assert pending.access_state == Stage1AccessState.ACTIVE
    assert pending.config_available is True
    assert "not automatic" in pending.user_action.lower()
    assert full.state == S2SubscriptionLifecycleState.REFUNDED_SUSPENDED
    assert full.access_state == Stage1AccessState.SUSPENDED
    assert full.payment_state == Stage1PaymentState.REFUNDED
    assert full.provisioning_state == Stage1ProvisioningState.SUSPENDED
    assert full.config_available is False
    assert full.support_escalation is True


def test_s2_manual_renewal_and_reminder_contract_is_deterministic_and_secret_free() -> None:
    expires_at = datetime(2026, 5, 22, 9, 0, tzinfo=UTC)

    paid_schedule = build_s2_expiry_reminder_schedule(
        access_kind=S2LifecycleAccessKind.PAID_SUBSCRIPTION,
        access_expires_at=expires_at,
    )
    trial_schedule = build_s2_expiry_reminder_schedule(
        access_kind=S2LifecycleAccessKind.TRIAL,
        access_expires_at=expires_at,
    )
    grace_schedule = build_s2_grace_reminder_schedule(access_expires_at=expires_at)
    steps = build_s2_manual_renewal_steps()

    assert paid_schedule == (
        expires_at - timedelta(hours=72),
        expires_at - timedelta(hours=24),
        expires_at - timedelta(hours=3),
    )
    assert trial_schedule == (expires_at - timedelta(hours=24), expires_at - timedelta(hours=3))
    assert grace_schedule == (
        expires_at + timedelta(hours=48),
        expires_at + timedelta(hours=69),
    )
    assert steps[0] == "open_public_catalog_or_mini_app_plans"
    assert steps[-1] == "record_payment_attempt_and_reconciliation_state"
    serialized = str((paid_schedule, trial_schedule, grace_schedule, steps)).lower()
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "password" not in serialized


def test_s2_autoprolongation_requires_all_evidence_before_enabled() -> None:
    incomplete = evaluate_s2_autoprolongation_readiness(
        ["provider_recurring_support", "explicit_user_consent"],
        requested=True,
    )
    complete = evaluate_s2_autoprolongation_readiness(
        S2_AUTOPROLONGATION_REQUIRED_EVIDENCE,
        requested=True,
    )
    not_requested = evaluate_s2_autoprolongation_readiness(
        S2_AUTOPROLONGATION_REQUIRED_EVIDENCE,
        requested=False,
    )

    assert incomplete.allowed is False
    assert "cancel_flow" in incomplete.missing_evidence
    assert complete.allowed is True
    assert complete.missing_evidence == ()
    assert not_requested.allowed is False
    assert not_requested.missing_evidence == ()
    assert complete.runtime_flag == "PAYMENT_AUTORENEWAL_ENABLED"


def test_s2_flow_status_output_is_redacted_and_ui_addressable() -> None:
    now = datetime(2026, 5, 22, 9, 0, tzinfo=UTC)
    decision = evaluate_s2_subscription_lifecycle(
        S2SubscriptionLifecycleSnapshot(
            observed_at=now,
            payment_state=Stage1PaymentState.PAID,
            provisioning_state=Stage1ProvisioningState.REMNAWAVE_UNAVAILABLE,
        )
    )

    flow = decision.to_flow_status()

    assert flow.details["s2_lifecycle_state"] == "config_unavailable"
    assert flow.details["message_key"] == "subscription.config_unavailable"
    assert flow.support_escalation is True
    serialized = str(flow.model_dump()).lower()
    assert "https://" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "password" not in serialized
