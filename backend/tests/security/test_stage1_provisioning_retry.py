"""S1-VPN-006 provisioning retry checks."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.application.use_cases.subscriptions.stage1_paid_provisioning import (
    STAGE1_PAID_ORDER_STATUS,
    STAGE1_PAID_SETTLEMENT_STATUS,
    Stage1PaidProvisioningRequest,
    Stage1PaidProvisioningResult,
    build_stage1_paid_provisioning_request,
)
from src.application.use_cases.subscriptions.stage1_provisioning_retry import (
    Stage1ProvisioningRetryJob,
    Stage1ProvisioningRetryJobState,
    Stage1ProvisioningRetryOperation,
    Stage1ProvisioningRetryPolicy,
    Stage1ProvisioningRetryService,
)
from src.application.use_cases.subscriptions.stage1_provisioning_retry_worker import Stage1ProvisioningRetryWorker
from src.application.use_cases.trial.stage1_trial_provisioning import (
    STAGE1_TRIAL_DURATION_DAYS,
    Stage1TrialProvisioningRequest,
    Stage1TrialProvisioningResult,
    build_stage1_trial_provisioning_request,
)
from src.presentation.api.shared import STAGE1_DEFAULT_VPN_PROFILE_ID
from src.presentation.api.shared.stage1_contract import (
    Stage1AccessState,
    Stage1PaymentState,
    Stage1ProvisioningState,
    Stage1SupportState,
)


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value

    def advance(self, delta: timedelta) -> None:
        self.value += delta


class InMemoryRetryQueue:
    def __init__(self) -> None:
        self.jobs: dict[str, Stage1ProvisioningRetryJob] = {}
        self.saved: list[Stage1ProvisioningRetryJob] = []

    async def save_retry_job(self, job: Stage1ProvisioningRetryJob) -> Stage1ProvisioningRetryJob:
        self.jobs[str(job.job_id)] = job
        self.saved.append(job)
        return job


class DurableLikeRetryQueue(InMemoryRetryQueue):
    def __init__(self) -> None:
        super().__init__()
        self.jobs_by_key: dict[tuple[str, str], Stage1ProvisioningRetryJob] = {}

    async def save_retry_job(self, job: Stage1ProvisioningRetryJob) -> Stage1ProvisioningRetryJob:
        key = (job.operation.value, job.correlation_id)
        existing = self.jobs_by_key.get(key)
        if (
            existing is not None
            and existing.job_id != job.job_id
            and existing.state
            in {
                Stage1ProvisioningRetryJobState.QUEUED,
                Stage1ProvisioningRetryJobState.RETRYING,
            }
        ):
            self.saved.append(existing)
            return existing
        self.jobs_by_key[key] = job
        return await super().save_retry_job(job)

    async def claim_due_jobs(
        self,
        *,
        now: datetime,
        limit: int,
        worker_id: str,
    ) -> list[Stage1ProvisioningRetryJob]:
        _ = worker_id
        due = [
            job
            for job in self.jobs_by_key.values()
            if job.state in {Stage1ProvisioningRetryJobState.QUEUED, Stage1ProvisioningRetryJobState.RETRYING}
            and job.next_attempt_at <= now
        ]
        return due[:limit]

    async def mark_reconciliation_required(
        self,
        job: Stage1ProvisioningRetryJob,
        *,
        completed_at: datetime,
        error_code: str,
    ) -> Stage1ProvisioningRetryJob:
        updated = replace(
            job,
            state=Stage1ProvisioningRetryJobState.DEAD_LETTER,
            provisioning_state=Stage1ProvisioningState.RECONCILIATION_REQUIRED,
            support_state=Stage1SupportState.OPS_ESCALATION,
            completed_at=completed_at,
            last_error_code=error_code,
            last_error_message="Remnawave provisioning retry requires reconciliation; details redacted.",
        )
        return await self.save_retry_job(updated)

    async def metrics_snapshot(self, *, now: datetime) -> dict:
        active = [
            job
            for job in self.jobs_by_key.values()
            if job.state in {Stage1ProvisioningRetryJobState.QUEUED, Stage1ProvisioningRetryJobState.RETRYING}
        ]
        max_age_seconds = int(max(((now - job.queued_at).total_seconds() for job in active), default=0))
        return {
            "counts_by_state": {
                state.value: sum(1 for job in self.jobs_by_key.values() if job.state == state)
                for state in Stage1ProvisioningRetryJobState
            },
            "max_job_age_seconds": max_age_seconds,
        }


class FlakyPaidGateway:
    def __init__(self, outcomes: list[Exception | Stage1PaidProvisioningResult]) -> None:
        self.outcomes = outcomes
        self.requests: list[Stage1PaidProvisioningRequest] = []

    async def provision_paid_access(
        self,
        request: Stage1PaidProvisioningRequest,
    ) -> Stage1PaidProvisioningResult:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FlakyTrialGateway:
    def __init__(self, outcomes: list[Exception | Stage1TrialProvisioningResult]) -> None:
        self.outcomes = outcomes
        self.requests: list[Stage1TrialProvisioningRequest] = []

    async def provision_trial_access(
        self,
        request: Stage1TrialProvisioningRequest,
    ) -> Stage1TrialProvisioningResult:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_stage1_retry_policy_uses_capped_exponential_backoff() -> None:
    policy = Stage1ProvisioningRetryPolicy(initial_delay_seconds=60, backoff_multiplier=2, max_delay_seconds=900)
    failed_at = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)

    assert policy.delay_for_attempt(1) == 60
    assert policy.delay_for_attempt(2) == 120
    assert policy.delay_for_attempt(5) == 900
    assert policy.next_attempt_at(failed_at=failed_at, attempt_count=2) == failed_at + timedelta(seconds=120)


@pytest.mark.asyncio
async def test_stage1_paid_remnawave_outage_preserves_paid_state_and_queues_retry() -> None:
    clock = MutableClock(datetime(2026, 5, 4, 9, 30, tzinfo=UTC))
    queue = InMemoryRetryQueue()
    request = _build_paid_request(clock.value, source_payment_id="provider-payment-should-not-leak")
    gateway = FlakyPaidGateway([ConnectionError("remnawave down token=should-not-leak")])

    decision = await Stage1ProvisioningRetryService(queue=queue, now=clock).provision_paid_or_queue(
        request=request,
        gateway=gateway,
    )

    assert decision.queued_for_retry is True
    assert decision.completed is False
    assert decision.payment_state == Stage1PaymentState.PAID
    assert decision.provisioning_state == Stage1ProvisioningState.RETRYING
    assert decision.support_state == Stage1SupportState.OPS_ESCALATION
    assert decision.retry_job is not None
    job = decision.retry_job
    assert queue.jobs[str(job.job_id)] is job
    assert job.operation == Stage1ProvisioningRetryOperation.PAID_ACCESS
    assert job.state == Stage1ProvisioningRetryJobState.QUEUED
    assert job.attempt_count == 1
    assert job.next_attempt_at == clock.value + timedelta(seconds=60)
    assert job.request_payload["order_id"] == str(request.order_id)
    assert job.request_payload["has_existing_remnawave_uuid"] is False
    serialized = str(job.to_safe_dict()).lower()
    assert "paid-user@example.test" not in serialized
    assert "provider-payment-should-not-leak" not in serialized
    assert "subscription" not in serialized
    assert "config_link" not in serialized
    assert "secret" not in serialized
    assert "token=should-not-leak" not in serialized


@pytest.mark.asyncio
async def test_stage1_paid_retry_queue_is_idempotent_by_operation_and_correlation() -> None:
    clock = MutableClock(datetime(2026, 5, 4, 9, 30, tzinfo=UTC))
    queue = DurableLikeRetryQueue()
    request = _build_paid_request(clock.value)
    service = Stage1ProvisioningRetryService(queue=queue, now=clock)

    first = await service.provision_paid_or_queue(
        request=request,
        gateway=FlakyPaidGateway([ConnectionError("remnawave down")]),
    )
    duplicate = await service.provision_paid_or_queue(
        request=request,
        gateway=FlakyPaidGateway([TimeoutError("same webhook replay")]),
    )

    assert first.retry_job is not None
    assert duplicate.retry_job is not None
    assert duplicate.retry_job.job_id == first.retry_job.job_id
    assert len(queue.jobs_by_key) == 1
    assert duplicate.retry_job.attempt_count == 1


@pytest.mark.asyncio
async def test_stage1_paid_retry_later_succeeds_and_marks_job_ready() -> None:
    clock = MutableClock(datetime(2026, 5, 4, 9, 30, tzinfo=UTC))
    queue = InMemoryRetryQueue()
    request = _build_paid_request(clock.value)
    service = Stage1ProvisioningRetryService(queue=queue, now=clock)

    first = await service.provision_paid_or_queue(
        request=request,
        gateway=FlakyPaidGateway([TimeoutError("remnawave timeout password=should-not-leak")]),
    )
    assert first.retry_job is not None
    clock.advance(timedelta(seconds=60))

    success = Stage1PaidProvisioningResult(
        customer_account_id=request.customer_account_id,
        order_id=request.order_id,
        remnawave_uuid=str(uuid4()),
        profile_id=request.profile_id,
        status="active",
        expires_at=request.access_expires_at,
        subscription_url="https://subscription.example.local/sub/redacted-paid",
        created=True,
    )
    retry = await service.retry_paid_job(
        job=first.retry_job,
        request=request,
        gateway=FlakyPaidGateway([success]),
    )

    assert retry.completed is True
    assert retry.queued_for_retry is False
    assert retry.provisioning_state == Stage1ProvisioningState.READY
    assert retry.support_state == Stage1SupportState.NONE
    assert retry.result is success
    assert retry.retry_job is not None
    assert retry.retry_job.state == Stage1ProvisioningRetryJobState.SUCCEEDED
    assert retry.retry_job.completed_at == clock.value
    assert retry.retry_job.result_payload["profile_id"] == STAGE1_DEFAULT_VPN_PROFILE_ID
    assert "subscription" not in str(retry.retry_job.to_safe_dict()).lower()


@pytest.mark.asyncio
async def test_stage1_worker_replays_due_job_from_durable_state_after_broker_restart() -> None:
    clock = MutableClock(datetime(2026, 5, 4, 9, 30, tzinfo=UTC))
    queue = DurableLikeRetryQueue()
    request = _build_paid_request(clock.value)
    service = Stage1ProvisioningRetryService(queue=queue, now=clock)
    first = await service.provision_paid_or_queue(
        request=request,
        gateway=FlakyPaidGateway([ConnectionError("redis stream lost but postgres kept the job")]),
    )
    assert first.retry_job is not None
    clock.advance(timedelta(seconds=60))
    success = Stage1PaidProvisioningResult(
        customer_account_id=request.customer_account_id,
        order_id=request.order_id,
        remnawave_uuid=str(uuid4()),
        profile_id=request.profile_id,
        status="active",
        expires_at=request.access_expires_at,
        subscription_url="https://subscription.example.local/sub/redacted-paid",
        created=False,
    )

    result = await Stage1ProvisioningRetryWorker(
        repository=queue,
        retry_service=service,
        paid_gateway=FlakyPaidGateway([success]),
        trial_gateway=FlakyTrialGateway([]),
        now=clock,
    ).run_due_jobs(limit=10, worker_id="pytest-worker")

    assert result.claimed == 1
    assert result.succeeded == 1
    assert result.retrying == 0
    assert result.dead_letter == 0
    assert queue.jobs_by_key[(Stage1ProvisioningRetryOperation.PAID_ACCESS.value, str(request.order_id))].state == (
        Stage1ProvisioningRetryJobState.SUCCEEDED
    )


@pytest.mark.asyncio
async def test_stage1_retry_failure_before_max_attempts_keeps_job_retrying() -> None:
    clock = MutableClock(datetime(2026, 5, 4, 9, 30, tzinfo=UTC))
    queue = InMemoryRetryQueue()
    request = _build_paid_request(clock.value)
    service = Stage1ProvisioningRetryService(queue=queue, now=clock)
    first = await service.provision_paid_or_queue(
        request=request,
        gateway=FlakyPaidGateway([ConnectionError("temporary outage")]),
    )
    assert first.retry_job is not None
    clock.advance(timedelta(seconds=60))

    retry = await service.retry_paid_job(
        job=first.retry_job,
        request=request,
        gateway=FlakyPaidGateway([ConnectionError("still unavailable")]),
    )

    assert retry.queued_for_retry is True
    assert retry.retry_job is not None
    assert retry.retry_job.state == Stage1ProvisioningRetryJobState.RETRYING
    assert retry.retry_job.attempt_count == 2
    assert retry.retry_job.next_attempt_at == clock.value + timedelta(seconds=120)
    assert retry.provisioning_state == Stage1ProvisioningState.RETRYING


@pytest.mark.asyncio
async def test_stage1_retry_exhaustion_moves_job_to_dead_letter_reconciliation() -> None:
    clock = MutableClock(datetime(2026, 5, 4, 9, 30, tzinfo=UTC))
    queue = InMemoryRetryQueue()
    request = _build_paid_request(clock.value)
    service = Stage1ProvisioningRetryService(queue=queue, now=clock)
    first = await service.provision_paid_or_queue(
        request=request,
        gateway=FlakyPaidGateway([ConnectionError("temporary outage")]),
    )
    assert first.retry_job is not None
    exhausted_job = replace(first.retry_job, attempt_count=5)

    retry = await service.retry_paid_job(
        job=exhausted_job,
        request=request,
        gateway=FlakyPaidGateway([ConnectionError("still unavailable")]),
    )

    assert retry.queued_for_retry is False
    assert retry.retry_job is not None
    assert retry.retry_job.state == Stage1ProvisioningRetryJobState.DEAD_LETTER
    assert retry.retry_job.attempt_count == 6
    assert retry.provisioning_state == Stage1ProvisioningState.RECONCILIATION_REQUIRED
    assert retry.support_state == Stage1SupportState.OPS_ESCALATION
    assert retry.to_flow_status().support_escalation is True


@pytest.mark.asyncio
async def test_stage1_worker_exhausts_due_job_to_dead_letter() -> None:
    clock = MutableClock(datetime(2026, 5, 4, 9, 30, tzinfo=UTC))
    queue = DurableLikeRetryQueue()
    request = _build_paid_request(clock.value)
    service = Stage1ProvisioningRetryService(queue=queue, now=clock)
    first = await service.provision_paid_or_queue(
        request=request,
        gateway=FlakyPaidGateway([ConnectionError("temporary outage")]),
    )
    assert first.retry_job is not None
    exhausted = replace(
        first.retry_job,
        attempt_count=5,
        next_attempt_at=clock.value,
    )
    await queue.save_retry_job(exhausted)

    result = await Stage1ProvisioningRetryWorker(
        repository=queue,
        retry_service=service,
        paid_gateway=FlakyPaidGateway([ConnectionError("still unavailable raw detail should not leak")]),
        trial_gateway=FlakyTrialGateway([]),
        now=clock,
    ).run_due_jobs(limit=10, worker_id="pytest-worker")

    stored = queue.jobs_by_key[(Stage1ProvisioningRetryOperation.PAID_ACCESS.value, str(request.order_id))]
    serialized = str(stored.to_safe_dict()).lower()
    assert result.dead_letter == 1
    assert result.reconciliation_required == 1
    assert stored.state == Stage1ProvisioningRetryJobState.DEAD_LETTER
    assert stored.provisioning_state == Stage1ProvisioningState.RECONCILIATION_REQUIRED
    assert "raw detail should not leak" not in serialized


@pytest.mark.asyncio
async def test_stage1_trial_remnawave_outage_also_queues_retry() -> None:
    clock = MutableClock(datetime(2026, 5, 4, 9, 30, tzinfo=UTC))
    queue = InMemoryRetryQueue()
    request = build_stage1_trial_provisioning_request(
        customer_account_id=uuid4(),
        email="trial-user@example.test",
        username="trial-user",
        telegram_id=123,
        trial_expires_at=clock.value + timedelta(days=STAGE1_TRIAL_DURATION_DAYS),
    )

    decision = await Stage1ProvisioningRetryService(queue=queue, now=clock).provision_trial_or_queue(
        request=request,
        gateway=FlakyTrialGateway([ConnectionError("remnawave unavailable")]),
    )

    assert decision.queued_for_retry is True
    assert decision.payment_state is None
    assert decision.retry_job is not None
    assert decision.retry_job.operation == Stage1ProvisioningRetryOperation.TRIAL_ACCESS
    assert decision.retry_job.request_payload["trial_expires_at"] == request.trial_expires_at.isoformat()
    serialized = str(decision.retry_job.to_safe_dict()).lower()
    assert "trial-user@example.test" not in serialized
    assert "subscription" not in serialized
    assert "secret" not in serialized


@pytest.mark.asyncio
async def test_stage1_retry_decision_flow_status_is_customer_safe() -> None:
    clock = MutableClock(datetime(2026, 5, 4, 9, 30, tzinfo=UTC))
    queue = InMemoryRetryQueue()
    request = _build_paid_request(clock.value)
    decision = await Stage1ProvisioningRetryService(queue=queue, now=clock).provision_paid_or_queue(
        request=request,
        gateway=FlakyPaidGateway([ConnectionError("remnawave unavailable config_link=should-not-leak")]),
    )

    flow_status = decision.to_flow_status()

    assert flow_status.access_state == Stage1AccessState.PROVISIONING_PENDING
    assert flow_status.payment_state == Stage1PaymentState.PAID
    assert flow_status.provisioning_state == Stage1ProvisioningState.RETRYING
    assert flow_status.support_state == Stage1SupportState.OPS_ESCALATION
    assert flow_status.support_escalation is True
    serialized = str(flow_status.model_dump(mode="json")).lower()
    assert "config_link=should-not-leak" not in serialized
    assert "paid-user@example.test" not in serialized
    assert "subscription" not in serialized
    assert "secret" not in serialized


def _build_paid_request(
    requested_at: datetime,
    *,
    source_payment_id: str | None = None,
) -> Stage1PaidProvisioningRequest:
    return build_stage1_paid_provisioning_request(
        customer_account_id=uuid4(),
        order_id=uuid4(),
        email="paid-user@example.test",
        username="paid-user",
        telegram_id=777,
        order_status=STAGE1_PAID_ORDER_STATUS,
        settlement_status=STAGE1_PAID_SETTLEMENT_STATUS,
        plan_duration_days=30,
        paid_at=requested_at,
        provisioning_requested_at=requested_at,
        traffic_limit_bytes=200 * 1024 * 1024 * 1024,
        device_limit=3,
        source_provider="nowpayments",
        source_payment_id=source_payment_id,
    )
