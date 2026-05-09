"""Stage 1 payment reconciliation job helpers."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import PaymentAttemptStatus, PaymentStatus
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.presentation.api.shared.stage1_contract import (
    PAYMENT_ATTEMPT_STATUS_TO_STAGE1_STATE,
    PAYMENT_STATUS_TO_STAGE1_STATE,
    Stage1PaymentState,
)
from src.presentation.api.shared.stage1_orphan_payment_policy import (
    STAGE1_ORPHAN_ALERT_AFTER_MINUTES,
    STAGE1_ORPHAN_P0_AFTER_MINUTES,
    STAGE1_ORPHAN_P1_AFTER_MINUTES,
    Stage1OrphanPaymentAction,
    Stage1PaymentAccessSnapshot,
    evaluate_stage1_orphan_payment,
)
from src.presentation.api.shared.stage1_payment_mapping import Stage1PaymentProvider

REPORT_VERSION = "stage1-payment-reconciliation-v1"
DEFAULT_RECONCILIATION_LIMIT = 250
MAX_RECONCILIATION_LIMIT = 1000

ACTIVE_ATTEMPT_STATUSES = {
    PaymentAttemptStatus.PENDING.value,
    PaymentAttemptStatus.PROCESSING.value,
}
PAID_SETTLEMENT_STATUS = "paid"
REFUNDED_SETTLEMENT_STATUSES = {"refunded", "partially_refunded"}
KNOWN_PAYMENT_STATUSES = {status.value for status in PaymentStatus}
KNOWN_ATTEMPT_STATUSES = {status.value for status in PaymentAttemptStatus}

FORBIDDEN_RECONCILIATION_OUTPUT_FIELDS = (
    "payment_id",
    "order_id",
    "user_id",
    "provider_payment_id",
    "external_id",
    "external_reference",
    "idempotency_key",
    "provider_snapshot",
    "request_snapshot",
    "invoice.payment_url",
)


class Stage1PaymentReconciliationSeverity(StrEnum):
    """Action level for a reconciliation finding."""

    MANUAL_REVIEW = "manual_review"
    ALERT_15M = "alert_15m"
    P1_ESCALATION = "p1_escalation"
    P0_BLOCKER = "p0_blocker"


class Stage1PaymentReconciliationCode(StrEnum):
    """Stable S1 reconciliation mismatch codes."""

    STALE_ACTIVE_ATTEMPT = "stale_active_attempt"
    SUCCEEDED_ATTEMPT_WITHOUT_PAYMENT = "succeeded_attempt_without_payment"
    ATTEMPT_PAYMENT_STATUS_MISMATCH = "attempt_payment_status_mismatch"
    ORDER_SETTLEMENT_MISMATCH = "order_settlement_mismatch"
    CANONICAL_PAYMENT_WITHOUT_ATTEMPT = "canonical_payment_without_attempt"
    UNKNOWN_PAYMENT_ATTEMPT_STATUS = "unknown_payment_attempt_status"
    UNKNOWN_PAYMENT_STATUS = "unknown_payment_status"
    USER_MISMATCH = "user_mismatch"


@dataclass(frozen=True, slots=True)
class Stage1PaymentReconciliationItem:
    """Redacted, actionable payment reconciliation finding."""

    code: Stage1PaymentReconciliationCode
    severity: Stage1PaymentReconciliationSeverity
    provider: str
    safe_reference: str
    age_minutes: int
    payment_state: Stage1PaymentState
    actions: tuple[str, ...]
    payment_status: str | None = None
    attempt_status: str | None = None
    order_status: str | None = None
    settlement_status: str | None = None
    message: str = ""
    details: dict[str, str | int | bool | None] | None = None

    @property
    def manual_review_required(self) -> bool:
        return True

    @property
    def support_escalation(self) -> bool:
        return self.severity in {
            Stage1PaymentReconciliationSeverity.ALERT_15M,
            Stage1PaymentReconciliationSeverity.P1_ESCALATION,
            Stage1PaymentReconciliationSeverity.P0_BLOCKER,
        }

    @property
    def launch_blocker(self) -> bool:
        return self.severity == Stage1PaymentReconciliationSeverity.P0_BLOCKER

    def to_api_dict(self) -> dict[str, Any]:
        """Serialize without raw provider/customer/payment identifiers."""

        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "provider": self.provider,
            "safe_reference": self.safe_reference,
            "age_minutes": self.age_minutes,
            "payment_state": self.payment_state.value,
            "payment_status": self.payment_status,
            "attempt_status": self.attempt_status,
            "order_status": self.order_status,
            "settlement_status": self.settlement_status,
            "message": self.message,
            "details": dict(self.details or {}),
            "actions": list(self.actions),
            "manual_review_required": self.manual_review_required,
            "support_escalation": self.support_escalation,
            "launch_blocker": self.launch_blocker,
            "redacted_fields": list(FORBIDDEN_RECONCILIATION_OUTPUT_FIELDS),
        }


@dataclass(frozen=True, slots=True)
class Stage1PaymentReconciliationSummary:
    """Aggregate job result for alerts/evidence."""

    total_items: int
    manual_review_items: int
    alert_15m_items: int
    p1_escalation_items: int
    p0_blocker_items: int
    max_age_minutes: int
    launch_blocked: bool
    mismatch_counts: dict[str, int]

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "total_items": self.total_items,
            "manual_review_items": self.manual_review_items,
            "alert_15m_items": self.alert_15m_items,
            "p1_escalation_items": self.p1_escalation_items,
            "p0_blocker_items": self.p0_blocker_items,
            "max_age_minutes": self.max_age_minutes,
            "launch_blocked": self.launch_blocked,
            "mismatch_counts": dict(self.mismatch_counts),
        }


@dataclass(frozen=True, slots=True)
class Stage1PaymentReconciliationReport:
    """Complete safe reconciliation job report."""

    report_version: str
    generated_at: datetime
    inspected_attempts: int
    inspected_payments_without_attempt: int
    summary: Stage1PaymentReconciliationSummary
    items: tuple[Stage1PaymentReconciliationItem, ...]

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "generated_at": self.generated_at.isoformat(),
            "inspected_attempts": self.inspected_attempts,
            "inspected_payments_without_attempt": self.inspected_payments_without_attempt,
            "summary": self.summary.to_api_dict(),
            "items": [item.to_api_dict() for item in self.items],
        }


class Stage1PaymentReconciliationUseCase:
    """Run the S1 payment reconciliation scan against canonical backend tables."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self,
        *,
        limit: int = DEFAULT_RECONCILIATION_LIMIT,
        observed_at: datetime | None = None,
    ) -> Stage1PaymentReconciliationReport:
        observed = _aware_utc(observed_at or datetime.now(UTC))
        safe_limit = min(max(int(limit), 1), MAX_RECONCILIATION_LIMIT)

        attempt_rows = await self._list_attempt_rows(limit=safe_limit)
        payment_rows = await self._list_payments_without_attempt(limit=safe_limit)

        items: list[Stage1PaymentReconciliationItem] = []
        for attempt, order, payment in attempt_rows:
            items.extend(
                reconcile_stage1_payment_attempt_snapshot(
                    attempt=attempt,
                    order=order,
                    payment=payment,
                    observed_at=observed,
                )
            )
        for payment in payment_rows:
            items.extend(
                reconcile_stage1_payment_without_attempt(
                    payment=payment,
                    observed_at=observed,
                )
            )

        return build_stage1_payment_reconciliation_report(
            items=items,
            inspected_attempts=len(attempt_rows),
            inspected_payments_without_attempt=len(payment_rows),
            generated_at=observed,
        )

    async def _list_attempt_rows(
        self,
        *,
        limit: int,
    ) -> list[tuple[PaymentAttemptModel, OrderModel, PaymentModel | None]]:
        result = await self._session.execute(
            select(PaymentAttemptModel, OrderModel, PaymentModel)
            .join(OrderModel, PaymentAttemptModel.order_id == OrderModel.id)
            .outerjoin(PaymentModel, PaymentAttemptModel.payment_id == PaymentModel.id)
            .order_by(PaymentAttemptModel.updated_at.desc())
            .limit(limit)
        )
        return [(attempt, order, payment) for attempt, order, payment in result.all()]

    async def _list_payments_without_attempt(self, *, limit: int) -> list[PaymentModel]:
        result = await self._session.execute(
            select(PaymentModel)
            .outerjoin(PaymentAttemptModel, PaymentAttemptModel.payment_id == PaymentModel.id)
            .where(
                PaymentAttemptModel.id.is_(None),
                PaymentModel.status.in_(
                    [
                        PaymentStatus.COMPLETED.value,
                        PaymentStatus.REFUNDED.value,
                    ]
                ),
            )
            .order_by(PaymentModel.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


def reconcile_stage1_payment_attempt_snapshot(
    *,
    attempt: Any,
    order: Any,
    payment: Any | None,
    observed_at: datetime,
) -> tuple[Stage1PaymentReconciliationItem, ...]:
    """Reconcile one attempt/order/payment row without exposing raw identifiers."""

    observed = _aware_utc(observed_at)
    items: list[Stage1PaymentReconciliationItem] = []
    provider = _string(getattr(attempt, "provider", None), fallback="unknown")
    attempt_status = _string(getattr(attempt, "status", None), fallback="unknown")
    payment_status = _string(getattr(payment, "status", None), fallback=None) if payment is not None else None
    order_status = _string(getattr(order, "order_status", None), fallback=None)
    settlement_status = _string(getattr(order, "settlement_status", None), fallback=None)
    age_minutes = _age_minutes(_detected_at(attempt), observed)
    safe_reference = _safe_reference(
        "attempt",
        provider,
        getattr(attempt, "id", None),
        getattr(attempt, "external_reference", None),
        getattr(attempt, "payment_id", None),
        getattr(order, "id", None),
    )

    if attempt_status not in KNOWN_ATTEMPT_STATUSES:
        items.append(
            _item(
                code=Stage1PaymentReconciliationCode.UNKNOWN_PAYMENT_ATTEMPT_STATUS,
                provider=provider,
                safe_reference=safe_reference,
                age_minutes=age_minutes,
                payment_state=Stage1PaymentState.RECONCILIATION_REQUIRED,
                attempt_status=attempt_status,
                payment_status=payment_status,
                order_status=order_status,
                settlement_status=settlement_status,
                message="Payment attempt has an unknown status and must be reconciled before side effects.",
                actions=(
                    "freeze_payment_side_effects",
                    "reconcile_provider_dashboard",
                    "create_manual_review_item",
                ),
            )
        )

    if attempt_status in ACTIVE_ATTEMPT_STATUSES and age_minutes >= STAGE1_ORPHAN_ALERT_AFTER_MINUTES:
        items.append(
            _item(
                code=Stage1PaymentReconciliationCode.STALE_ACTIVE_ATTEMPT,
                provider=provider,
                safe_reference=safe_reference,
                age_minutes=age_minutes,
                payment_state=_stage1_payment_state_for_attempt(attempt_status),
                attempt_status=attempt_status,
                payment_status=payment_status,
                order_status=order_status,
                settlement_status=settlement_status,
                message="Active payment attempt is stale and needs provider/status reconciliation.",
                actions=(
                    "reconcile_provider_dashboard",
                    "notify_support_finance",
                    "do_not_provision_until_final_success",
                ),
            )
        )

    if attempt_status == PaymentAttemptStatus.SUCCEEDED.value and payment is None:
        orphan_decision = _orphan_decision_for_attempt(
            attempt=attempt,
            order_found=order is not None,
            observed_at=observed,
        )
        decision_safe_reference = (
            orphan_decision.safe_reference
            if orphan_decision is not None
            else _safe_reference("attempt-orphan", provider, getattr(attempt, "id", None))
        )
        decision_age_minutes = orphan_decision.age_minutes if orphan_decision is not None else age_minutes
        decision_payment_state = (
            orphan_decision.payment_state
            if orphan_decision is not None
            else Stage1PaymentState.ORPHAN_REVIEW_REQUIRED
        )
        decision_actions = (
            tuple(action.value for action in orphan_decision.actions)
            if orphan_decision is not None
            else (
                Stage1OrphanPaymentAction.CREATE_MANUAL_REVIEW_ITEM.value,
                Stage1OrphanPaymentAction.RECONCILE_PROVIDER_DASHBOARD.value,
                Stage1OrphanPaymentAction.DO_NOT_CREATE_ACCOUNT_SILENTLY.value,
            )
        )
        items.append(
            _item(
                code=Stage1PaymentReconciliationCode.SUCCEEDED_ATTEMPT_WITHOUT_PAYMENT,
                provider=provider,
                safe_reference=decision_safe_reference,
                age_minutes=decision_age_minutes,
                payment_state=decision_payment_state,
                attempt_status=attempt_status,
                payment_status=None,
                order_status=order_status,
                settlement_status=settlement_status,
                message="Provider attempt succeeded but no canonical payment row is linked.",
                actions=decision_actions,
            )
        )

    if payment is not None:
        items.extend(
            _reconcile_linked_payment(
                attempt=attempt,
                order=order,
                payment=payment,
                provider=provider,
                safe_reference=safe_reference,
                age_minutes=max(age_minutes, _age_minutes(_detected_at(payment), observed)),
                attempt_status=attempt_status,
                payment_status=payment_status,
                order_status=order_status,
                settlement_status=settlement_status,
            )
        )

    return tuple(items)


def reconcile_stage1_payment_without_attempt(
    *,
    payment: Any,
    observed_at: datetime,
) -> tuple[Stage1PaymentReconciliationItem, ...]:
    """Detect completed/refunded canonical payments not linked to payment attempts."""

    observed = _aware_utc(observed_at)
    provider = _string(getattr(payment, "provider", None), fallback="unknown")
    payment_status = _string(getattr(payment, "status", None), fallback="unknown")
    age_minutes = _age_minutes(_detected_at(payment), observed)
    if payment_status not in {
        PaymentStatus.COMPLETED.value,
        PaymentStatus.REFUNDED.value,
    }:
        return ()

    if payment_status == PaymentStatus.REFUNDED.value:
        payment_state = Stage1PaymentState.REFUNDED
        actions = (
            "verify_refund_record_exists",
            "reconcile_provider_dashboard",
            "create_manual_review_item",
        )
    elif (provider_for_policy := _stage1_provider_or_none(provider)) is not None:
        orphan_decision = evaluate_stage1_orphan_payment(
            Stage1PaymentAccessSnapshot(
                provider=provider_for_policy,
                provider_payment_id=_string(
                    getattr(payment, "external_id", None),
                    fallback=str(getattr(payment, "id", "")),
                ),
                payment_id=str(getattr(payment, "id", "")),
                detected_at=_detected_at(payment),
                observed_at=observed,
                payment_state=Stage1PaymentState.PAID,
                order_found=False,
                access_ready=False,
            )
        )
        payment_state = orphan_decision.payment_state
        actions = tuple(action.value for action in orphan_decision.actions)
    else:
        payment_state = Stage1PaymentState.ORPHAN_REVIEW_REQUIRED
        actions = (
            Stage1OrphanPaymentAction.CREATE_MANUAL_REVIEW_ITEM.value,
            Stage1OrphanPaymentAction.RECONCILE_PROVIDER_DASHBOARD.value,
            Stage1OrphanPaymentAction.DO_NOT_CREATE_ACCOUNT_SILENTLY.value,
        )

    return (
        _item(
            code=Stage1PaymentReconciliationCode.CANONICAL_PAYMENT_WITHOUT_ATTEMPT,
            provider=provider,
            safe_reference=_safe_reference(
                "payment",
                provider,
                getattr(payment, "id", None),
                getattr(payment, "external_id", None),
            ),
            age_minutes=age_minutes,
            payment_state=payment_state,
            payment_status=payment_status,
            message="Canonical payment is final but is not linked to an order payment attempt.",
            actions=actions,
        ),
    )


def build_stage1_payment_reconciliation_report(
    *,
    items: Iterable[Stage1PaymentReconciliationItem],
    inspected_attempts: int,
    inspected_payments_without_attempt: int,
    generated_at: datetime | None = None,
) -> Stage1PaymentReconciliationReport:
    """Build a deterministic report from reconciliation findings."""

    item_tuple = tuple(items)
    counts = Counter(item.code.value for item in item_tuple)
    summary = Stage1PaymentReconciliationSummary(
        total_items=len(item_tuple),
        manual_review_items=len(item_tuple),
        alert_15m_items=sum(
            item.severity
            in {
                Stage1PaymentReconciliationSeverity.ALERT_15M,
                Stage1PaymentReconciliationSeverity.P1_ESCALATION,
                Stage1PaymentReconciliationSeverity.P0_BLOCKER,
            }
            for item in item_tuple
        ),
        p1_escalation_items=sum(
            item.severity
            in {
                Stage1PaymentReconciliationSeverity.P1_ESCALATION,
                Stage1PaymentReconciliationSeverity.P0_BLOCKER,
            }
            for item in item_tuple
        ),
        p0_blocker_items=sum(
            item.severity == Stage1PaymentReconciliationSeverity.P0_BLOCKER for item in item_tuple
        ),
        max_age_minutes=max((item.age_minutes for item in item_tuple), default=0),
        launch_blocked=any(item.launch_blocker for item in item_tuple),
        mismatch_counts=dict(sorted(counts.items())),
    )
    return Stage1PaymentReconciliationReport(
        report_version=REPORT_VERSION,
        generated_at=_aware_utc(generated_at or datetime.now(UTC)),
        inspected_attempts=inspected_attempts,
        inspected_payments_without_attempt=inspected_payments_without_attempt,
        summary=summary,
        items=item_tuple,
    )


def assert_stage1_payment_reconciliation_output_is_redacted(payload: dict[str, Any] | Sequence[Any]) -> None:
    """Guard evidence payloads from accidental raw field exposure."""

    forbidden_keys = {field.replace(".", "_") for field in FORBIDDEN_RECONCILIATION_OUTPUT_FIELDS}

    def visit(value: Any, *, parent_key: str | None = None) -> None:
        if parent_key == "redacted_fields":
            return
        if isinstance(value, dict):
            for key, nested in value.items():
                normalized = str(key).replace(".", "_")
                if normalized in forbidden_keys:
                    msg = f"Reconciliation output leaked forbidden raw field: {key}"
                    raise AssertionError(msg)
                visit(nested, parent_key=str(key))
            return
        if isinstance(value, (list, tuple)):
            for nested in value:
                visit(nested, parent_key=parent_key)

    visit(payload)


def _reconcile_linked_payment(
    *,
    attempt: Any,
    order: Any,
    payment: Any,
    provider: str,
    safe_reference: str,
    age_minutes: int,
    attempt_status: str,
    payment_status: str | None,
    order_status: str | None,
    settlement_status: str | None,
) -> tuple[Stage1PaymentReconciliationItem, ...]:
    items: list[Stage1PaymentReconciliationItem] = []
    payment_state = _stage1_payment_state_for_payment(payment_status)

    if payment_status not in KNOWN_PAYMENT_STATUSES:
        items.append(
            _item(
                code=Stage1PaymentReconciliationCode.UNKNOWN_PAYMENT_STATUS,
                provider=provider,
                safe_reference=safe_reference,
                age_minutes=age_minutes,
                payment_state=Stage1PaymentState.RECONCILIATION_REQUIRED,
                attempt_status=attempt_status,
                payment_status=payment_status,
                order_status=order_status,
                settlement_status=settlement_status,
                message="Canonical payment has an unknown status and must not drive access changes.",
                actions=(
                    "freeze_payment_side_effects",
                    "reconcile_provider_dashboard",
                    "create_manual_review_item",
                ),
            )
        )

    if attempt_status == PaymentAttemptStatus.SUCCEEDED.value and payment_status != PaymentStatus.COMPLETED.value:
        valid_refund_transition = (
            payment_status == PaymentStatus.REFUNDED.value and settlement_status in REFUNDED_SETTLEMENT_STATUSES
        )
        if not valid_refund_transition:
            items.append(
                _item(
                    code=Stage1PaymentReconciliationCode.ATTEMPT_PAYMENT_STATUS_MISMATCH,
                    provider=provider,
                    safe_reference=safe_reference,
                    age_minutes=age_minutes,
                    payment_state=Stage1PaymentState.RECONCILIATION_REQUIRED,
                    attempt_status=attempt_status,
                    payment_status=payment_status,
                    order_status=order_status,
                    settlement_status=settlement_status,
                    message="Succeeded payment attempt does not match canonical payment final state.",
                    actions=(
                        "reconcile_provider_dashboard",
                        "preserve_existing_access_state",
                        "create_manual_review_item",
                    ),
                )
            )

    if payment_status == PaymentStatus.COMPLETED.value and attempt_status != PaymentAttemptStatus.SUCCEEDED.value:
        items.append(
            _item(
                code=Stage1PaymentReconciliationCode.ATTEMPT_PAYMENT_STATUS_MISMATCH,
                provider=provider,
                safe_reference=safe_reference,
                age_minutes=age_minutes,
                payment_state=Stage1PaymentState.RECONCILIATION_REQUIRED,
                attempt_status=attempt_status,
                payment_status=payment_status,
                order_status=order_status,
                settlement_status=settlement_status,
                message="Canonical payment is completed but linked attempt is not succeeded.",
                actions=(
                    "reconcile_provider_dashboard",
                    "block_duplicate_provisioning",
                    "create_manual_review_item",
                ),
            )
        )

    if (
        attempt_status == PaymentAttemptStatus.SUCCEEDED.value
        and payment_status == PaymentStatus.COMPLETED.value
        and settlement_status != PAID_SETTLEMENT_STATUS
    ):
        items.append(
            _item(
                code=Stage1PaymentReconciliationCode.ORDER_SETTLEMENT_MISMATCH,
                provider=provider,
                safe_reference=safe_reference,
                age_minutes=age_minutes,
                payment_state=payment_state,
                attempt_status=attempt_status,
                payment_status=payment_status,
                order_status=order_status,
                settlement_status=settlement_status,
                message="Payment is completed but canonical order settlement is not paid.",
                actions=(
                    "run_post_payment_processing_or_repair",
                    "reconcile_order_settlement",
                    "create_manual_review_item",
                ),
            )
        )

    payment_user = _string(getattr(payment, "user_uuid", None), fallback=None)
    order_user = _string(getattr(order, "user_id", None), fallback=None)
    if payment_user != order_user:
        items.append(
            _item(
                code=Stage1PaymentReconciliationCode.USER_MISMATCH,
                provider=provider,
                safe_reference=safe_reference,
                age_minutes=age_minutes,
                payment_state=Stage1PaymentState.RECONCILIATION_REQUIRED,
                attempt_status=attempt_status,
                payment_status=payment_status,
                order_status=order_status,
                settlement_status=settlement_status,
                message="Payment user does not match order user; block automatic access changes.",
                actions=(
                    "block_automatic_access",
                    "reconcile_identity_linkage",
                    "create_manual_review_item",
                ),
            )
        )

    return tuple(items)


def _orphan_decision_for_attempt(
    *,
    attempt: Any,
    order_found: bool,
    observed_at: datetime,
):
    provider = _stage1_provider_or_none(_string(getattr(attempt, "provider", None), fallback="unknown") or "unknown")
    if provider is None:
        return None
    return evaluate_stage1_orphan_payment(
        Stage1PaymentAccessSnapshot(
            provider=provider,
            provider_payment_id=_string(
                getattr(attempt, "external_reference", None),
                fallback=str(getattr(attempt, "id", "")),
            ),
            detected_at=_detected_at(attempt),
            observed_at=observed_at,
            payment_state=Stage1PaymentState.PAID,
            order_found=order_found,
            access_ready=False,
        )
    )


def _item(
    *,
    code: Stage1PaymentReconciliationCode,
    provider: str,
    safe_reference: str,
    age_minutes: int,
    payment_state: Stage1PaymentState,
    actions: Sequence[str | Stage1OrphanPaymentAction],
    payment_status: str | None = None,
    attempt_status: str | None = None,
    order_status: str | None = None,
    settlement_status: str | None = None,
    message: str = "",
    details: dict[str, str | int | bool | None] | None = None,
) -> Stage1PaymentReconciliationItem:
    return Stage1PaymentReconciliationItem(
        code=code,
        severity=_severity_for_age(age_minutes),
        provider=provider,
        safe_reference=safe_reference,
        age_minutes=age_minutes,
        payment_state=payment_state,
        payment_status=payment_status,
        attempt_status=attempt_status,
        order_status=order_status,
        settlement_status=settlement_status,
        message=message,
        details=details,
        actions=tuple(
            dict.fromkeys(
                str(action.value if isinstance(action, StrEnum) else action)
                for action in actions
            )
        ),
    )


def _severity_for_age(age_minutes: int) -> Stage1PaymentReconciliationSeverity:
    if age_minutes >= STAGE1_ORPHAN_P0_AFTER_MINUTES:
        return Stage1PaymentReconciliationSeverity.P0_BLOCKER
    if age_minutes >= STAGE1_ORPHAN_P1_AFTER_MINUTES:
        return Stage1PaymentReconciliationSeverity.P1_ESCALATION
    if age_minutes >= STAGE1_ORPHAN_ALERT_AFTER_MINUTES:
        return Stage1PaymentReconciliationSeverity.ALERT_15M
    return Stage1PaymentReconciliationSeverity.MANUAL_REVIEW


def _stage1_payment_state_for_attempt(status_value: str) -> Stage1PaymentState:
    try:
        return PAYMENT_ATTEMPT_STATUS_TO_STAGE1_STATE[PaymentAttemptStatus(status_value)]
    except ValueError:
        return Stage1PaymentState.RECONCILIATION_REQUIRED


def _stage1_payment_state_for_payment(status_value: str | None) -> Stage1PaymentState:
    try:
        return PAYMENT_STATUS_TO_STAGE1_STATE[PaymentStatus(str(status_value))]
    except ValueError:
        return Stage1PaymentState.RECONCILIATION_REQUIRED


def _detected_at(record: Any) -> datetime:
    for attr_name in ("terminal_at", "updated_at", "created_at"):
        value = getattr(record, attr_name, None)
        if isinstance(value, datetime):
            return _aware_utc(value)
    return datetime.now(UTC)


def _age_minutes(detected_at: datetime, observed_at: datetime) -> int:
    return max(0, int((_aware_utc(observed_at) - _aware_utc(detected_at)).total_seconds() // 60))


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _safe_reference(scope: str, *values: Any) -> str:
    key_material = json.dumps(
        [scope, *[str(value or "") for value in values]],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    digest = sha256(key_material.encode("utf-8")).hexdigest()
    return f"s1:payment-reconciliation:{digest}"


def _stage1_provider_or_none(provider: str) -> Stage1PaymentProvider | None:
    try:
        return Stage1PaymentProvider(provider)
    except ValueError:
        return None


def _string(value: Any, *, fallback: str | None) -> str | None:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback
