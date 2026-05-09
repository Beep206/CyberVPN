"""S1-PAY-008 payment webhook -> provisioning failure checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.application.use_cases.subscriptions.stage1_paid_provisioning import (
    STAGE1_PAID_ORDER_STATUS,
    STAGE1_PAID_SETTLEMENT_STATUS,
    Stage1PaidProvisioningRequest,
    Stage1PaidProvisioningResult,
    build_stage1_paid_provisioning_request,
)
from src.application.use_cases.subscriptions.stage1_payment_provisioning import (
    handle_stage1_paid_webhook_provisioning,
)
from src.application.use_cases.subscriptions.stage1_provisioning_retry import (
    Stage1ProvisioningRetryJob,
    Stage1ProvisioningRetryJobState,
    Stage1ProvisioningRetryService,
)
from src.presentation.api.shared import (
    Stage1InMemoryWebhookIdempotencyGuard,
    Stage1OrphanPaymentAction,
    Stage1OrphanPaymentReason,
    Stage1PaymentProvider,
    Stage1WebhookSideEffect,
    extract_stage1_webhook_identity,
    resolve_stage1_provider_payment_status,
)
from src.presentation.api.shared.stage1_contract import (
    Stage1AccessState,
    Stage1PaymentState,
    Stage1ProvisioningState,
    Stage1SupportState,
)

NOW = datetime(2026, 5, 4, 12, 0, tzinfo=UTC)


class InMemoryRetryQueue:
    def __init__(self) -> None:
        self.jobs: dict[str, Stage1ProvisioningRetryJob] = {}
        self.saved: list[Stage1ProvisioningRetryJob] = []

    async def save_retry_job(self, job: Stage1ProvisioningRetryJob) -> Stage1ProvisioningRetryJob:
        self.jobs[str(job.job_id)] = job
        self.saved.append(job)
        return job


class FailingPaidGateway:
    def __init__(self) -> None:
        self.requests: list[Stage1PaidProvisioningRequest] = []

    async def provision_paid_access(
        self,
        request: Stage1PaidProvisioningRequest,
    ) -> Stage1PaidProvisioningResult:
        self.requests.append(request)
        raise ConnectionError("remnawave unavailable token=should-not-leak")


class SuccessfulPaidGateway:
    def __init__(self) -> None:
        self.requests: list[Stage1PaidProvisioningRequest] = []

    async def provision_paid_access(
        self,
        request: Stage1PaidProvisioningRequest,
    ) -> Stage1PaidProvisioningResult:
        self.requests.append(request)
        return Stage1PaidProvisioningResult(
            customer_account_id=request.customer_account_id,
            order_id=request.order_id,
            remnawave_uuid=str(uuid4()),
            profile_id=request.profile_id,
            status="active",
            expires_at=request.access_expires_at,
            subscription_url="https://subscription.example.local/raw-secret-config",
            created=True,
        )


def _cryptobot_paid_payload() -> dict[str, Any]:
    return {
        "update_id": 901001,
        "update_type": "invoice_paid",
        "payload": {
            "invoice_id": "raw-cryptobot-invoice-123",
            "hash": "raw-provider-hash-should-not-leak",
            "status": "paid",
        },
    }


def _paid_request(*, source_payment_id: str = "raw-provider-payment-id") -> Stage1PaidProvisioningRequest:
    return build_stage1_paid_provisioning_request(
        customer_account_id=uuid4(),
        order_id=uuid4(),
        email="paid-user@example.test",
        username="paid-user",
        telegram_id=777,
        order_status=STAGE1_PAID_ORDER_STATUS,
        settlement_status=STAGE1_PAID_SETTLEMENT_STATUS,
        plan_duration_days=30,
        paid_at=NOW,
        provisioning_requested_at=NOW,
        traffic_limit_bytes=200 * 1024 * 1024 * 1024,
        device_limit=3,
        source_provider=Stage1PaymentProvider.CRYPTOBOT.value,
        source_payment_id=source_payment_id,
    )


@pytest.mark.asyncio
async def test_stage1_pay_008_preserves_paid_state_and_queues_retry_on_provisioning_failure() -> None:
    identity = extract_stage1_webhook_identity(Stage1PaymentProvider.CRYPTOBOT, _cryptobot_paid_payload())
    webhook_decision = Stage1InMemoryWebhookIdempotencyGuard().record(identity)
    payment_decision = resolve_stage1_provider_payment_status(identity.provider, identity.normalized_status)
    queue = InMemoryRetryQueue()
    gateway = FailingPaidGateway()

    result = await handle_stage1_paid_webhook_provisioning(
        payment_decision=payment_decision,
        webhook_decision=webhook_decision,
        paid_request=_paid_request(source_payment_id=identity.provider_payment_id),
        gateway=gateway,
        retry_service=Stage1ProvisioningRetryService(queue=queue, now=lambda: NOW),
        provider_payment_id=identity.provider_payment_id,
        payment_id="internal-payment-should-not-leak",
        detected_at=NOW - timedelta(minutes=10),
        observed_at=NOW,
    )

    assert result.payment_state == Stage1PaymentState.PAID
    assert result.paid_state_preserved is True
    assert result.provisioning_state == Stage1ProvisioningState.RETRYING
    assert result.access_state == Stage1AccessState.PROVISIONING_PENDING
    assert result.support_state == Stage1SupportState.OPS_ESCALATION
    assert result.retry_queued is True
    assert result.retry_job is not None
    assert result.retry_job.state == Stage1ProvisioningRetryJobState.QUEUED
    assert result.retry_job.next_attempt_at == NOW + timedelta(seconds=60)
    assert queue.saved == [result.retry_job]
    assert len(gateway.requests) == 1
    assert result.orphan_decision is not None
    assert result.orphan_decision.reason == Stage1OrphanPaymentReason.REMNAWAVE_UNAVAILABLE
    assert Stage1OrphanPaymentAction.PRESERVE_PAID_STATE in result.orphan_decision.actions
    assert Stage1OrphanPaymentAction.QUEUE_PROVISIONING_RETRY in result.orphan_decision.actions

    safe = result.to_safe_dict()
    flow = result.to_flow_status().model_dump(mode="json")
    serialized = f"{safe} {flow}".lower()
    assert "raw-cryptobot-invoice-123" not in serialized
    assert "internal-payment-should-not-leak" not in serialized
    assert "paid-user@example.test" not in serialized
    assert "raw-provider-hash" not in serialized
    assert "token=should-not-leak" not in serialized
    assert "subscription.example.local" not in serialized


@pytest.mark.asyncio
async def test_stage1_pay_008_duplicate_paid_webhook_does_not_queue_second_provisioning_job() -> None:
    guard = Stage1InMemoryWebhookIdempotencyGuard()
    identity = extract_stage1_webhook_identity(Stage1PaymentProvider.CRYPTOBOT, _cryptobot_paid_payload())
    payment_decision = resolve_stage1_provider_payment_status(identity.provider, identity.normalized_status)
    queue = InMemoryRetryQueue()
    gateway = FailingPaidGateway()
    first_webhook = guard.record(identity)

    first = await handle_stage1_paid_webhook_provisioning(
        payment_decision=payment_decision,
        webhook_decision=first_webhook,
        paid_request=_paid_request(source_payment_id=identity.provider_payment_id),
        gateway=gateway,
        retry_service=Stage1ProvisioningRetryService(queue=queue, now=lambda: NOW),
        provider_payment_id=identity.provider_payment_id,
        payment_id="internal-payment-1",
        detected_at=NOW,
        observed_at=NOW,
    )
    duplicate_webhook = guard.record(identity)
    duplicate = await handle_stage1_paid_webhook_provisioning(
        payment_decision=payment_decision,
        webhook_decision=duplicate_webhook,
        paid_request=_paid_request(source_payment_id=identity.provider_payment_id),
        gateway=gateway,
        retry_service=Stage1ProvisioningRetryService(queue=queue, now=lambda: NOW),
        provider_payment_id=identity.provider_payment_id,
        payment_id="internal-payment-1",
        detected_at=NOW,
        observed_at=NOW,
    )

    assert first.retry_queued is True
    assert duplicate.webhook_duplicate is True
    assert duplicate.provisioning_attempted is False
    assert duplicate.retry_queued is False
    assert duplicate.paid_state_preserved is True
    assert duplicate.skipped_reason == "webhook_provisioning_side_effect_already_applied"
    assert len(queue.saved) == 1
    assert len(gateway.requests) == 1


@pytest.mark.asyncio
async def test_stage1_pay_008_non_final_payment_never_attempts_provisioning() -> None:
    identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.CRYPTOBOT,
        {
            "update_id": 901002,
            "update_type": "invoice_created",
            "payload": {"invoice_id": "raw-pending-invoice"},
        },
    )
    webhook_decision = Stage1InMemoryWebhookIdempotencyGuard().record(
        identity,
        side_effects=(Stage1WebhookSideEffect.PAYMENT_STATUS_UPDATE,),
    )
    payment_decision = resolve_stage1_provider_payment_status(identity.provider, "active")
    queue = InMemoryRetryQueue()
    gateway = FailingPaidGateway()

    result = await handle_stage1_paid_webhook_provisioning(
        payment_decision=payment_decision,
        webhook_decision=webhook_decision,
        paid_request=None,
        gateway=gateway,
        retry_service=Stage1ProvisioningRetryService(queue=queue, now=lambda: NOW),
        provider_payment_id=identity.provider_payment_id,
        payment_id=None,
        detected_at=NOW,
        observed_at=NOW,
    )

    assert result.payment_state == Stage1PaymentState.PENDING
    assert result.provisioning_attempted is False
    assert result.retry_queued is False
    assert result.access_state == Stage1AccessState.PAYMENT_PENDING
    assert queue.saved == []
    assert gateway.requests == []


@pytest.mark.asyncio
async def test_stage1_pay_008_successful_provisioning_completes_flow_without_manual_review() -> None:
    identity = extract_stage1_webhook_identity(Stage1PaymentProvider.CRYPTOBOT, _cryptobot_paid_payload())
    webhook_decision = Stage1InMemoryWebhookIdempotencyGuard().record(identity)
    payment_decision = resolve_stage1_provider_payment_status(identity.provider, identity.normalized_status)
    queue = InMemoryRetryQueue()
    gateway = SuccessfulPaidGateway()

    result = await handle_stage1_paid_webhook_provisioning(
        payment_decision=payment_decision,
        webhook_decision=webhook_decision,
        paid_request=_paid_request(source_payment_id=identity.provider_payment_id),
        gateway=gateway,
        retry_service=Stage1ProvisioningRetryService(queue=queue, now=lambda: NOW),
        provider_payment_id=identity.provider_payment_id,
        payment_id="internal-payment-1",
        detected_at=NOW,
        observed_at=NOW,
    )

    assert result.payment_state == Stage1PaymentState.PAID
    assert result.access_state == Stage1AccessState.ACTIVE
    assert result.provisioning_state == Stage1ProvisioningState.READY
    assert result.retry_queued is False
    assert result.manual_review_required is False
    assert queue.saved == []
    assert len(gateway.requests) == 1


@pytest.mark.asyncio
async def test_stage1_pay_008_e2e_webhook_route_failure_is_safe_and_idempotent() -> None:
    app = FastAPI()
    guard = Stage1InMemoryWebhookIdempotencyGuard()
    queue = InMemoryRetryQueue()
    gateway = FailingPaidGateway()

    @app.post("/s1/webhooks/cryptobot")
    async def cryptobot_webhook(payload: dict[str, Any]) -> dict[str, Any]:
        identity = extract_stage1_webhook_identity(Stage1PaymentProvider.CRYPTOBOT, payload)
        webhook_decision = guard.record(identity)
        payment_decision = resolve_stage1_provider_payment_status(identity.provider, identity.normalized_status)
        result = await handle_stage1_paid_webhook_provisioning(
            payment_decision=payment_decision,
            webhook_decision=webhook_decision,
            paid_request=_paid_request(source_payment_id=identity.provider_payment_id),
            gateway=gateway,
            retry_service=Stage1ProvisioningRetryService(queue=queue, now=lambda: NOW),
            provider_payment_id=identity.provider_payment_id,
            payment_id="internal-payment-should-not-leak",
            detected_at=NOW - timedelta(minutes=5),
            observed_at=NOW,
        )
        return {
            "flow": result.to_flow_status().model_dump(mode="json"),
            "safe": result.to_safe_dict(),
        }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://backend") as client:
        first = await client.post("/s1/webhooks/cryptobot", json=_cryptobot_paid_payload())
        duplicate = await client.post("/s1/webhooks/cryptobot", json=_cryptobot_paid_payload())

    assert first.status_code == 200
    first_body = first.json()
    assert first_body["flow"]["payment_state"] == "paid"
    assert first_body["flow"]["provisioning_state"] == "retrying"
    assert first_body["flow"]["access_state"] == "provisioning_pending"
    assert first_body["flow"]["details"]["retry_queued"] is True
    assert first_body["safe"]["paid_state_preserved"] is True
    assert first_body["safe"]["retry_queued"] is True

    assert duplicate.status_code == 200
    duplicate_body = duplicate.json()
    assert duplicate_body["safe"]["webhook_duplicate"] is True
    assert duplicate_body["safe"]["provisioning_attempted"] is False
    assert duplicate_body["safe"]["retry_queued"] is False
    assert len(queue.saved) == 1
    assert len(gateway.requests) == 1

    serialized = f"{first_body} {duplicate_body}".lower()
    assert "raw-cryptobot-invoice-123" not in serialized
    assert "raw-provider-hash" not in serialized
    assert "internal-payment-should-not-leak" not in serialized
    assert "paid-user@example.test" not in serialized
    assert "token=should-not-leak" not in serialized
