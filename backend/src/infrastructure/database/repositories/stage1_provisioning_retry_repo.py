"""Durable repository for Stage 1 provisioning retry jobs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.subscriptions.stage1_provisioning_retry import (
    STAGE1_PROVISIONING_RETRY_QUEUE_NAME,
    Stage1ProvisioningRetryJob,
    Stage1ProvisioningRetryJobState,
    Stage1ProvisioningRetryOperation,
    Stage1ProvisioningRetryReason,
)
from src.infrastructure.database.models.stage1_provisioning_retry_model import Stage1ProvisioningRetryJobModel
from src.presentation.api.shared.stage1_contract import (
    JsonScalar,
    Stage1ErrorCode,
    Stage1PaymentState,
    Stage1ProvisioningState,
    Stage1SupportState,
)

ACTIVE_RETRY_STATES = (
    Stage1ProvisioningRetryJobState.QUEUED.value,
    Stage1ProvisioningRetryJobState.RETRYING.value,
)
TERMINAL_RETRY_STATES = (
    Stage1ProvisioningRetryJobState.SUCCEEDED.value,
    Stage1ProvisioningRetryJobState.DEAD_LETTER.value,
)


def build_claim_due_jobs_statement(*, now: datetime, limit: int) -> Select[tuple[Stage1ProvisioningRetryJobModel]]:
    """Build the PostgreSQL claim query with row locks and SKIP LOCKED."""

    return (
        select(Stage1ProvisioningRetryJobModel)
        .where(
            Stage1ProvisioningRetryJobModel.queue_name == STAGE1_PROVISIONING_RETRY_QUEUE_NAME,
            Stage1ProvisioningRetryJobModel.state.in_(ACTIVE_RETRY_STATES),
            Stage1ProvisioningRetryJobModel.next_attempt_at <= _ensure_aware_utc(now),
        )
        .order_by(
            Stage1ProvisioningRetryJobModel.next_attempt_at.asc(), Stage1ProvisioningRetryJobModel.queued_at.asc()
        )
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


class Stage1ProvisioningRetryJobRepository:
    """PostgreSQL-backed retry queue implementation used by backend and workers."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_retry_job(self, job: Stage1ProvisioningRetryJob) -> Stage1ProvisioningRetryJob:
        """Persist a retry job idempotently by ``operation + correlation_id``."""

        existing = await self.get_by_operation_correlation(
            operation=job.operation,
            correlation_id=job.correlation_id,
            lock=True,
        )
        if existing is not None and existing.id != job.job_id and existing.state in ACTIVE_RETRY_STATES:
            return self._to_job(existing)

        if existing is None:
            existing = self._from_job(job)
            self._session.add(existing)
        else:
            self._apply_job(existing, job)

        await self._session.flush()
        return self._to_job(existing)

    async def get_by_operation_correlation(
        self,
        *,
        operation: Stage1ProvisioningRetryOperation,
        correlation_id: str,
        lock: bool = False,
    ) -> Stage1ProvisioningRetryJobModel | None:
        stmt = select(Stage1ProvisioningRetryJobModel).where(
            Stage1ProvisioningRetryJobModel.operation == operation.value,
            Stage1ProvisioningRetryJobModel.correlation_id == correlation_id,
        )
        if lock:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def claim_due_jobs(
        self,
        *,
        now: datetime,
        limit: int,
        worker_id: str,
    ) -> list[Stage1ProvisioningRetryJob]:
        """Claim due jobs with ``FOR UPDATE SKIP LOCKED`` to avoid double-run concurrency."""

        safe_limit = max(1, min(limit, 100))
        claimed_at = _ensure_aware_utc(now)
        result = await self._session.execute(build_claim_due_jobs_statement(now=claimed_at, limit=safe_limit))
        models = list(result.scalars().all())
        for model in models:
            model.state = Stage1ProvisioningRetryJobState.RETRYING.value
            model.locked_at = claimed_at
            model.locked_by = worker_id[:120]
            model.updated_at = claimed_at
            self._session.add(model)
        await self._session.flush()
        return [self._to_job(model) for model in models]

    async def metrics_snapshot(self, *, now: datetime) -> dict[str, JsonScalar | dict[str, JsonScalar]]:
        """Return low-cardinality queue metrics without job payloads."""

        counts_result = await self._session.execute(
            select(Stage1ProvisioningRetryJobModel.state, func.count())
            .where(Stage1ProvisioningRetryJobModel.queue_name == STAGE1_PROVISIONING_RETRY_QUEUE_NAME)
            .group_by(Stage1ProvisioningRetryJobModel.state)
        )
        counts = {state: count for state, count in counts_result.all()}
        oldest_result = await self._session.execute(
            select(func.min(Stage1ProvisioningRetryJobModel.queued_at)).where(
                Stage1ProvisioningRetryJobModel.queue_name == STAGE1_PROVISIONING_RETRY_QUEUE_NAME,
                Stage1ProvisioningRetryJobModel.state.in_(ACTIVE_RETRY_STATES),
            )
        )
        oldest = oldest_result.scalar_one_or_none()
        max_age_seconds = 0
        if isinstance(oldest, datetime):
            max_age_seconds = max(0, int((_ensure_aware_utc(now) - _ensure_aware_utc(oldest)).total_seconds()))
        return {
            "counts_by_state": {
                "queued": int(counts.get(Stage1ProvisioningRetryJobState.QUEUED.value, 0)),
                "retrying": int(counts.get(Stage1ProvisioningRetryJobState.RETRYING.value, 0)),
                "dead_letter": int(counts.get(Stage1ProvisioningRetryJobState.DEAD_LETTER.value, 0)),
                "succeeded": int(counts.get(Stage1ProvisioningRetryJobState.SUCCEEDED.value, 0)),
            },
            "max_job_age_seconds": max_age_seconds,
        }

    @staticmethod
    def _from_job(job: Stage1ProvisioningRetryJob) -> Stage1ProvisioningRetryJobModel:
        return Stage1ProvisioningRetryJobModel(
            id=job.job_id,
            queue_name=job.queue_name,
            operation=job.operation.value,
            correlation_id=job.correlation_id,
            customer_account_id=job.customer_account_id,
            state=job.state.value,
            reason=job.reason.value,
            error_code=job.error_code.value,
            provisioning_state=job.provisioning_state.value,
            payment_state=job.payment_state.value if job.payment_state else None,
            support_state=job.support_state.value,
            request_payload=dict(job.request_payload),
            result_payload=dict(job.result_payload),
            attempt_count=job.attempt_count,
            max_attempts=job.max_attempts,
            queued_at=_ensure_aware_utc(job.queued_at),
            next_attempt_at=_ensure_aware_utc(job.next_attempt_at),
            completed_at=_ensure_aware_utc(job.completed_at) if job.completed_at else None,
            last_error_code=job.last_error_code,
            last_error_message=job.last_error_message,
        )

    @staticmethod
    def _apply_job(model: Stage1ProvisioningRetryJobModel, job: Stage1ProvisioningRetryJob) -> None:
        model.queue_name = job.queue_name
        model.customer_account_id = job.customer_account_id
        model.state = job.state.value
        model.reason = job.reason.value
        model.error_code = job.error_code.value
        model.provisioning_state = job.provisioning_state.value
        model.payment_state = job.payment_state.value if job.payment_state else None
        model.support_state = job.support_state.value
        model.request_payload = dict(job.request_payload)
        model.result_payload = dict(job.result_payload)
        model.attempt_count = job.attempt_count
        model.max_attempts = job.max_attempts
        model.queued_at = _ensure_aware_utc(job.queued_at)
        model.next_attempt_at = _ensure_aware_utc(job.next_attempt_at)
        model.completed_at = _ensure_aware_utc(job.completed_at) if job.completed_at else None
        model.last_error_code = job.last_error_code
        model.last_error_message = job.last_error_message
        model.locked_at = None
        model.locked_by = None
        model.updated_at = datetime.now(UTC)

    @staticmethod
    def _to_job(model: Stage1ProvisioningRetryJobModel) -> Stage1ProvisioningRetryJob:
        return Stage1ProvisioningRetryJob(
            job_id=model.id,
            queue_name=model.queue_name,
            operation=Stage1ProvisioningRetryOperation(model.operation),
            customer_account_id=model.customer_account_id,
            correlation_id=model.correlation_id,
            request_payload=_json_scalar_dict(model.request_payload),
            queued_at=_ensure_aware_utc(model.queued_at),
            next_attempt_at=_ensure_aware_utc(model.next_attempt_at),
            attempt_count=model.attempt_count,
            max_attempts=model.max_attempts,
            reason=Stage1ProvisioningRetryReason(model.reason),
            error_code=Stage1ErrorCode(model.error_code),
            provisioning_state=Stage1ProvisioningState(model.provisioning_state),
            support_state=Stage1SupportState(model.support_state),
            state=Stage1ProvisioningRetryJobState(model.state),
            payment_state=Stage1PaymentState(model.payment_state) if model.payment_state else None,
            last_error_code=model.last_error_code,
            last_error_message=model.last_error_message,
            completed_at=_ensure_aware_utc(model.completed_at) if model.completed_at else None,
            result_payload=_json_scalar_dict(model.result_payload),
        )

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
            completed_at=_ensure_aware_utc(completed_at),
            last_error_code=error_code,
            last_error_message="Remnawave provisioning retry requires reconciliation; details redacted.",
        )
        return await self.save_retry_job(updated)


def _json_scalar_dict(value: Mapping[str, Any] | None) -> dict[str, JsonScalar]:
    safe: dict[str, JsonScalar] = {}
    for key, item in dict(value or {}).items():
        if isinstance(item, str | int | float | bool) or item is None:
            safe[str(key)] = item
    return safe


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
