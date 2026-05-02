from __future__ import annotations

import re
from datetime import UTC, timedelta

from src.domain.entities import (
    ApprovalPolicyRecord,
    BudgetPolicyRecord,
    FailoverEvaluationRecord,
    FailoverGuardrailPolicyRecord,
    FailoverPolicyBundleRecord,
    FleetRequestSubmission,
    OperatorCommandResult,
    RateLimitPolicyRecord,
    utcnow,
)
from src.domain.enums import RequestStatus, RequestType
from src.domain.exceptions import FailoverPolicyNotFoundError, NodePoolNotFoundError
from src.infra.database.repositories import FleetRequestRepository

from .audit_service import AuditTrailService
from .request_service import FleetRequestService


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "default"


def derive_failover_scope_id(*, environment: str, country: str, provider_selector: str | None) -> str:
    return "-".join((_slugify(environment), _slugify(country), _slugify(provider_selector or "auto")))


class FailoverPolicyService:
    def __init__(
        self,
        repository: FleetRequestRepository,
        request_service: FleetRequestService,
        audit_service: AuditTrailService,
    ) -> None:
        self._repository = repository
        self._request_service = request_service
        self._audit_service = audit_service

    async def upsert_policy_bundle(
        self,
        *,
        scope_id: str,
        environment: str,
        country: str,
        provider_selector: str | None,
        monthly_limit: int,
        burst_limit: int,
        current_month_spend: int,
        max_actions_per_window: int,
        window_seconds: int,
        cooldown_seconds: int,
        max_parallel_failovers: int,
        risk_threshold: float,
        budget_approval_threshold: int,
        approval_mode: str,
        require_human_above_threshold: bool,
        confidence_score_threshold: float,
        minimum_independent_signal_sources: int,
        country_emergency_stop: bool,
        node_class_allowlist: tuple[str, ...],
        provider_exclusion_window_seconds: int,
        traffic_canary_required: bool,
        rollback_and_drain_policy: str,
    ) -> FailoverPolicyBundleRecord:
        budget_policy = await self._repository.upsert_budget_policy(
            BudgetPolicyRecord(
                budget_policy_id=f"budget_{scope_id}",
                scope_id=scope_id,
                environment=environment,
                country=country,
                provider_selector=provider_selector,
                monthly_limit=monthly_limit,
                burst_limit=burst_limit,
                current_month_spend=current_month_spend,
            )
        )
        rate_limit_policy = await self._repository.upsert_rate_limit_policy(
            RateLimitPolicyRecord(
                rate_limit_policy_id=f"ratelimit_{scope_id}",
                scope_id=scope_id,
                environment=environment,
                country=country,
                provider_selector=provider_selector,
                max_actions_per_window=max_actions_per_window,
                window_seconds=window_seconds,
                cooldown_seconds=cooldown_seconds,
                max_parallel_failovers=max_parallel_failovers,
            )
        )
        approval_policy = await self._repository.upsert_approval_policy(
            ApprovalPolicyRecord(
                approval_policy_id=f"approval_{scope_id}",
                scope_id=scope_id,
                environment=environment,
                country=country,
                provider_selector=provider_selector,
                risk_threshold=risk_threshold,
                budget_approval_threshold=budget_approval_threshold,
                approval_mode=approval_mode,
                require_human_above_threshold=require_human_above_threshold,
            )
        )
        guardrail_policy = await self._repository.upsert_failover_guardrail_policy(
            FailoverGuardrailPolicyRecord(
                failover_policy_id=f"failover_{scope_id}",
                scope_id=scope_id,
                environment=environment,
                country=country,
                provider_selector=provider_selector,
                confidence_score_threshold=confidence_score_threshold,
                minimum_independent_signal_sources=minimum_independent_signal_sources,
                country_emergency_stop=country_emergency_stop,
                node_class_allowlist=node_class_allowlist,
                provider_exclusion_window_seconds=provider_exclusion_window_seconds,
                traffic_canary_required=traffic_canary_required,
                rollback_and_drain_policy=rollback_and_drain_policy,
            )
        )
        return FailoverPolicyBundleRecord(
            scope_id=scope_id,
            budget_policy=budget_policy,
            rate_limit_policy=rate_limit_policy,
            approval_policy=approval_policy,
            guardrail_policy=guardrail_policy,
        )

    async def get_policy_bundle(self, scope_id: str) -> FailoverPolicyBundleRecord:
        bundle = await self._repository.get_failover_policy_bundle(scope_id)
        if bundle is None:
            raise FailoverPolicyNotFoundError(f"Failover policy scope not found: {scope_id}")
        return bundle

    async def submit_failover(
        self,
        *,
        requested_by: str,
        idempotency_key: str,
        environment: str,
        country: str,
        node_class: str,
        provider_selector: str | None,
        region_selector: str | None,
        requested_capacity_delta: int,
        approval_mode: str,
        signal_group_id: str,
        confidence_score: float,
        independent_signal_sources: int,
        budget_impact: int,
        risk_score: float,
        reason_code: str,
        node_pool_id: str | None,
        target_node_id: str | None,
    ) -> OperatorCommandResult:
        scope_id = derive_failover_scope_id(
            environment=environment,
            country=country,
            provider_selector=provider_selector,
        )
        bundle = await self.get_policy_bundle(scope_id)
        if node_pool_id is not None:
            pool = await self._repository.get_node_pool(node_pool_id)
            if pool is None:
                raise NodePoolNotFoundError(f"Node pool not found: {node_pool_id}")

        existing_request = await self._repository.get_request_by_idempotency_key(idempotency_key)
        if existing_request is not None:
            operation_runs = await self._repository.get_operation_runs_for_request(existing_request.request_id)
            operation_run = operation_runs[-1]
            return OperatorCommandResult(
                command_name="node-failover",
                request=existing_request,
                operation_run=operation_run,
                policy_evaluation=FailoverEvaluationRecord(
                    scope_id=scope_id,
                    decision_status=existing_request.status,
                    confidence_score=existing_request.confidence_score or confidence_score,
                    independent_signal_sources=independent_signal_sources,
                    risk_score=risk_score,
                    budget_impact=budget_impact,
                    requires_human_approval=existing_request.status is RequestStatus.AWAITING_APPROVAL,
                    blocked_reasons=("idempotent_replay",),
                    canary_required=bundle.guardrail_policy.traffic_canary_required,
                ),
            )

        evaluation = await self._evaluate_failover(
            bundle=bundle,
            environment=environment,
            country=country,
            provider_selector=provider_selector,
            node_class=node_class,
            confidence_score=confidence_score,
            independent_signal_sources=independent_signal_sources,
            budget_impact=budget_impact,
            risk_score=risk_score,
            approval_mode=approval_mode,
        )

        request, operation_run = await self._request_service.submit(
            FleetRequestSubmission(
                request_type=RequestType.FAILOVER,
                requested_by=requested_by,
                idempotency_key=idempotency_key,
                environment=environment,
                country=country,
                provider_selector=provider_selector,
                region_selector=region_selector,
                node_class=node_class,
                node_pool_id=node_pool_id,
                target_node_id=target_node_id,
                reason_code=reason_code,
                approval_mode=approval_mode,
                requested_capacity_delta=requested_capacity_delta,
                signal_group_id=signal_group_id,
                confidence_score=confidence_score,
            ),
            initial_status=evaluation.decision_status,
        )
        await self._audit_service.record_request_event(
            event_type="fleet.failover.policy_evaluated",
            actor=requested_by,
            request=request,
            operation_run=operation_run,
            payload={
                "scope_id": scope_id,
                "signal_group_id": signal_group_id,
                "confidence_score": confidence_score,
                "independent_signal_sources": independent_signal_sources,
                "budget_impact": budget_impact,
                "risk_score": risk_score,
                "blocked_reasons": list(evaluation.blocked_reasons),
                "cooldown_remaining_seconds": evaluation.cooldown_remaining_seconds,
                "actions_in_window": evaluation.actions_in_window,
                "active_parallel_failovers": evaluation.active_parallel_failovers,
                "requires_human_approval": evaluation.requires_human_approval,
                "canary_required": evaluation.canary_required,
            },
        )
        return OperatorCommandResult(
            command_name="node-failover",
            request=request,
            operation_run=operation_run,
            policy_evaluation=evaluation,
        )

    async def _evaluate_failover(
        self,
        *,
        bundle: FailoverPolicyBundleRecord,
        environment: str,
        country: str,
        provider_selector: str | None,
        node_class: str,
        confidence_score: float,
        independent_signal_sources: int,
        budget_impact: int,
        risk_score: float,
        approval_mode: str,
    ) -> FailoverEvaluationRecord:
        now = utcnow()
        rate_policy = bundle.rate_limit_policy
        approval_policy = bundle.approval_policy
        budget_policy = bundle.budget_policy
        guardrail_policy = bundle.guardrail_policy

        blocked_reasons: list[str] = []
        cooldown_remaining_seconds = 0

        if guardrail_policy.country_emergency_stop:
            blocked_reasons.append("country_emergency_stop")
        if guardrail_policy.node_class_allowlist and node_class not in guardrail_policy.node_class_allowlist:
            blocked_reasons.append("node_class_not_allowed")
        if confidence_score < guardrail_policy.confidence_score_threshold:
            blocked_reasons.append("confidence_below_threshold")
        if independent_signal_sources < guardrail_policy.minimum_independent_signal_sources:
            blocked_reasons.append("insufficient_signal_sources")
        if budget_policy.monthly_limit > 0 and budget_policy.current_month_spend + budget_impact > budget_policy.monthly_limit:
            blocked_reasons.append("monthly_budget_exceeded")
        if budget_policy.burst_limit > 0 and budget_impact > budget_policy.burst_limit:
            blocked_reasons.append("burst_budget_exceeded")

        window_start = now - timedelta(seconds=max(rate_policy.window_seconds, 0))
        actions_in_window = await self._repository.count_failover_requests_since(
            environment=environment,
            country=country,
            provider_selector=provider_selector,
            since=window_start,
            include_statuses=(
                RequestStatus.ACCEPTED,
                RequestStatus.AWAITING_APPROVAL,
                RequestStatus.RUNNING,
                RequestStatus.COMPLETED,
            ),
        )
        if rate_policy.max_actions_per_window > 0 and actions_in_window >= rate_policy.max_actions_per_window:
            blocked_reasons.append("rate_limit_window_exceeded")

        active_parallel_failovers = await self._repository.count_active_failover_requests(
            environment=environment,
            country=country,
            provider_selector=provider_selector,
        )
        if rate_policy.max_parallel_failovers > 0 and active_parallel_failovers >= rate_policy.max_parallel_failovers:
            blocked_reasons.append("max_parallel_failovers_exceeded")

        latest_request = await self._repository.get_latest_failover_request(
            environment=environment,
            country=country,
            provider_selector=provider_selector,
            include_statuses=(
                RequestStatus.ACCEPTED,
                RequestStatus.AWAITING_APPROVAL,
                RequestStatus.RUNNING,
                RequestStatus.COMPLETED,
            ),
        )
        if latest_request is not None and rate_policy.cooldown_seconds > 0:
            latest_created_at = latest_request.created_at
            if latest_created_at.tzinfo is None:
                latest_created_at = latest_created_at.replace(tzinfo=UTC)
            elapsed = (now - latest_created_at).total_seconds()
            if elapsed < rate_policy.cooldown_seconds:
                cooldown_remaining_seconds = max(int(rate_policy.cooldown_seconds - elapsed), 0)
                blocked_reasons.append("cooldown_active")

        requires_human_approval = False
        if approval_policy.require_human_above_threshold:
            if risk_score >= approval_policy.risk_threshold:
                requires_human_approval = True
            if approval_policy.budget_approval_threshold > 0 and budget_impact >= approval_policy.budget_approval_threshold:
                requires_human_approval = True
        if approval_mode == "manual" or approval_policy.approval_mode == "manual":
            requires_human_approval = True

        if blocked_reasons:
            decision_status = RequestStatus.BLOCKED_POLICY
        elif requires_human_approval:
            decision_status = RequestStatus.AWAITING_APPROVAL
        else:
            decision_status = RequestStatus.ACCEPTED

        return FailoverEvaluationRecord(
            scope_id=bundle.scope_id,
            decision_status=decision_status,
            confidence_score=confidence_score,
            independent_signal_sources=independent_signal_sources,
            risk_score=risk_score,
            budget_impact=budget_impact,
            requires_human_approval=requires_human_approval,
            blocked_reasons=tuple(blocked_reasons),
            cooldown_remaining_seconds=cooldown_remaining_seconds,
            actions_in_window=actions_in_window,
            active_parallel_failovers=active_parallel_failovers,
            canary_required=guardrail_policy.traffic_canary_required,
        )
