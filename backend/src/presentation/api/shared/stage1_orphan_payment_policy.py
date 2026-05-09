"""S1 orphan payment and paid-but-no-access policy helpers."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any

from src.presentation.api.shared.stage1_contract import (
    Stage1AccessState,
    Stage1ErrorCode,
    Stage1FlowStatusResponse,
    Stage1PaymentState,
    Stage1ProvisioningState,
    Stage1SupportState,
)
from src.presentation.api.shared.stage1_payment_mapping import Stage1PaymentProvider

STAGE1_ORPHAN_ALERT_AFTER_MINUTES = 15
STAGE1_ORPHAN_P1_AFTER_MINUTES = 60
STAGE1_ORPHAN_P0_AFTER_MINUTES = 24 * 60


class Stage1OrphanPaymentReason(StrEnum):
    """Reason a payment needs manual S1 review."""

    NONE = "none"
    USER_NOT_FOUND = "user_not_found"
    ORDER_NOT_FOUND = "order_not_found"
    PAID_BUT_ACCESS_NOT_READY = "paid_but_access_not_ready"
    PROVISIONING_FAILED = "provisioning_failed"
    REMNAWAVE_UNAVAILABLE = "remnawave_unavailable"
    AMOUNT_CURRENCY_MISMATCH = "amount_currency_mismatch"
    PROVIDER_SUCCESS_AFTER_TIMEOUT = "provider_success_after_timeout"
    USER_REPORTED_DEBIT_PROVIDER_PENDING = "user_reported_debit_provider_pending"
    RESOLVED = "resolved"


class Stage1OrphanPaymentSlaState(StrEnum):
    """S1 SLA state for orphan and paid-but-no-access cases."""

    OK = "ok"
    MANUAL_REVIEW = "manual_review"
    ALERT_15M = "alert_15m"
    P1_ESCALATION = "p1_escalation"
    P0_BLOCKER = "p0_blocker"


class Stage1OrphanPaymentAction(StrEnum):
    """Operational actions required by the S1 orphan payment policy."""

    CREATE_MANUAL_REVIEW_ITEM = "create_manual_review_item"
    CREATE_SUPPORT_TICKET = "create_support_ticket"
    ALERT_SUPPORT_FINANCE = "alert_support_finance"
    RECONCILE_PROVIDER_DASHBOARD = "reconcile_provider_dashboard"
    PRESERVE_PAID_STATE = "preserve_paid_state"
    QUEUE_PROVISIONING_RETRY = "queue_provisioning_retry"
    BLOCK_AUTOMATIC_ACCESS = "block_automatic_access"
    DO_NOT_CREATE_ACCOUNT_SILENTLY = "do_not_create_account_silently"
    REOPEN_RECONCILIATION = "reopen_reconciliation"
    SEND_PAID_WITHOUT_ACCESS_ALERT = "send_paid_without_access_alert"
    P1_SUPPORT_OPS_ESCALATION = "p1_support_ops_escalation"
    P0_LAUNCH_BLOCKER = "p0_launch_blocker"


@dataclass(frozen=True, slots=True)
class Stage1PaymentAccessSnapshot:
    """Input snapshot for local S1 orphan payment policy evaluation."""

    provider: Stage1PaymentProvider | str
    provider_payment_id: str
    detected_at: datetime
    observed_at: datetime
    payment_id: str | None = None
    payment_state: Stage1PaymentState | str = Stage1PaymentState.PAID
    provisioning_state: Stage1ProvisioningState | str = Stage1ProvisioningState.PENDING
    user_found: bool = True
    order_found: bool = True
    amount_currency_match: bool = True
    access_ready: bool = False
    provider_final_success_after_timeout: bool = False
    user_reported_debit_provider_pending: bool = False
    resolved: bool = False


@dataclass(frozen=True, slots=True)
class Stage1OrphanPaymentDecision:
    """Machine-readable decision for support/admin/payment orchestration."""

    provider: Stage1PaymentProvider
    reason: Stage1OrphanPaymentReason
    sla_state: Stage1OrphanPaymentSlaState
    payment_state: Stage1PaymentState
    provisioning_state: Stage1ProvisioningState
    support_state: Stage1SupportState
    access_state: Stage1AccessState
    safe_reference: str
    age_minutes: int
    actions: tuple[Stage1OrphanPaymentAction, ...]
    manual_review_required: bool
    support_escalation: bool
    launch_blocker: bool

    def to_flow_status(self) -> Stage1FlowStatusResponse:
        """Convert the decision into the common S1 flow status response."""

        return Stage1FlowStatusResponse(
            access_state=self.access_state,
            payment_state=self.payment_state,
            provisioning_state=self.provisioning_state,
            support_state=self.support_state,
            user_action=self._user_action(),
            support_escalation=self.support_escalation,
            details={
                "reason": self.reason.value,
                "sla_state": self.sla_state.value,
                "age_minutes": self.age_minutes,
                "safe_reference": self.safe_reference,
            },
        )

    def to_api_dict(self) -> dict[str, Any]:
        """Serialize without raw provider payment ids or personal data."""

        return {
            "provider": self.provider.value,
            "reason": self.reason.value,
            "sla_state": self.sla_state.value,
            "payment_state": self.payment_state.value,
            "provisioning_state": self.provisioning_state.value,
            "support_state": self.support_state.value,
            "access_state": self.access_state.value,
            "safe_reference": self.safe_reference,
            "age_minutes": self.age_minutes,
            "actions": [action.value for action in self.actions],
            "manual_review_required": self.manual_review_required,
            "support_escalation": self.support_escalation,
            "launch_blocker": self.launch_blocker,
            "error_code": self._error_code().value if self.manual_review_required else None,
        }

    def _error_code(self) -> Stage1ErrorCode:
        if self.reason in {
            Stage1OrphanPaymentReason.PAID_BUT_ACCESS_NOT_READY,
            Stage1OrphanPaymentReason.PROVISIONING_FAILED,
            Stage1OrphanPaymentReason.REMNAWAVE_UNAVAILABLE,
        }:
            return Stage1ErrorCode.PROVISIONING_RECONCILIATION_REQUIRED
        return Stage1ErrorCode.PAYMENT_ORPHAN_REVIEW_REQUIRED

    def _user_action(self) -> str | None:
        if not self.manual_review_required:
            return None
        if self.launch_blocker:
            return "Support/ops must resolve this before S1 beta can continue normally."
        return "Support must review payment and access state under the S1 orphan-payment SLA."


@dataclass(frozen=True, slots=True)
class Stage1OrphanPaymentQueueSummary:
    """Dashboard/alert summary for unresolved orphan payment decisions."""

    total_items: int
    manual_review_items: int
    alert_15m_items: int
    p1_escalation_items: int
    p0_blocker_items: int
    max_age_minutes: int
    launch_blocked: bool

    def to_api_dict(self) -> dict[str, int | bool]:
        return {
            "total_items": self.total_items,
            "manual_review_items": self.manual_review_items,
            "alert_15m_items": self.alert_15m_items,
            "p1_escalation_items": self.p1_escalation_items,
            "p0_blocker_items": self.p0_blocker_items,
            "max_age_minutes": self.max_age_minutes,
            "launch_blocked": self.launch_blocked,
        }


def evaluate_stage1_orphan_payment(snapshot: Stage1PaymentAccessSnapshot) -> Stage1OrphanPaymentDecision:
    """Evaluate a payment/access snapshot against the S1 orphan policy."""

    provider = _coerce_provider(snapshot.provider)
    payment_state = _coerce_payment_state(snapshot.payment_state)
    provisioning_state = _coerce_provisioning_state(snapshot.provisioning_state)
    age_minutes = _age_minutes(snapshot.detected_at, snapshot.observed_at)
    safe_reference = _safe_payment_reference(
        provider=provider,
        provider_payment_id=snapshot.provider_payment_id,
        payment_id=snapshot.payment_id,
    )

    reason = _resolve_reason(snapshot, payment_state, provisioning_state)
    if reason in {Stage1OrphanPaymentReason.NONE, Stage1OrphanPaymentReason.RESOLVED}:
        return Stage1OrphanPaymentDecision(
            provider=provider,
            reason=reason,
            sla_state=Stage1OrphanPaymentSlaState.OK,
            payment_state=payment_state,
            provisioning_state=Stage1ProvisioningState.READY if snapshot.access_ready else provisioning_state,
            support_state=Stage1SupportState.RESOLVED
            if reason == Stage1OrphanPaymentReason.RESOLVED
            else Stage1SupportState.NONE,
            access_state=Stage1AccessState.ACTIVE if snapshot.access_ready else Stage1AccessState.PAYMENT_PENDING,
            safe_reference=safe_reference,
            age_minutes=age_minutes,
            actions=(),
            manual_review_required=False,
            support_escalation=False,
            launch_blocker=False,
        )

    sla_state = _resolve_sla_state(age_minutes)
    support_state = (
        Stage1SupportState.OPS_ESCALATION
        if sla_state in {Stage1OrphanPaymentSlaState.P1_ESCALATION, Stage1OrphanPaymentSlaState.P0_BLOCKER}
        else Stage1SupportState.SUPPORT_REVIEW
    )
    actions = _resolve_actions(reason, sla_state)
    resolved_payment_state, resolved_provisioning_state, access_state = _resolve_flow_states(
        reason=reason,
        payment_state=payment_state,
        provisioning_state=provisioning_state,
    )

    return Stage1OrphanPaymentDecision(
        provider=provider,
        reason=reason,
        sla_state=sla_state,
        payment_state=resolved_payment_state,
        provisioning_state=resolved_provisioning_state,
        support_state=support_state,
        access_state=access_state,
        safe_reference=safe_reference,
        age_minutes=age_minutes,
        actions=actions,
        manual_review_required=True,
        support_escalation=True,
        launch_blocker=sla_state == Stage1OrphanPaymentSlaState.P0_BLOCKER,
    )


def summarize_stage1_orphan_payment_queue(
    decisions: Sequence[Stage1OrphanPaymentDecision],
) -> Stage1OrphanPaymentQueueSummary:
    """Summarize unresolved orphan/paid-but-no-access decisions for dashboard/alerts."""

    manual_review_decisions = [decision for decision in decisions if decision.manual_review_required]
    alert_15m_items = sum(
        decision.sla_state
        in {
            Stage1OrphanPaymentSlaState.ALERT_15M,
            Stage1OrphanPaymentSlaState.P1_ESCALATION,
            Stage1OrphanPaymentSlaState.P0_BLOCKER,
        }
        for decision in manual_review_decisions
    )
    p1_items = sum(
        decision.sla_state
        in {
            Stage1OrphanPaymentSlaState.P1_ESCALATION,
            Stage1OrphanPaymentSlaState.P0_BLOCKER,
        }
        for decision in manual_review_decisions
    )
    p0_items = sum(decision.sla_state == Stage1OrphanPaymentSlaState.P0_BLOCKER for decision in manual_review_decisions)

    return Stage1OrphanPaymentQueueSummary(
        total_items=len(decisions),
        manual_review_items=len(manual_review_decisions),
        alert_15m_items=alert_15m_items,
        p1_escalation_items=p1_items,
        p0_blocker_items=p0_items,
        max_age_minutes=max((decision.age_minutes for decision in manual_review_decisions), default=0),
        launch_blocked=p0_items > 0,
    )


def _resolve_reason(
    snapshot: Stage1PaymentAccessSnapshot,
    payment_state: Stage1PaymentState,
    provisioning_state: Stage1ProvisioningState,
) -> Stage1OrphanPaymentReason:
    if snapshot.resolved:
        return Stage1OrphanPaymentReason.RESOLVED
    if snapshot.user_reported_debit_provider_pending:
        return Stage1OrphanPaymentReason.USER_REPORTED_DEBIT_PROVIDER_PENDING
    if payment_state != Stage1PaymentState.PAID:
        if payment_state == Stage1PaymentState.RECONCILIATION_REQUIRED:
            return Stage1OrphanPaymentReason.AMOUNT_CURRENCY_MISMATCH
        return Stage1OrphanPaymentReason.NONE
    if not snapshot.user_found:
        return Stage1OrphanPaymentReason.USER_NOT_FOUND
    if not snapshot.order_found:
        return Stage1OrphanPaymentReason.ORDER_NOT_FOUND
    if not snapshot.amount_currency_match:
        return Stage1OrphanPaymentReason.AMOUNT_CURRENCY_MISMATCH
    if snapshot.provider_final_success_after_timeout:
        return Stage1OrphanPaymentReason.PROVIDER_SUCCESS_AFTER_TIMEOUT
    if snapshot.access_ready:
        return Stage1OrphanPaymentReason.NONE
    if provisioning_state == Stage1ProvisioningState.FAILED:
        return Stage1OrphanPaymentReason.PROVISIONING_FAILED
    if provisioning_state == Stage1ProvisioningState.REMNAWAVE_UNAVAILABLE:
        return Stage1OrphanPaymentReason.REMNAWAVE_UNAVAILABLE
    return Stage1OrphanPaymentReason.PAID_BUT_ACCESS_NOT_READY


def _resolve_sla_state(age_minutes: int) -> Stage1OrphanPaymentSlaState:
    if age_minutes >= STAGE1_ORPHAN_P0_AFTER_MINUTES:
        return Stage1OrphanPaymentSlaState.P0_BLOCKER
    if age_minutes >= STAGE1_ORPHAN_P1_AFTER_MINUTES:
        return Stage1OrphanPaymentSlaState.P1_ESCALATION
    if age_minutes >= STAGE1_ORPHAN_ALERT_AFTER_MINUTES:
        return Stage1OrphanPaymentSlaState.ALERT_15M
    return Stage1OrphanPaymentSlaState.MANUAL_REVIEW


def _resolve_actions(
    reason: Stage1OrphanPaymentReason,
    sla_state: Stage1OrphanPaymentSlaState,
) -> tuple[Stage1OrphanPaymentAction, ...]:
    actions: list[Stage1OrphanPaymentAction] = [Stage1OrphanPaymentAction.CREATE_MANUAL_REVIEW_ITEM]

    if reason in {Stage1OrphanPaymentReason.USER_NOT_FOUND, Stage1OrphanPaymentReason.ORDER_NOT_FOUND}:
        actions.extend(
            [
                Stage1OrphanPaymentAction.ALERT_SUPPORT_FINANCE,
                Stage1OrphanPaymentAction.RECONCILE_PROVIDER_DASHBOARD,
                Stage1OrphanPaymentAction.DO_NOT_CREATE_ACCOUNT_SILENTLY,
            ]
        )
    elif reason in {
        Stage1OrphanPaymentReason.PAID_BUT_ACCESS_NOT_READY,
        Stage1OrphanPaymentReason.PROVISIONING_FAILED,
        Stage1OrphanPaymentReason.REMNAWAVE_UNAVAILABLE,
    }:
        actions.extend(
            [
                Stage1OrphanPaymentAction.PRESERVE_PAID_STATE,
                Stage1OrphanPaymentAction.QUEUE_PROVISIONING_RETRY,
            ]
        )
    elif reason == Stage1OrphanPaymentReason.AMOUNT_CURRENCY_MISMATCH:
        actions.extend(
            [
                Stage1OrphanPaymentAction.BLOCK_AUTOMATIC_ACCESS,
                Stage1OrphanPaymentAction.RECONCILE_PROVIDER_DASHBOARD,
            ]
        )
    elif reason == Stage1OrphanPaymentReason.PROVIDER_SUCCESS_AFTER_TIMEOUT:
        actions.extend(
            [
                Stage1OrphanPaymentAction.PRESERVE_PAID_STATE,
                Stage1OrphanPaymentAction.REOPEN_RECONCILIATION,
                Stage1OrphanPaymentAction.QUEUE_PROVISIONING_RETRY,
            ]
        )
    elif reason == Stage1OrphanPaymentReason.USER_REPORTED_DEBIT_PROVIDER_PENDING:
        actions.extend(
            [
                Stage1OrphanPaymentAction.CREATE_SUPPORT_TICKET,
                Stage1OrphanPaymentAction.RECONCILE_PROVIDER_DASHBOARD,
            ]
        )

    if sla_state in {
        Stage1OrphanPaymentSlaState.ALERT_15M,
        Stage1OrphanPaymentSlaState.P1_ESCALATION,
        Stage1OrphanPaymentSlaState.P0_BLOCKER,
    }:
        actions.append(Stage1OrphanPaymentAction.SEND_PAID_WITHOUT_ACCESS_ALERT)
    if sla_state in {Stage1OrphanPaymentSlaState.P1_ESCALATION, Stage1OrphanPaymentSlaState.P0_BLOCKER}:
        actions.append(Stage1OrphanPaymentAction.P1_SUPPORT_OPS_ESCALATION)
    if sla_state == Stage1OrphanPaymentSlaState.P0_BLOCKER:
        actions.append(Stage1OrphanPaymentAction.P0_LAUNCH_BLOCKER)

    return tuple(dict.fromkeys(actions))


def _resolve_flow_states(
    *,
    reason: Stage1OrphanPaymentReason,
    payment_state: Stage1PaymentState,
    provisioning_state: Stage1ProvisioningState,
) -> tuple[Stage1PaymentState, Stage1ProvisioningState, Stage1AccessState]:
    if reason in {Stage1OrphanPaymentReason.USER_NOT_FOUND, Stage1OrphanPaymentReason.ORDER_NOT_FOUND}:
        return (
            Stage1PaymentState.ORPHAN_REVIEW_REQUIRED,
            Stage1ProvisioningState.NOT_REQUIRED,
            Stage1AccessState.NO_ACCESS,
        )
    if reason == Stage1OrphanPaymentReason.AMOUNT_CURRENCY_MISMATCH:
        return (
            Stage1PaymentState.RECONCILIATION_REQUIRED,
            Stage1ProvisioningState.RECONCILIATION_REQUIRED,
            Stage1AccessState.NO_ACCESS,
        )
    if reason == Stage1OrphanPaymentReason.USER_REPORTED_DEBIT_PROVIDER_PENDING:
        return (
            Stage1PaymentState.PENDING,
            Stage1ProvisioningState.NOT_REQUIRED,
            Stage1AccessState.PAYMENT_PENDING,
        )
    if reason == Stage1OrphanPaymentReason.REMNAWAVE_UNAVAILABLE:
        return (
            Stage1PaymentState.PAID,
            Stage1ProvisioningState.REMNAWAVE_UNAVAILABLE,
            Stage1AccessState.PROVISIONING_PENDING,
        )
    if reason == Stage1OrphanPaymentReason.PROVISIONING_FAILED:
        return (
            Stage1PaymentState.PAID,
            Stage1ProvisioningState.RETRYING,
            Stage1AccessState.PROVISIONING_PENDING,
        )
    if reason == Stage1OrphanPaymentReason.PROVIDER_SUCCESS_AFTER_TIMEOUT:
        return (
            Stage1PaymentState.PAID,
            Stage1ProvisioningState.RECONCILIATION_REQUIRED,
            Stage1AccessState.PROVISIONING_PENDING,
        )
    return (payment_state, provisioning_state, Stage1AccessState.PROVISIONING_PENDING)


def _coerce_provider(provider: Stage1PaymentProvider | str) -> Stage1PaymentProvider:
    if isinstance(provider, Stage1PaymentProvider):
        return provider
    return Stage1PaymentProvider(str(provider))


def _coerce_payment_state(state: Stage1PaymentState | str) -> Stage1PaymentState:
    if isinstance(state, Stage1PaymentState):
        return state
    return Stage1PaymentState(str(state))


def _coerce_provisioning_state(state: Stage1ProvisioningState | str) -> Stage1ProvisioningState:
    if isinstance(state, Stage1ProvisioningState):
        return state
    return Stage1ProvisioningState(str(state))


def _age_minutes(detected_at: datetime, observed_at: datetime) -> int:
    detected = _aware_utc(detected_at)
    observed = _aware_utc(observed_at)
    return max(0, int((observed - detected).total_seconds() // 60))


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _safe_payment_reference(
    *,
    provider: Stage1PaymentProvider,
    provider_payment_id: str,
    payment_id: str | None,
) -> str:
    key_material = json.dumps(
        [provider.value, provider_payment_id, payment_id or ""],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return f"s1:payment-review:{sha256(key_material.encode('utf-8')).hexdigest()}"
