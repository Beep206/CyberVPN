"""Stage 1 provisioning retry contract for Remnawave-backed VPN access."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from src.application.use_cases.subscriptions.stage1_paid_provisioning import (
    Stage1PaidProvisioningGateway,
    Stage1PaidProvisioningRequest,
    Stage1PaidProvisioningResult,
)
from src.application.use_cases.trial.stage1_trial_provisioning import (
    Stage1TrialProvisioningGateway,
    Stage1TrialProvisioningRequest,
    Stage1TrialProvisioningResult,
)
from src.presentation.api.shared.stage1_contract import (
    JsonScalar,
    Stage1AccessState,
    Stage1ErrorCode,
    Stage1FlowStatusResponse,
    Stage1PaymentState,
    Stage1ProvisioningState,
    Stage1SupportState,
)

STAGE1_PROVISIONING_RETRY_QUEUE_NAME = "stage1_provisioning_retry"


class Stage1ProvisioningRetryOperation(StrEnum):
    """S1 provisioning operation types that may be retried."""

    TRIAL_ACCESS = "trial_access"
    PAID_ACCESS = "paid_access"


class Stage1ProvisioningRetryJobState(StrEnum):
    """Durable retry job lifecycle state."""

    QUEUED = "queued"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    DEAD_LETTER = "dead_letter"


class Stage1ProvisioningRetryReason(StrEnum):
    """Reason a provisioning attempt entered retry handling."""

    REMNAWAVE_UNAVAILABLE = "remnawave_unavailable"
    PROVISIONING_FAILED = "provisioning_failed"


Stage1ProvisioningRetryResult = Stage1PaidProvisioningResult | Stage1TrialProvisioningResult


@dataclass(frozen=True, slots=True)
class Stage1ProvisioningRetryPolicy:
    """Backoff policy for S1 Remnawave provisioning retries."""

    initial_delay_seconds: int = 60
    backoff_multiplier: int = 2
    max_delay_seconds: int = 15 * 60
    max_attempts: int = 6

    def delay_for_attempt(self, attempt_count: int) -> int:
        """Return retry delay after the given failed attempt count."""

        if attempt_count <= 0:
            raise ValueError("attempt_count must be positive")
        delay = self.initial_delay_seconds * (self.backoff_multiplier ** (attempt_count - 1))
        return min(delay, self.max_delay_seconds)

    def next_attempt_at(self, *, failed_at: datetime, attempt_count: int) -> datetime:
        """Return the next attempt timestamp after a failed attempt."""

        return _ensure_aware_utc(failed_at) + timedelta(seconds=self.delay_for_attempt(attempt_count))


@dataclass(frozen=True, slots=True)
class Stage1ProvisioningRetryJob:
    """Safe retry job record that can be stored in PostgreSQL-backed queue tables."""

    operation: Stage1ProvisioningRetryOperation
    customer_account_id: UUID
    correlation_id: str
    request_payload: dict[str, JsonScalar]
    queued_at: datetime
    next_attempt_at: datetime
    attempt_count: int
    max_attempts: int
    reason: Stage1ProvisioningRetryReason
    error_code: Stage1ErrorCode
    provisioning_state: Stage1ProvisioningState
    support_state: Stage1SupportState
    job_id: UUID = field(default_factory=uuid4)
    queue_name: str = STAGE1_PROVISIONING_RETRY_QUEUE_NAME
    state: Stage1ProvisioningRetryJobState = Stage1ProvisioningRetryJobState.QUEUED
    payment_state: Stage1PaymentState | None = None
    last_error_code: str = ""
    last_error_message: str = "Provisioning failed; details redacted."
    completed_at: datetime | None = None
    result_payload: dict[str, JsonScalar] = field(default_factory=dict)

    def to_safe_dict(self) -> dict[str, JsonScalar | dict[str, JsonScalar]]:
        """Serialize retry state without provider secrets, raw config links or PII."""

        return {
            "job_id": str(self.job_id),
            "queue_name": self.queue_name,
            "operation": self.operation.value,
            "state": self.state.value,
            "customer_account_id": str(self.customer_account_id),
            "correlation_id": self.correlation_id,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "queued_at": self.queued_at.isoformat(),
            "next_attempt_at": self.next_attempt_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "reason": self.reason.value,
            "error_code": self.error_code.value,
            "provisioning_state": self.provisioning_state.value,
            "payment_state": self.payment_state.value if self.payment_state else None,
            "support_state": self.support_state.value,
            "last_error_code": self.last_error_code,
            "last_error_message": self.last_error_message,
            "request_payload": self.request_payload,
            "result_payload": self.result_payload,
        }


@dataclass(frozen=True, slots=True)
class Stage1ProvisioningRetryDecision:
    """Result of a provisioning attempt with retry handling."""

    provisioning_state: Stage1ProvisioningState
    support_state: Stage1SupportState
    retry_job: Stage1ProvisioningRetryJob | None = None
    result: Stage1ProvisioningRetryResult | None = None
    payment_state: Stage1PaymentState | None = None
    queued_for_retry: bool = False
    completed: bool = False

    def to_flow_status(self) -> Stage1FlowStatusResponse:
        """Convert retry decision into the common S1 flow status response."""

        return Stage1FlowStatusResponse(
            access_state=Stage1AccessState.ACTIVE if self.completed else Stage1AccessState.PROVISIONING_PENDING,
            payment_state=self.payment_state or Stage1PaymentState.NOT_STARTED,
            provisioning_state=self.provisioning_state,
            support_state=self.support_state,
            user_action=None if self.completed else "Wait for automatic provisioning retry or contact support.",
            support_escalation=self.support_state != Stage1SupportState.NONE,
            details=self._flow_details(),
        )

    def _flow_details(self) -> dict[str, JsonScalar]:
        if self.retry_job is None:
            return {}
        return {
            "retry_job_id": str(self.retry_job.job_id),
            "queue_name": self.retry_job.queue_name,
            "operation": self.retry_job.operation.value,
            "attempt_count": self.retry_job.attempt_count,
            "next_attempt_at": self.retry_job.next_attempt_at.isoformat(),
            "reason": self.retry_job.reason.value,
        }


class Stage1ProvisioningRetryQueue(Protocol):
    """Queue abstraction implemented by durable storage or tests."""

    async def save_retry_job(self, job: Stage1ProvisioningRetryJob) -> Stage1ProvisioningRetryJob:
        """Persist or update a provisioning retry job."""


class Stage1ProvisioningRetryService:
    """Runs provisioning attempts and records durable retry jobs on Remnawave failures."""

    def __init__(
        self,
        *,
        queue: Stage1ProvisioningRetryQueue,
        policy: Stage1ProvisioningRetryPolicy | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._queue = queue
        self._policy = policy or Stage1ProvisioningRetryPolicy()
        self._now = now or (lambda: datetime.now(UTC))

    async def provision_paid_or_queue(
        self,
        *,
        request: Stage1PaidProvisioningRequest,
        gateway: Stage1PaidProvisioningGateway,
    ) -> Stage1ProvisioningRetryDecision:
        """Provision paid access or queue a retry if Remnawave is unavailable."""

        return await self._execute_or_queue(
            operation=Stage1ProvisioningRetryOperation.PAID_ACCESS,
            customer_account_id=request.customer_account_id,
            correlation_id=str(request.order_id),
            request_payload=_safe_paid_request_payload(request),
            payment_state=Stage1PaymentState.PAID,
            action=lambda: gateway.provision_paid_access(request),
        )

    async def retry_paid_job(
        self,
        *,
        job: Stage1ProvisioningRetryJob,
        request: Stage1PaidProvisioningRequest,
        gateway: Stage1PaidProvisioningGateway,
    ) -> Stage1ProvisioningRetryDecision:
        """Retry a queued paid provisioning job."""

        return await self._retry_job(
            job=job,
            action=lambda: gateway.provision_paid_access(request),
            payment_state=Stage1PaymentState.PAID,
        )

    async def provision_trial_or_queue(
        self,
        *,
        request: Stage1TrialProvisioningRequest,
        gateway: Stage1TrialProvisioningGateway,
    ) -> Stage1ProvisioningRetryDecision:
        """Provision trial access or queue a retry if Remnawave is unavailable."""

        return await self._execute_or_queue(
            operation=Stage1ProvisioningRetryOperation.TRIAL_ACCESS,
            customer_account_id=request.customer_account_id,
            correlation_id=str(request.customer_account_id),
            request_payload=_safe_trial_request_payload(request),
            payment_state=None,
            action=lambda: gateway.provision_trial_access(request),
        )

    async def retry_trial_job(
        self,
        *,
        job: Stage1ProvisioningRetryJob,
        request: Stage1TrialProvisioningRequest,
        gateway: Stage1TrialProvisioningGateway,
    ) -> Stage1ProvisioningRetryDecision:
        """Retry a queued trial provisioning job."""

        return await self._retry_job(
            job=job,
            action=lambda: gateway.provision_trial_access(request),
            payment_state=None,
        )

    async def _execute_or_queue(
        self,
        *,
        operation: Stage1ProvisioningRetryOperation,
        customer_account_id: UUID,
        correlation_id: str,
        request_payload: dict[str, JsonScalar],
        payment_state: Stage1PaymentState | None,
        action: Callable[[], Awaitable[Stage1ProvisioningRetryResult]],
    ) -> Stage1ProvisioningRetryDecision:
        try:
            result = await action()
        except Exception as exc:  # noqa: BLE001 - gateway boundaries differ by HTTP client.
            now = _ensure_aware_utc(self._now())
            retry_job = _build_retry_job(
                operation=operation,
                customer_account_id=customer_account_id,
                correlation_id=correlation_id,
                request_payload=request_payload,
                payment_state=payment_state,
                failed_at=now,
                attempt_count=1,
                policy=self._policy,
                error=exc,
            )
            saved_job = await self._queue.save_retry_job(retry_job)
            return Stage1ProvisioningRetryDecision(
                provisioning_state=Stage1ProvisioningState.RETRYING,
                payment_state=payment_state,
                support_state=Stage1SupportState.OPS_ESCALATION,
                retry_job=saved_job,
                queued_for_retry=True,
                completed=False,
            )

        return Stage1ProvisioningRetryDecision(
            provisioning_state=Stage1ProvisioningState.READY,
            payment_state=payment_state,
            support_state=Stage1SupportState.NONE,
            result=result,
            completed=True,
        )

    async def _retry_job(
        self,
        *,
        job: Stage1ProvisioningRetryJob,
        action: Callable[[], Awaitable[Stage1ProvisioningRetryResult]],
        payment_state: Stage1PaymentState | None,
    ) -> Stage1ProvisioningRetryDecision:
        try:
            result = await action()
        except Exception as exc:  # noqa: BLE001 - gateway boundaries differ by HTTP client.
            failed_at = _ensure_aware_utc(self._now())
            next_attempt_count = job.attempt_count + 1
            if next_attempt_count >= job.max_attempts:
                updated_job = replace(
                    job,
                    state=Stage1ProvisioningRetryJobState.DEAD_LETTER,
                    attempt_count=next_attempt_count,
                    provisioning_state=Stage1ProvisioningState.RECONCILIATION_REQUIRED,
                    support_state=Stage1SupportState.OPS_ESCALATION,
                    last_error_code=exc.__class__.__name__,
                    last_error_message=_redacted_error_message(),
                    completed_at=failed_at,
                )
                saved_job = await self._queue.save_retry_job(updated_job)
                return Stage1ProvisioningRetryDecision(
                    provisioning_state=Stage1ProvisioningState.RECONCILIATION_REQUIRED,
                    payment_state=payment_state,
                    support_state=Stage1SupportState.OPS_ESCALATION,
                    retry_job=saved_job,
                    queued_for_retry=False,
                    completed=False,
                )

            updated_job = replace(
                job,
                state=Stage1ProvisioningRetryJobState.RETRYING,
                attempt_count=next_attempt_count,
                next_attempt_at=self._policy.next_attempt_at(
                    failed_at=failed_at,
                    attempt_count=next_attempt_count,
                ),
                last_error_code=exc.__class__.__name__,
                last_error_message=_redacted_error_message(),
            )
            saved_job = await self._queue.save_retry_job(updated_job)
            return Stage1ProvisioningRetryDecision(
                provisioning_state=Stage1ProvisioningState.RETRYING,
                payment_state=payment_state,
                support_state=Stage1SupportState.OPS_ESCALATION,
                retry_job=saved_job,
                queued_for_retry=True,
                completed=False,
            )

        completed_at = _ensure_aware_utc(self._now())
        updated_job = replace(
            job,
            state=Stage1ProvisioningRetryJobState.SUCCEEDED,
            provisioning_state=Stage1ProvisioningState.READY,
            support_state=Stage1SupportState.NONE,
            completed_at=completed_at,
            result_payload=_safe_result_payload(result),
        )
        saved_job = await self._queue.save_retry_job(updated_job)
        return Stage1ProvisioningRetryDecision(
            provisioning_state=Stage1ProvisioningState.READY,
            payment_state=payment_state,
            support_state=Stage1SupportState.NONE,
            retry_job=saved_job,
            result=result,
            queued_for_retry=False,
            completed=True,
        )


def _build_retry_job(
    *,
    operation: Stage1ProvisioningRetryOperation,
    customer_account_id: UUID,
    correlation_id: str,
    request_payload: dict[str, JsonScalar],
    payment_state: Stage1PaymentState | None,
    failed_at: datetime,
    attempt_count: int,
    policy: Stage1ProvisioningRetryPolicy,
    error: Exception,
) -> Stage1ProvisioningRetryJob:
    return Stage1ProvisioningRetryJob(
        operation=operation,
        customer_account_id=customer_account_id,
        correlation_id=correlation_id,
        request_payload=request_payload,
        queued_at=failed_at,
        next_attempt_at=policy.next_attempt_at(failed_at=failed_at, attempt_count=attempt_count),
        attempt_count=attempt_count,
        max_attempts=policy.max_attempts,
        reason=Stage1ProvisioningRetryReason.REMNAWAVE_UNAVAILABLE,
        error_code=Stage1ErrorCode.REMNAWAVE_UNAVAILABLE,
        provisioning_state=Stage1ProvisioningState.RETRYING,
        support_state=Stage1SupportState.OPS_ESCALATION,
        payment_state=payment_state,
        last_error_code=error.__class__.__name__,
        last_error_message=_redacted_error_message(),
    )


def _safe_paid_request_payload(request: Stage1PaidProvisioningRequest) -> dict[str, JsonScalar]:
    return {
        "customer_account_id": str(request.customer_account_id),
        "order_id": str(request.order_id),
        "profile_id": request.profile_id,
        "access_expires_at": request.access_expires_at.isoformat(),
        "traffic_limit_bytes": request.traffic_limit_bytes,
        "device_limit": request.device_limit,
        "source_provider": request.source_provider,
        "has_existing_remnawave_uuid": request.existing_remnawave_uuid is not None,
    }


def _safe_trial_request_payload(request: Stage1TrialProvisioningRequest) -> dict[str, JsonScalar]:
    return {
        "customer_account_id": str(request.customer_account_id),
        "profile_id": request.profile_id,
        "trial_expires_at": request.trial_expires_at.isoformat(),
        "traffic_limit_bytes": request.traffic_limit_bytes,
        "device_limit": request.device_limit,
        "has_existing_remnawave_uuid": request.existing_remnawave_uuid is not None,
    }


def _safe_result_payload(result: Stage1ProvisioningRetryResult) -> dict[str, JsonScalar]:
    safe = result.to_safe_dict()
    return {key: value for key, value in safe.items() if isinstance(value, str | int | float | bool) or value is None}


def _redacted_error_message() -> str:
    return "Remnawave provisioning attempt failed; details redacted."


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
