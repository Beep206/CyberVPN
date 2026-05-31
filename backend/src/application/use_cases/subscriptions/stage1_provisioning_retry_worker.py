"""Worker orchestration for durable Stage 1 provisioning retries."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from src.application.use_cases.subscriptions.stage1_paid_provisioning import (
    Stage1PaidProvisioningGateway,
    Stage1PaidProvisioningRequest,
)
from src.application.use_cases.subscriptions.stage1_provisioning_retry import (
    Stage1ProvisioningRetryDecision,
    Stage1ProvisioningRetryJob,
    Stage1ProvisioningRetryJobState,
    Stage1ProvisioningRetryOperation,
    Stage1ProvisioningRetryService,
)
from src.application.use_cases.trial.stage1_trial_provisioning import (
    Stage1TrialProvisioningGateway,
    Stage1TrialProvisioningRequest,
)
from src.presentation.api.shared.stage1_contract import JsonScalar


class Stage1ProvisioningRetryClaimRepository(Protocol):
    async def claim_due_jobs(
        self,
        *,
        now: datetime,
        limit: int,
        worker_id: str,
    ) -> list[Stage1ProvisioningRetryJob]:
        """Claim due jobs for this worker."""

    async def mark_reconciliation_required(
        self,
        job: Stage1ProvisioningRetryJob,
        *,
        completed_at: datetime,
        error_code: str,
    ) -> Stage1ProvisioningRetryJob:
        """Move an unretryable job to reconciliation-required dead-letter state."""

    async def metrics_snapshot(self, *, now: datetime) -> dict[str, JsonScalar | dict[str, JsonScalar]]:
        """Return safe queue metrics."""


@dataclass(frozen=True, slots=True)
class Stage1ProvisioningRetryWorkerResult:
    """Safe summary returned to task-worker and launch evidence."""

    claimed: int = 0
    succeeded: int = 0
    retrying: int = 0
    dead_letter: int = 0
    reconciliation_required: int = 0
    skipped: bool = False
    skipped_reason: str | None = None
    remnawave_dependency_errors: dict[str, int] = field(default_factory=dict)
    metrics: dict[str, JsonScalar | dict[str, JsonScalar]] = field(default_factory=dict)

    def to_safe_dict(self) -> dict[str, JsonScalar | dict[str, JsonScalar]]:
        return {
            "claimed": self.claimed,
            "succeeded": self.succeeded,
            "retrying": self.retrying,
            "dead_letter": self.dead_letter,
            "reconciliation_required": self.reconciliation_required,
            "skipped": self.skipped,
            "skipped_reason": self.skipped_reason,
            "remnawave_dependency_errors": dict(self.remnawave_dependency_errors),
            "metrics": self.metrics,
        }


class Stage1ProvisioningRetryWorker:
    """Claim due durable retry jobs and replay them through existing provisioning gateways."""

    def __init__(
        self,
        *,
        repository: Stage1ProvisioningRetryClaimRepository,
        retry_service: Stage1ProvisioningRetryService,
        paid_gateway: Stage1PaidProvisioningGateway,
        trial_gateway: Stage1TrialProvisioningGateway,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._retry_service = retry_service
        self._paid_gateway = paid_gateway
        self._trial_gateway = trial_gateway
        self._now = now or (lambda: datetime.now(UTC))

    async def run_due_jobs(self, *, limit: int, worker_id: str) -> Stage1ProvisioningRetryWorkerResult:
        now = _ensure_aware_utc(self._now())
        jobs = await self._repository.claim_due_jobs(now=now, limit=limit, worker_id=worker_id)
        counts = {
            "succeeded": 0,
            "retrying": 0,
            "dead_letter": 0,
            "reconciliation_required": 0,
        }
        dependency_errors: dict[str, int] = {}

        for job in jobs:
            decision = await self._retry_one(job)
            if decision.retry_job is None:
                counts["reconciliation_required"] += 1
                continue
            state = decision.retry_job.state
            if state == Stage1ProvisioningRetryJobState.SUCCEEDED:
                counts["succeeded"] += 1
            elif state == Stage1ProvisioningRetryJobState.DEAD_LETTER:
                counts["dead_letter"] += 1
                counts["reconciliation_required"] += 1
                _increment(dependency_errors, decision.retry_job.last_error_code or "RemnawaveProvisioningError")
            else:
                counts["retrying"] += 1
                _increment(dependency_errors, decision.retry_job.last_error_code or "RemnawaveProvisioningError")

        metrics = await self._repository.metrics_snapshot(now=_ensure_aware_utc(self._now()))
        return Stage1ProvisioningRetryWorkerResult(
            claimed=len(jobs),
            succeeded=counts["succeeded"],
            retrying=counts["retrying"],
            dead_letter=counts["dead_letter"],
            reconciliation_required=counts["reconciliation_required"],
            skipped=len(jobs) == 0,
            skipped_reason="no_due_jobs" if not jobs else None,
            remnawave_dependency_errors=dependency_errors,
            metrics=metrics,
        )

    async def _retry_one(self, job: Stage1ProvisioningRetryJob) -> Stage1ProvisioningRetryDecision:
        try:
            if job.operation == Stage1ProvisioningRetryOperation.PAID_ACCESS:
                return await self._retry_service.retry_paid_job(
                    job=job,
                    request=_paid_request_from_job(job),
                    gateway=self._paid_gateway,
                )
            if job.operation == Stage1ProvisioningRetryOperation.TRIAL_ACCESS:
                return await self._retry_service.retry_trial_job(
                    job=job,
                    request=_trial_request_from_job(job),
                    gateway=self._trial_gateway,
                )
        except Exception as exc:  # noqa: BLE001 - retry runner must never leak raw upstream details.
            marked = await self._repository.mark_reconciliation_required(
                job,
                completed_at=_ensure_aware_utc(self._now()),
                error_code=exc.__class__.__name__,
            )
            return Stage1ProvisioningRetryDecision(
                provisioning_state=marked.provisioning_state,
                support_state=marked.support_state,
                payment_state=marked.payment_state,
                retry_job=marked,
                queued_for_retry=False,
                completed=False,
            )

        marked = await self._repository.mark_reconciliation_required(
            job,
            completed_at=_ensure_aware_utc(self._now()),
            error_code="UnsupportedProvisioningOperation",
        )
        return Stage1ProvisioningRetryDecision(
            provisioning_state=marked.provisioning_state,
            support_state=marked.support_state,
            payment_state=marked.payment_state,
            retry_job=marked,
            queued_for_retry=False,
            completed=False,
        )


def _paid_request_from_job(job: Stage1ProvisioningRetryJob) -> Stage1PaidProvisioningRequest:
    payload = job.request_payload
    customer_account_id = _uuid_from_payload(payload, "customer_account_id")
    order_id = _uuid_from_payload(payload, "order_id")
    access_expires_at = _datetime_from_payload(payload, "access_expires_at")
    return Stage1PaidProvisioningRequest(
        customer_account_id=customer_account_id,
        order_id=order_id,
        email=f"cvpn-p-{customer_account_id.hex[:28]}@cyber-vpn.net",
        username=None,
        telegram_id=None,
        plan_code=_optional_str(payload.get("plan_code")),
        plan_duration_days=1,
        paid_at=job.queued_at,
        access_starts_at=job.queued_at,
        access_expires_at=access_expires_at,
        traffic_limit_bytes=_optional_int(payload.get("traffic_limit_bytes")),
        device_limit=_int_from_payload(payload, "device_limit"),
        profile_id=str(payload["profile_id"]),
        existing_remnawave_uuid=_optional_str(payload.get("existing_remnawave_uuid")),
        source_provider=_optional_str(payload.get("source_provider")),
        source_payment_id=None,
    )


def _trial_request_from_job(job: Stage1ProvisioningRetryJob) -> Stage1TrialProvisioningRequest:
    payload = job.request_payload
    customer_account_id = _uuid_from_payload(payload, "customer_account_id")
    return Stage1TrialProvisioningRequest(
        customer_account_id=customer_account_id,
        email=f"cvpn-t-{customer_account_id.hex[:28]}@cyber-vpn.net",
        username=None,
        telegram_id=None,
        trial_expires_at=_datetime_from_payload(payload, "trial_expires_at"),
        profile_id=str(payload["profile_id"]),
        existing_remnawave_uuid=_optional_str(payload.get("existing_remnawave_uuid")),
        traffic_limit_bytes=_int_from_payload(payload, "traffic_limit_bytes"),
        device_limit=_int_from_payload(payload, "device_limit"),
    )


def _uuid_from_payload(payload: Mapping[str, JsonScalar], key: str) -> UUID:
    return UUID(str(payload[key]))


def _datetime_from_payload(payload: Mapping[str, JsonScalar], key: str) -> datetime:
    return _ensure_aware_utc(datetime.fromisoformat(str(payload[key])))


def _int_from_payload(payload: Mapping[str, JsonScalar], key: str) -> int:
    return int(payload[key])


def _optional_int(value: JsonScalar | None) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_str(value: JsonScalar | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _increment(values: dict[str, int], key: str) -> None:
    values[key] = values.get(key, 0) + 1


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
