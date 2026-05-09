"""Stage 1 payment-to-provisioning orchestration contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.application.use_cases.subscriptions.stage1_paid_provisioning import (
    Stage1PaidProvisioningGateway,
    Stage1PaidProvisioningRequest,
)
from src.application.use_cases.subscriptions.stage1_provisioning_retry import (
    Stage1ProvisioningRetryDecision,
    Stage1ProvisioningRetryJob,
    Stage1ProvisioningRetryService,
)
from src.presentation.api.shared.stage1_contract import (
    JsonScalar,
    Stage1AccessState,
    Stage1FlowStatusResponse,
    Stage1PaymentState,
    Stage1ProvisioningState,
    Stage1SupportState,
)
from src.presentation.api.shared.stage1_orphan_payment_policy import (
    Stage1OrphanPaymentDecision,
    Stage1PaymentAccessSnapshot,
    evaluate_stage1_orphan_payment,
)
from src.presentation.api.shared.stage1_payment_mapping import Stage1ProviderPaymentStatusDecision
from src.presentation.api.shared.stage1_webhook_idempotency import (
    Stage1WebhookIdempotencyDecision,
    Stage1WebhookSideEffect,
)


class Stage1PaymentProvisioningError(RuntimeError):
    """Raised when an S1 paid webhook cannot be safely mapped to provisioning."""


@dataclass(frozen=True, slots=True)
class Stage1PaymentProvisioningResult:
    """Composite result for paid webhook -> VPN provisioning handling."""

    access_state: Stage1AccessState
    payment_state: Stage1PaymentState
    provisioning_state: Stage1ProvisioningState
    support_state: Stage1SupportState
    webhook_decision: Stage1WebhookIdempotencyDecision
    payment_decision: Stage1ProviderPaymentStatusDecision
    provisioning_attempted: bool
    paid_state_preserved: bool
    retry_queued: bool
    manual_review_required: bool
    support_escalation: bool
    skipped_reason: str | None = None
    retry_job: Stage1ProvisioningRetryJob | None = None
    retry_decision: Stage1ProvisioningRetryDecision | None = None
    orphan_decision: Stage1OrphanPaymentDecision | None = None

    @property
    def webhook_duplicate(self) -> bool:
        """Return whether the provider webhook event was a duplicate."""

        return self.webhook_decision.duplicate

    def to_flow_status(self) -> Stage1FlowStatusResponse:
        """Build the common S1 flow status response without raw provider ids."""

        return Stage1FlowStatusResponse(
            access_state=self.access_state,
            payment_state=self.payment_state,
            provisioning_state=self.provisioning_state,
            support_state=self.support_state,
            user_action=_user_action(self),
            support_escalation=self.support_escalation,
            details=self._flow_details(),
        )

    def to_safe_dict(self) -> dict[str, JsonScalar | dict[str, JsonScalar]]:
        """Serialize orchestration evidence without raw payment ids, PII or config links."""

        payload: dict[str, JsonScalar | dict[str, JsonScalar]] = {
            "access_state": self.access_state.value,
            "payment_state": self.payment_state.value,
            "provisioning_state": self.provisioning_state.value,
            "support_state": self.support_state.value,
            "provider": self.payment_decision.provider.value,
            "provider_status": self.payment_decision.provider_status,
            "normalized_status": self.payment_decision.normalized_status,
            "webhook_duplicate": self.webhook_duplicate,
            "provisioning_attempted": self.provisioning_attempted,
            "paid_state_preserved": self.paid_state_preserved,
            "retry_queued": self.retry_queued,
            "manual_review_required": self.manual_review_required,
            "support_escalation": self.support_escalation,
            "skipped_reason": self.skipped_reason,
            "idempotency_key": self.webhook_decision.identity.idempotency_key,
            "operation_key": self.webhook_decision.identity.operation_key,
        }
        if self.retry_job is not None:
            payload["retry_job"] = self._safe_retry_job_payload()
        if self.orphan_decision is not None:
            payload["orphan"] = {
                "safe_reference": self.orphan_decision.safe_reference,
                "reason": self.orphan_decision.reason.value,
                "sla_state": self.orphan_decision.sla_state.value,
                "age_minutes": self.orphan_decision.age_minutes,
                "launch_blocker": self.orphan_decision.launch_blocker,
            }
        return payload

    def _flow_details(self) -> dict[str, JsonScalar]:
        details: dict[str, JsonScalar] = {
            "provider": self.payment_decision.provider.value,
            "normalized_status": self.payment_decision.normalized_status,
            "webhook_duplicate": self.webhook_duplicate,
            "provisioning_attempted": self.provisioning_attempted,
            "paid_state_preserved": self.paid_state_preserved,
            "retry_queued": self.retry_queued,
        }
        if self.skipped_reason:
            details["skipped_reason"] = self.skipped_reason
        if self.retry_job:
            details.update(
                {
                    "retry_job_id": str(self.retry_job.job_id),
                    "queue_name": self.retry_job.queue_name,
                    "next_attempt_at": self.retry_job.next_attempt_at.isoformat(),
                    "retry_attempt_count": self.retry_job.attempt_count,
                }
            )
        if self.orphan_decision:
            details.update(
                {
                    "safe_reference": self.orphan_decision.safe_reference,
                    "sla_state": self.orphan_decision.sla_state.value,
                    "orphan_reason": self.orphan_decision.reason.value,
                }
            )
        return details

    def _safe_retry_job_payload(self) -> dict[str, JsonScalar]:
        safe = self.retry_job.to_safe_dict() if self.retry_job else {}
        return {
            "job_id": safe.get("job_id"),
            "queue_name": safe.get("queue_name"),
            "operation": safe.get("operation"),
            "state": safe.get("state"),
            "attempt_count": safe.get("attempt_count"),
            "max_attempts": safe.get("max_attempts"),
            "next_attempt_at": safe.get("next_attempt_at"),
            "reason": safe.get("reason"),
            "payment_state": safe.get("payment_state"),
            "provisioning_state": safe.get("provisioning_state"),
        }


async def handle_stage1_paid_webhook_provisioning(
    *,
    payment_decision: Stage1ProviderPaymentStatusDecision,
    webhook_decision: Stage1WebhookIdempotencyDecision,
    paid_request: Stage1PaidProvisioningRequest | None,
    gateway: Stage1PaidProvisioningGateway,
    retry_service: Stage1ProvisioningRetryService,
    provider_payment_id: str,
    payment_id: str | None,
    detected_at: datetime,
    observed_at: datetime,
    user_found: bool = True,
    order_found: bool = True,
    amount_currency_match: bool = True,
) -> Stage1PaymentProvisioningResult:
    """Handle a verified paid webhook and queue provisioning retry on failure.

    This function is a local S1 orchestration contract. Production code still
    needs durable webhook idempotency, durable retry storage and live provider
    signature evidence before enabling paid beta.
    """

    if payment_decision.payment_state != Stage1PaymentState.PAID or not payment_decision.automatic_paid_access_allowed:
        return _skipped_result(
            payment_decision=payment_decision,
            webhook_decision=webhook_decision,
            reason="payment_not_eligible_for_automatic_paid_access",
        )

    if Stage1WebhookSideEffect.PROVISIONING_JOB not in webhook_decision.side_effects_allowed:
        return _skipped_result(
            payment_decision=payment_decision,
            webhook_decision=webhook_decision,
            reason="webhook_provisioning_side_effect_already_applied",
        )

    if paid_request is None:
        raise Stage1PaymentProvisioningError("Paid provisioning requires a paid request")

    retry_decision = await retry_service.provision_paid_or_queue(
        request=paid_request,
        gateway=gateway,
    )
    snapshot_state = _snapshot_provisioning_state(retry_decision)
    orphan_decision = evaluate_stage1_orphan_payment(
        Stage1PaymentAccessSnapshot(
            provider=payment_decision.provider,
            provider_payment_id=provider_payment_id,
            payment_id=payment_id,
            detected_at=_ensure_aware_utc(detected_at),
            observed_at=_ensure_aware_utc(observed_at),
            payment_state=Stage1PaymentState.PAID,
            provisioning_state=snapshot_state,
            user_found=user_found,
            order_found=order_found,
            amount_currency_match=amount_currency_match,
            access_ready=retry_decision.completed,
        )
    )
    payment_state = Stage1PaymentState.PAID
    provisioning_state = retry_decision.provisioning_state
    access_state = Stage1AccessState.ACTIVE if retry_decision.completed else Stage1AccessState.PROVISIONING_PENDING
    support_state = _support_state_for_retry(
        retry_decision=retry_decision,
        orphan_decision=orphan_decision,
        payment_decision=payment_decision,
    )
    manual_review_required = orphan_decision.manual_review_required or payment_decision.manual_review_required

    return Stage1PaymentProvisioningResult(
        access_state=access_state,
        payment_state=payment_state,
        provisioning_state=provisioning_state,
        support_state=support_state,
        webhook_decision=webhook_decision,
        payment_decision=payment_decision,
        provisioning_attempted=True,
        paid_state_preserved=True,
        retry_queued=retry_decision.queued_for_retry,
        manual_review_required=manual_review_required,
        support_escalation=(
            retry_decision.support_state != Stage1SupportState.NONE
            or orphan_decision.support_escalation
            or payment_decision.support_state != Stage1SupportState.NONE
        ),
        retry_job=retry_decision.retry_job,
        retry_decision=retry_decision,
        orphan_decision=orphan_decision,
    )


def _skipped_result(
    *,
    payment_decision: Stage1ProviderPaymentStatusDecision,
    webhook_decision: Stage1WebhookIdempotencyDecision,
    reason: str,
) -> Stage1PaymentProvisioningResult:
    payment_state = payment_decision.payment_state
    return Stage1PaymentProvisioningResult(
        access_state=_access_state_for_skipped_payment(payment_state),
        payment_state=payment_state,
        provisioning_state=Stage1ProvisioningState.NOT_REQUIRED,
        support_state=payment_decision.support_state,
        webhook_decision=webhook_decision,
        payment_decision=payment_decision,
        provisioning_attempted=False,
        paid_state_preserved=payment_state == Stage1PaymentState.PAID,
        retry_queued=False,
        manual_review_required=payment_decision.manual_review_required,
        support_escalation=payment_decision.support_state != Stage1SupportState.NONE,
        skipped_reason=reason,
    )


def _snapshot_provisioning_state(
    retry_decision: Stage1ProvisioningRetryDecision,
) -> Stage1ProvisioningState:
    if retry_decision.completed:
        return Stage1ProvisioningState.READY
    if retry_decision.retry_job is not None:
        return Stage1ProvisioningState.REMNAWAVE_UNAVAILABLE
    return retry_decision.provisioning_state


def _support_state_for_retry(
    *,
    retry_decision: Stage1ProvisioningRetryDecision,
    orphan_decision: Stage1OrphanPaymentDecision,
    payment_decision: Stage1ProviderPaymentStatusDecision,
) -> Stage1SupportState:
    if retry_decision.support_state != Stage1SupportState.NONE:
        return retry_decision.support_state
    if orphan_decision.support_state != Stage1SupportState.NONE:
        return orphan_decision.support_state
    if payment_decision.support_state != Stage1SupportState.NONE:
        return payment_decision.support_state
    return orphan_decision.support_state


def _access_state_for_skipped_payment(payment_state: Stage1PaymentState) -> Stage1AccessState:
    if payment_state == Stage1PaymentState.PAID:
        return Stage1AccessState.PROVISIONING_PENDING
    if payment_state in {Stage1PaymentState.PENDING, Stage1PaymentState.PROCESSING}:
        return Stage1AccessState.PAYMENT_PENDING
    return Stage1AccessState.NO_ACCESS


def _user_action(result: Stage1PaymentProvisioningResult) -> str | None:
    if result.retry_queued:
        return "Payment is confirmed; wait for automatic VPN provisioning retry or contact support."
    if result.webhook_duplicate:
        return None
    if result.manual_review_required:
        return "Support must review payment and VPN access state."
    return None


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
