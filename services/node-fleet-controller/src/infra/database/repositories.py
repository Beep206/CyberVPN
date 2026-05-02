from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import (
    ApprovalPolicyRecord,
    AuditEntryRecord,
    BudgetPolicyRecord,
    HealthSignalRecord,
    BootstrapTokenRecord,
    FailoverGuardrailPolicyRecord,
    FailoverPolicyBundleRecord,
    FleetRequestRecord,
    NodePoolRecord,
    NodeObservedStateRecord,
    NodeCertificateRecord,
    NodeRecord,
    OperationRunRecord,
    OperationStepRecord,
    RateLimitPolicyRecord,
    RuntimeReadinessRecord,
    SyntheticCheckRecord,
    TrafficEligibilityRecord,
)
from src.domain.enums import (
    AdapterAckState,
    BootstrapState,
    CertificateState,
    HealthState,
    EnrollmentStatus,
    LifecycleState,
    OperationStatus,
    OperationStepStatus,
    ProviderResourceState,
    RequestStatus,
    RequestType,
    SignalSeverity,
    SyntheticStatus,
    TrafficEligibilityState,
)
from src.infra.database.models import (
    ApprovalPolicyModel,
    AuditEntryModel,
    BudgetPolicyModel,
    BootstrapTokenModel,
    FailoverGuardrailPolicyModel,
    FleetRequestModel,
    HealthSignalModel,
    NodeObservedStateModel,
    NodeCertificateModel,
    NodeModel,
    NodePoolModel,
    OperationRunModel,
    OperationStepModel,
    RateLimitPolicyModel,
    RuntimeReadinessModel,
    SyntheticCheckModel,
    TrafficEligibilityModel,
)


class FleetRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_request(
        self,
        request: FleetRequestRecord,
        operation_run: OperationRunRecord,
    ) -> tuple[FleetRequestRecord, OperationRunRecord]:
        request_model = FleetRequestModel(
            request_id=request.request_id,
            request_type=request.request_type.value,
            status=request.status.value,
            requested_by=request.requested_by,
            idempotency_key=request.idempotency_key,
            environment=request.environment,
            country=request.country,
            provider_selector=request.provider_selector,
            region_selector=request.region_selector,
            node_class=request.node_class,
            node_pool_id=request.node_pool_id,
            target_node_id=request.target_node_id,
            reason_code=request.reason_code,
            approval_mode=request.approval_mode,
            requested_capacity_delta=request.requested_capacity_delta,
            correlation_id=request.correlation_id,
            signal_group_id=request.signal_group_id,
            confidence_score=request.confidence_score,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )
        operation_model = OperationRunModel(
            operation_run_id=operation_run.operation_run_id,
            request_id=operation_run.request_id,
            operation_name=operation_run.operation_name,
            status=operation_run.status.value,
            current_step=operation_run.current_step,
            started_at=operation_run.started_at,
            finished_at=operation_run.finished_at,
        )
        self._session.add(request_model)
        self._session.add(operation_model)
        await self._session.flush()
        return request, operation_run

    async def get_request(self, request_id: str) -> FleetRequestRecord | None:
        result = await self._session.execute(
            select(FleetRequestModel).where(FleetRequestModel.request_id == request_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._request_from_model(model)

    async def get_request_by_idempotency_key(self, idempotency_key: str) -> FleetRequestRecord | None:
        result = await self._session.execute(
            select(FleetRequestModel).where(FleetRequestModel.idempotency_key == idempotency_key)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._request_from_model(model)

    async def get_operation_run(self, operation_run_id: str) -> OperationRunRecord | None:
        result = await self._session.execute(
            select(OperationRunModel).where(OperationRunModel.operation_run_id == operation_run_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._operation_from_model(model)

    async def get_operation_runs_for_request(self, request_id: str) -> list[OperationRunRecord]:
        result = await self._session.execute(
            select(OperationRunModel)
            .where(OperationRunModel.request_id == request_id)
            .order_by(OperationRunModel.started_at.asc())
        )
        return [self._operation_from_model(model) for model in result.scalars().all()]

    async def append_operation_step(self, step: OperationStepRecord) -> OperationStepRecord:
        model = OperationStepModel(
            operation_step_id=step.operation_step_id,
            operation_run_id=step.operation_run_id,
            step_name=step.step_name,
            status=step.status.value,
            attempt=step.attempt,
            error_code=step.error_code,
            artifact_ref=step.artifact_ref,
            created_at=step.created_at,
            updated_at=step.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return step

    async def list_operation_steps(self, operation_run_id: str) -> list[OperationStepRecord]:
        result = await self._session.execute(
            select(OperationStepModel)
            .where(OperationStepModel.operation_run_id == operation_run_id)
            .order_by(OperationStepModel.created_at.asc(), OperationStepModel.operation_step_id.asc())
        )
        return [self._operation_step_from_model(model) for model in result.scalars().all()]

    async def update_request_status(self, request_id: str, status: RequestStatus) -> FleetRequestRecord | None:
        result = await self._session.execute(select(FleetRequestModel).where(FleetRequestModel.request_id == request_id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.status = status.value
        await self._session.flush()
        return self._request_from_model(model)

    async def update_operation_run(
        self,
        operation_run_id: str,
        *,
        status: OperationStatus | None = None,
        current_step: str | None = None,
        finished_at=None,
    ) -> OperationRunRecord | None:
        result = await self._session.execute(
            select(OperationRunModel).where(OperationRunModel.operation_run_id == operation_run_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        if status is not None:
            model.status = status.value
        model.current_step = current_step
        model.finished_at = finished_at
        await self._session.flush()
        return self._operation_from_model(model)

    async def list_pending_requests(self, *, limit: int) -> list[FleetRequestRecord]:
        result = await self._session.execute(
            select(FleetRequestModel)
            .where(
                FleetRequestModel.status.in_(
                    [
                        RequestStatus.ACCEPTED.value,
                        RequestStatus.RUNNING.value,
                        RequestStatus.AWAITING_APPROVAL.value,
                    ]
                )
            )
            .order_by(FleetRequestModel.created_at.asc())
            .limit(limit)
        )
        return [self._request_from_model(model) for model in result.scalars().all()]

    async def append_audit_entry(self, entry: AuditEntryRecord) -> AuditEntryRecord:
        model = AuditEntryModel(
            audit_entry_id=entry.audit_entry_id,
            event_type=entry.event_type,
            actor=entry.actor,
            request_id=entry.request_id,
            operation_run_id=entry.operation_run_id,
            payload=entry.payload,
            created_at=entry.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return entry

    async def list_audit_entries(self, *, request_id: str) -> list[AuditEntryRecord]:
        result = await self._session.execute(
            select(AuditEntryModel)
            .where(AuditEntryModel.request_id == request_id)
            .order_by(AuditEntryModel.created_at.asc())
        )
        return [self._audit_from_model(model) for model in result.scalars().all()]

    async def create_node(self, node: NodeRecord) -> NodeRecord:
        model = NodeModel(
            node_id=node.node_id,
            environment=node.environment,
            role=node.role,
            country=node.country,
            provider=node.provider,
            region=node.region,
            node_class=node.node_class,
            current_lifecycle_state=node.current_lifecycle_state.value,
            enrollment_status=node.enrollment_status.value,
            bootstrap_state=node.bootstrap_state.value,
            certificate_state=node.certificate_state.value,
            provider_resource_state=node.provider_resource_state.value,
            request_id=node.request_id,
            operation_run_id=node.operation_run_id,
            created_at=node.created_at,
            updated_at=node.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return node

    async def get_node(self, node_id: str) -> NodeRecord | None:
        result = await self._session.execute(select(NodeModel).where(NodeModel.node_id == node_id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._node_from_model(model)

    async def get_node_pool(self, node_pool_id: str) -> NodePoolRecord | None:
        result = await self._session.execute(select(NodePoolModel).where(NodePoolModel.node_pool_id == node_pool_id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._node_pool_from_model(model)

    async def upsert_node_pool(self, pool: NodePoolRecord) -> NodePoolRecord:
        existing = await self._session.execute(
            select(NodePoolModel).where(NodePoolModel.node_pool_id == pool.node_pool_id)
        )
        model = existing.scalar_one_or_none()
        if model is None:
            model = NodePoolModel(
                node_pool_id=pool.node_pool_id,
                environment=pool.environment,
                country=pool.country,
                role=pool.role,
                node_class=pool.node_class,
                provider_selector=pool.provider_selector,
                region_selector=pool.region_selector,
                desired_capacity=pool.desired_capacity,
                current_capacity=pool.current_capacity,
                created_at=pool.created_at,
                updated_at=pool.updated_at,
            )
            self._session.add(model)
            await self._session.flush()
            return pool
        model.environment = pool.environment
        model.country = pool.country
        model.role = pool.role
        model.node_class = pool.node_class
        model.provider_selector = pool.provider_selector
        model.region_selector = pool.region_selector
        model.desired_capacity = pool.desired_capacity
        model.current_capacity = pool.current_capacity
        await self._session.flush()
        return self._node_pool_from_model(model)

    async def list_node_pools(self) -> list[NodePoolRecord]:
        result = await self._session.execute(select(NodePoolModel).order_by(NodePoolModel.node_pool_id.asc()))
        return [self._node_pool_from_model(model) for model in result.scalars().all()]

    async def get_budget_policy(self, scope_id: str) -> BudgetPolicyRecord | None:
        result = await self._session.execute(select(BudgetPolicyModel).where(BudgetPolicyModel.scope_id == scope_id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._budget_policy_from_model(model)

    async def upsert_budget_policy(self, policy: BudgetPolicyRecord) -> BudgetPolicyRecord:
        existing = await self._session.execute(
            select(BudgetPolicyModel).where(BudgetPolicyModel.scope_id == policy.scope_id)
        )
        model = existing.scalar_one_or_none()
        if model is None:
            model = BudgetPolicyModel(
                budget_policy_id=policy.budget_policy_id,
                scope_id=policy.scope_id,
                environment=policy.environment,
                country=policy.country,
                provider_selector=policy.provider_selector,
                monthly_limit=policy.monthly_limit,
                burst_limit=policy.burst_limit,
                current_month_spend=policy.current_month_spend,
                created_at=policy.created_at,
                updated_at=policy.updated_at,
            )
            self._session.add(model)
            await self._session.flush()
            return policy
        model.environment = policy.environment
        model.country = policy.country
        model.provider_selector = policy.provider_selector
        model.monthly_limit = policy.monthly_limit
        model.burst_limit = policy.burst_limit
        model.current_month_spend = policy.current_month_spend
        await self._session.flush()
        return self._budget_policy_from_model(model)

    async def get_rate_limit_policy(self, scope_id: str) -> RateLimitPolicyRecord | None:
        result = await self._session.execute(
            select(RateLimitPolicyModel).where(RateLimitPolicyModel.scope_id == scope_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._rate_limit_policy_from_model(model)

    async def upsert_rate_limit_policy(self, policy: RateLimitPolicyRecord) -> RateLimitPolicyRecord:
        existing = await self._session.execute(
            select(RateLimitPolicyModel).where(RateLimitPolicyModel.scope_id == policy.scope_id)
        )
        model = existing.scalar_one_or_none()
        if model is None:
            model = RateLimitPolicyModel(
                rate_limit_policy_id=policy.rate_limit_policy_id,
                scope_id=policy.scope_id,
                environment=policy.environment,
                country=policy.country,
                provider_selector=policy.provider_selector,
                max_actions_per_window=policy.max_actions_per_window,
                window_seconds=policy.window_seconds,
                cooldown_seconds=policy.cooldown_seconds,
                max_parallel_failovers=policy.max_parallel_failovers,
                created_at=policy.created_at,
                updated_at=policy.updated_at,
            )
            self._session.add(model)
            await self._session.flush()
            return policy
        model.environment = policy.environment
        model.country = policy.country
        model.provider_selector = policy.provider_selector
        model.max_actions_per_window = policy.max_actions_per_window
        model.window_seconds = policy.window_seconds
        model.cooldown_seconds = policy.cooldown_seconds
        model.max_parallel_failovers = policy.max_parallel_failovers
        await self._session.flush()
        return self._rate_limit_policy_from_model(model)

    async def get_approval_policy(self, scope_id: str) -> ApprovalPolicyRecord | None:
        result = await self._session.execute(
            select(ApprovalPolicyModel).where(ApprovalPolicyModel.scope_id == scope_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._approval_policy_from_model(model)

    async def upsert_approval_policy(self, policy: ApprovalPolicyRecord) -> ApprovalPolicyRecord:
        existing = await self._session.execute(
            select(ApprovalPolicyModel).where(ApprovalPolicyModel.scope_id == policy.scope_id)
        )
        model = existing.scalar_one_or_none()
        if model is None:
            model = ApprovalPolicyModel(
                approval_policy_id=policy.approval_policy_id,
                scope_id=policy.scope_id,
                environment=policy.environment,
                country=policy.country,
                provider_selector=policy.provider_selector,
                risk_threshold=policy.risk_threshold,
                budget_approval_threshold=policy.budget_approval_threshold,
                approval_mode=policy.approval_mode,
                require_human_above_threshold=policy.require_human_above_threshold,
                created_at=policy.created_at,
                updated_at=policy.updated_at,
            )
            self._session.add(model)
            await self._session.flush()
            return policy
        model.environment = policy.environment
        model.country = policy.country
        model.provider_selector = policy.provider_selector
        model.risk_threshold = policy.risk_threshold
        model.budget_approval_threshold = policy.budget_approval_threshold
        model.approval_mode = policy.approval_mode
        model.require_human_above_threshold = policy.require_human_above_threshold
        await self._session.flush()
        return self._approval_policy_from_model(model)

    async def get_failover_guardrail_policy(self, scope_id: str) -> FailoverGuardrailPolicyRecord | None:
        result = await self._session.execute(
            select(FailoverGuardrailPolicyModel).where(FailoverGuardrailPolicyModel.scope_id == scope_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._failover_guardrail_policy_from_model(model)

    async def upsert_failover_guardrail_policy(
        self,
        policy: FailoverGuardrailPolicyRecord,
    ) -> FailoverGuardrailPolicyRecord:
        existing = await self._session.execute(
            select(FailoverGuardrailPolicyModel).where(FailoverGuardrailPolicyModel.scope_id == policy.scope_id)
        )
        model = existing.scalar_one_or_none()
        if model is None:
            model = FailoverGuardrailPolicyModel(
                failover_policy_id=policy.failover_policy_id,
                scope_id=policy.scope_id,
                environment=policy.environment,
                country=policy.country,
                provider_selector=policy.provider_selector,
                confidence_score_threshold=policy.confidence_score_threshold,
                minimum_independent_signal_sources=policy.minimum_independent_signal_sources,
                country_emergency_stop=policy.country_emergency_stop,
                node_class_allowlist=list(policy.node_class_allowlist),
                provider_exclusion_window_seconds=policy.provider_exclusion_window_seconds,
                traffic_canary_required=policy.traffic_canary_required,
                rollback_and_drain_policy=policy.rollback_and_drain_policy,
                created_at=policy.created_at,
                updated_at=policy.updated_at,
            )
            self._session.add(model)
            await self._session.flush()
            return policy
        model.environment = policy.environment
        model.country = policy.country
        model.provider_selector = policy.provider_selector
        model.confidence_score_threshold = policy.confidence_score_threshold
        model.minimum_independent_signal_sources = policy.minimum_independent_signal_sources
        model.country_emergency_stop = policy.country_emergency_stop
        model.node_class_allowlist = list(policy.node_class_allowlist)
        model.provider_exclusion_window_seconds = policy.provider_exclusion_window_seconds
        model.traffic_canary_required = policy.traffic_canary_required
        model.rollback_and_drain_policy = policy.rollback_and_drain_policy
        await self._session.flush()
        return self._failover_guardrail_policy_from_model(model)

    async def get_failover_policy_bundle(self, scope_id: str) -> FailoverPolicyBundleRecord | None:
        budget_policy = await self.get_budget_policy(scope_id)
        rate_limit_policy = await self.get_rate_limit_policy(scope_id)
        approval_policy = await self.get_approval_policy(scope_id)
        guardrail_policy = await self.get_failover_guardrail_policy(scope_id)
        if any(item is None for item in (budget_policy, rate_limit_policy, approval_policy, guardrail_policy)):
            return None
        return FailoverPolicyBundleRecord(
            scope_id=scope_id,
            budget_policy=budget_policy,
            rate_limit_policy=rate_limit_policy,
            approval_policy=approval_policy,
            guardrail_policy=guardrail_policy,
        )

    async def upsert_node(self, node: NodeRecord) -> NodeRecord:
        existing = await self._session.execute(select(NodeModel).where(NodeModel.node_id == node.node_id))
        model = existing.scalar_one_or_none()
        if model is None:
            return await self.create_node(node)
        model.environment = node.environment
        model.role = node.role
        model.country = node.country
        model.provider = node.provider
        model.region = node.region
        model.node_class = node.node_class
        model.current_lifecycle_state = node.current_lifecycle_state.value
        model.enrollment_status = node.enrollment_status.value
        model.bootstrap_state = node.bootstrap_state.value
        model.certificate_state = node.certificate_state.value
        model.provider_resource_state = node.provider_resource_state.value
        model.request_id = node.request_id
        model.operation_run_id = node.operation_run_id
        await self._session.flush()
        return self._node_from_model(model)

    async def list_nodes_for_request(self, request_id: str) -> list[NodeRecord]:
        result = await self._session.execute(
            select(NodeModel).where(NodeModel.request_id == request_id).order_by(NodeModel.created_at.asc())
        )
        return [self._node_from_model(model) for model in result.scalars().all()]

    async def create_bootstrap_token(self, token: BootstrapTokenRecord) -> BootstrapTokenRecord:
        model = BootstrapTokenModel(
            token_id=token.token_id,
            node_id=token.node_id,
            operation_run_id=token.operation_run_id,
            wrapped_ref=token.wrapped_ref,
            role_name=token.role_name,
            wrap_ttl=token.wrap_ttl,
            expires_at=token.expires_at,
            consumed_at=token.consumed_at,
            created_at=token.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return token

    async def mark_bootstrap_token_consumed(self, token_id: str, *, consumed_at) -> BootstrapTokenRecord | None:
        result = await self._session.execute(select(BootstrapTokenModel).where(BootstrapTokenModel.token_id == token_id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.consumed_at = consumed_at
        await self._session.flush()
        return self._bootstrap_token_from_model(model)

    async def list_bootstrap_tokens(self, node_id: str) -> list[BootstrapTokenRecord]:
        result = await self._session.execute(
            select(BootstrapTokenModel)
            .where(BootstrapTokenModel.node_id == node_id)
            .order_by(BootstrapTokenModel.created_at.asc())
        )
        return [self._bootstrap_token_from_model(model) for model in result.scalars().all()]

    async def create_certificate(self, certificate: NodeCertificateRecord) -> NodeCertificateRecord:
        model = NodeCertificateModel(
            certificate_id=certificate.certificate_id,
            node_id=certificate.node_id,
            role_name=certificate.role_name,
            serial=certificate.serial,
            common_name=certificate.common_name,
            state=certificate.state.value,
            issued_at=certificate.issued_at,
            expires_at=certificate.expires_at,
            revoked_at=certificate.revoked_at,
        )
        self._session.add(model)
        await self._session.flush()
        return certificate

    async def revoke_certificate(self, certificate_id: str, *, revoked_at) -> NodeCertificateRecord | None:
        result = await self._session.execute(
            select(NodeCertificateModel).where(NodeCertificateModel.certificate_id == certificate_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.state = CertificateState.REVOKED.value
        model.revoked_at = revoked_at
        await self._session.flush()
        return self._certificate_from_model(model)

    async def list_certificates(self, node_id: str) -> list[NodeCertificateRecord]:
        result = await self._session.execute(
            select(NodeCertificateModel)
            .where(NodeCertificateModel.node_id == node_id)
            .order_by(NodeCertificateModel.issued_at.asc())
        )
        return [self._certificate_from_model(model) for model in result.scalars().all()]

    async def get_node_observed_state(self, node_id: str) -> NodeObservedStateRecord | None:
        result = await self._session.execute(
            select(NodeObservedStateModel).where(NodeObservedStateModel.node_id == node_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._observed_state_from_model(model)

    async def upsert_node_observed_state(self, observed: NodeObservedStateRecord) -> NodeObservedStateRecord:
        existing = await self._session.execute(
            select(NodeObservedStateModel).where(NodeObservedStateModel.node_id == observed.node_id)
        )
        model = existing.scalar_one_or_none()
        if model is None:
            model = NodeObservedStateModel(
                node_id=observed.node_id,
                observed_lifecycle_state=observed.observed_lifecycle_state.value,
                enrollment_status=observed.enrollment_status.value,
                services_status=dict(observed.services_status),
                synthetic_status=observed.synthetic_status.value,
                health_state=observed.health_state.value,
                alloy_telemetry_flowing=observed.alloy_telemetry_flowing,
                enrollment_hook_completed=observed.enrollment_hook_completed,
                runtime_adapter_ack_state=observed.runtime_adapter_ack_state.value,
                last_seen_at=observed.last_seen_at,
                last_synthetic_at=observed.last_synthetic_at,
                last_runtime_ack_at=observed.last_runtime_ack_at,
                updated_at=observed.updated_at,
            )
            self._session.add(model)
            await self._session.flush()
            return observed
        model.observed_lifecycle_state = observed.observed_lifecycle_state.value
        model.enrollment_status = observed.enrollment_status.value
        model.services_status = dict(observed.services_status)
        model.synthetic_status = observed.synthetic_status.value
        model.health_state = observed.health_state.value
        model.alloy_telemetry_flowing = observed.alloy_telemetry_flowing
        model.enrollment_hook_completed = observed.enrollment_hook_completed
        model.runtime_adapter_ack_state = observed.runtime_adapter_ack_state.value
        model.last_seen_at = observed.last_seen_at
        model.last_synthetic_at = observed.last_synthetic_at
        model.last_runtime_ack_at = observed.last_runtime_ack_at
        await self._session.flush()
        return self._observed_state_from_model(model)

    async def create_health_signal(self, signal: HealthSignalRecord) -> HealthSignalRecord:
        model = HealthSignalModel(
            signal_id=signal.signal_id,
            node_id=signal.node_id,
            signal_type=signal.signal_type,
            severity=signal.severity.value,
            source=signal.source,
            component=signal.component,
            observed_at=signal.observed_at,
            details=dict(signal.details),
        )
        self._session.add(model)
        await self._session.flush()
        return signal

    async def list_health_signals(self, node_id: str) -> list[HealthSignalRecord]:
        result = await self._session.execute(
            select(HealthSignalModel)
            .where(HealthSignalModel.node_id == node_id)
            .order_by(HealthSignalModel.observed_at.asc())
        )
        return [self._health_signal_from_model(model) for model in result.scalars().all()]

    async def create_synthetic_check(self, check: SyntheticCheckRecord) -> SyntheticCheckRecord:
        model = SyntheticCheckModel(
            synthetic_check_id=check.synthetic_check_id,
            node_id=check.node_id,
            probe=check.probe,
            status=check.status.value,
            source=check.source,
            observed_at=check.observed_at,
            details=dict(check.details),
        )
        self._session.add(model)
        await self._session.flush()
        return check

    async def list_synthetic_checks(self, node_id: str) -> list[SyntheticCheckRecord]:
        result = await self._session.execute(
            select(SyntheticCheckModel)
            .where(SyntheticCheckModel.node_id == node_id)
            .order_by(SyntheticCheckModel.observed_at.asc())
        )
        return [self._synthetic_check_from_model(model) for model in result.scalars().all()]

    async def create_runtime_readiness(self, readiness: RuntimeReadinessRecord) -> RuntimeReadinessRecord:
        model = RuntimeReadinessModel(
            readiness_id=readiness.readiness_id,
            node_id=readiness.node_id,
            adapter_slug=readiness.adapter_slug,
            ack_state=readiness.ack_state.value,
            observed_at=readiness.observed_at,
            details=dict(readiness.details),
        )
        self._session.add(model)
        await self._session.flush()
        return readiness

    async def list_runtime_readiness(self, node_id: str) -> list[RuntimeReadinessRecord]:
        result = await self._session.execute(
            select(RuntimeReadinessModel)
            .where(RuntimeReadinessModel.node_id == node_id)
            .order_by(RuntimeReadinessModel.observed_at.asc())
        )
        return [self._runtime_readiness_from_model(model) for model in result.scalars().all()]

    async def get_traffic_eligibility(self, node_id: str) -> TrafficEligibilityRecord | None:
        result = await self._session.execute(
            select(TrafficEligibilityModel).where(TrafficEligibilityModel.node_id == node_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._traffic_eligibility_from_model(model)

    async def upsert_traffic_eligibility(self, eligibility: TrafficEligibilityRecord) -> TrafficEligibilityRecord:
        existing = await self._session.execute(
            select(TrafficEligibilityModel).where(TrafficEligibilityModel.node_id == eligibility.node_id)
        )
        model = existing.scalar_one_or_none()
        if model is None:
            model = TrafficEligibilityModel(
                node_id=eligibility.node_id,
                eligibility_state=eligibility.eligibility_state.value,
                adapter_ack_state=eligibility.adapter_ack_state.value,
                blocked_reasons=list(eligibility.blocked_reasons),
                eligible_at=eligibility.eligible_at,
                last_evaluated_at=eligibility.last_evaluated_at,
            )
            self._session.add(model)
            await self._session.flush()
            return eligibility
        model.eligibility_state = eligibility.eligibility_state.value
        model.adapter_ack_state = eligibility.adapter_ack_state.value
        model.blocked_reasons = list(eligibility.blocked_reasons)
        model.eligible_at = eligibility.eligible_at
        model.last_evaluated_at = eligibility.last_evaluated_at
        await self._session.flush()
        return self._traffic_eligibility_from_model(model)

    async def update_request_status(self, request_id: str, status: RequestStatus) -> FleetRequestRecord | None:
        result = await self._session.execute(
            select(FleetRequestModel).where(FleetRequestModel.request_id == request_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.status = status.value
        await self._session.flush()
        return self._request_from_model(model)

    async def count_failover_requests_since(
        self,
        *,
        environment: str,
        country: str,
        provider_selector: str | None,
        since,
        include_statuses: Sequence[RequestStatus],
    ) -> int:
        result = await self._session.execute(
            select(FleetRequestModel)
            .where(FleetRequestModel.request_type == RequestType.FAILOVER.value)
            .where(FleetRequestModel.environment == environment)
            .where(FleetRequestModel.country == country)
            .where(FleetRequestModel.provider_selector == provider_selector)
            .where(FleetRequestModel.created_at >= since)
            .where(FleetRequestModel.status.in_([status.value for status in include_statuses]))
        )
        return len(result.scalars().all())

    async def count_active_failover_requests(
        self,
        *,
        environment: str,
        country: str,
        provider_selector: str | None,
    ) -> int:
        result = await self._session.execute(
            select(FleetRequestModel)
            .where(FleetRequestModel.request_type == RequestType.FAILOVER.value)
            .where(FleetRequestModel.environment == environment)
            .where(FleetRequestModel.country == country)
            .where(FleetRequestModel.provider_selector == provider_selector)
            .where(
                FleetRequestModel.status.in_(
                    [
                        RequestStatus.ACCEPTED.value,
                        RequestStatus.AWAITING_APPROVAL.value,
                        RequestStatus.RUNNING.value,
                    ]
                )
            )
        )
        return len(result.scalars().all())

    async def get_latest_failover_request(
        self,
        *,
        environment: str,
        country: str,
        provider_selector: str | None,
        include_statuses: Sequence[RequestStatus],
    ) -> FleetRequestRecord | None:
        result = await self._session.execute(
            select(FleetRequestModel)
            .where(FleetRequestModel.request_type == RequestType.FAILOVER.value)
            .where(FleetRequestModel.environment == environment)
            .where(FleetRequestModel.country == country)
            .where(FleetRequestModel.provider_selector == provider_selector)
            .where(FleetRequestModel.status.in_([status.value for status in include_statuses]))
            .order_by(FleetRequestModel.created_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._request_from_model(model)

    @staticmethod
    def _request_from_model(model: FleetRequestModel) -> FleetRequestRecord:
        return FleetRequestRecord(
            request_id=model.request_id,
            request_type=RequestType(model.request_type),
            requested_by=model.requested_by,
            idempotency_key=model.idempotency_key,
            status=RequestStatus(model.status),
            environment=model.environment,
            country=model.country,
            provider_selector=model.provider_selector,
            region_selector=model.region_selector,
            node_class=model.node_class,
            node_pool_id=model.node_pool_id,
            target_node_id=model.target_node_id,
            reason_code=model.reason_code,
            approval_mode=model.approval_mode,
            requested_capacity_delta=model.requested_capacity_delta,
            correlation_id=model.correlation_id,
            signal_group_id=model.signal_group_id,
            confidence_score=model.confidence_score,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _operation_from_model(model: OperationRunModel) -> OperationRunRecord:
        return OperationRunRecord(
            operation_run_id=model.operation_run_id,
            request_id=model.request_id,
            operation_name=model.operation_name,
            status=OperationStatus(model.status),
            current_step=model.current_step,
            started_at=model.started_at,
            finished_at=model.finished_at,
        )

    @staticmethod
    def _operation_step_from_model(model: OperationStepModel) -> OperationStepRecord:
        return OperationStepRecord(
            operation_step_id=model.operation_step_id,
            operation_run_id=model.operation_run_id,
            step_name=model.step_name,
            status=OperationStepStatus(model.status),
            attempt=model.attempt,
            error_code=model.error_code,
            artifact_ref=model.artifact_ref,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _audit_from_model(model: AuditEntryModel) -> AuditEntryRecord:
        return AuditEntryRecord(
            audit_entry_id=model.audit_entry_id,
            event_type=model.event_type,
            actor=model.actor,
            payload=dict(model.payload or {}),
            request_id=model.request_id,
            operation_run_id=model.operation_run_id,
            created_at=model.created_at,
        )

    @staticmethod
    def _node_from_model(model: NodeModel) -> NodeRecord:
        return NodeRecord(
            node_id=model.node_id,
            environment=model.environment,
            role=model.role,
            country=model.country,
            provider=model.provider,
            region=model.region,
            node_class=model.node_class,
            current_lifecycle_state=LifecycleState(model.current_lifecycle_state),
            enrollment_status=EnrollmentStatus(model.enrollment_status),
            bootstrap_state=BootstrapState(model.bootstrap_state),
            certificate_state=CertificateState(model.certificate_state),
            provider_resource_state=ProviderResourceState(model.provider_resource_state),
            request_id=model.request_id,
            operation_run_id=model.operation_run_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _node_pool_from_model(model: NodePoolModel) -> NodePoolRecord:
        return NodePoolRecord(
            node_pool_id=model.node_pool_id,
            environment=model.environment,
            country=model.country,
            role=model.role,
            node_class=model.node_class,
            provider_selector=model.provider_selector,
            region_selector=model.region_selector,
            desired_capacity=model.desired_capacity,
            current_capacity=model.current_capacity,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _budget_policy_from_model(model: BudgetPolicyModel) -> BudgetPolicyRecord:
        return BudgetPolicyRecord(
            budget_policy_id=model.budget_policy_id,
            scope_id=model.scope_id,
            environment=model.environment,
            country=model.country,
            provider_selector=model.provider_selector,
            monthly_limit=model.monthly_limit,
            burst_limit=model.burst_limit,
            current_month_spend=model.current_month_spend,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _rate_limit_policy_from_model(model: RateLimitPolicyModel) -> RateLimitPolicyRecord:
        return RateLimitPolicyRecord(
            rate_limit_policy_id=model.rate_limit_policy_id,
            scope_id=model.scope_id,
            environment=model.environment,
            country=model.country,
            provider_selector=model.provider_selector,
            max_actions_per_window=model.max_actions_per_window,
            window_seconds=model.window_seconds,
            cooldown_seconds=model.cooldown_seconds,
            max_parallel_failovers=model.max_parallel_failovers,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _approval_policy_from_model(model: ApprovalPolicyModel) -> ApprovalPolicyRecord:
        return ApprovalPolicyRecord(
            approval_policy_id=model.approval_policy_id,
            scope_id=model.scope_id,
            environment=model.environment,
            country=model.country,
            provider_selector=model.provider_selector,
            risk_threshold=model.risk_threshold,
            budget_approval_threshold=model.budget_approval_threshold,
            approval_mode=model.approval_mode,
            require_human_above_threshold=model.require_human_above_threshold,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _failover_guardrail_policy_from_model(
        model: FailoverGuardrailPolicyModel,
    ) -> FailoverGuardrailPolicyRecord:
        return FailoverGuardrailPolicyRecord(
            failover_policy_id=model.failover_policy_id,
            scope_id=model.scope_id,
            environment=model.environment,
            country=model.country,
            provider_selector=model.provider_selector,
            confidence_score_threshold=model.confidence_score_threshold,
            minimum_independent_signal_sources=model.minimum_independent_signal_sources,
            country_emergency_stop=model.country_emergency_stop,
            node_class_allowlist=tuple(str(item) for item in list(model.node_class_allowlist or [])),
            provider_exclusion_window_seconds=model.provider_exclusion_window_seconds,
            traffic_canary_required=model.traffic_canary_required,
            rollback_and_drain_policy=model.rollback_and_drain_policy,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _bootstrap_token_from_model(model: BootstrapTokenModel) -> BootstrapTokenRecord:
        return BootstrapTokenRecord(
            token_id=model.token_id,
            node_id=model.node_id,
            operation_run_id=model.operation_run_id,
            wrapped_ref=model.wrapped_ref,
            role_name=model.role_name,
            wrap_ttl=model.wrap_ttl,
            expires_at=model.expires_at,
            consumed_at=model.consumed_at,
            created_at=model.created_at,
        )

    @staticmethod
    def _certificate_from_model(model: NodeCertificateModel) -> NodeCertificateRecord:
        return NodeCertificateRecord(
            certificate_id=model.certificate_id,
            node_id=model.node_id,
            role_name=model.role_name,
            serial=model.serial,
            common_name=model.common_name,
            state=CertificateState(model.state),
            issued_at=model.issued_at,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
        )

    @staticmethod
    def _observed_state_from_model(model: NodeObservedStateModel) -> NodeObservedStateRecord:
        return NodeObservedStateRecord(
            node_id=model.node_id,
            observed_lifecycle_state=LifecycleState(model.observed_lifecycle_state),
            enrollment_status=EnrollmentStatus(model.enrollment_status),
            services_status={str(key): str(value) for key, value in dict(model.services_status or {}).items()},
            synthetic_status=SyntheticStatus(model.synthetic_status),
            health_state=HealthState(model.health_state),
            alloy_telemetry_flowing=model.alloy_telemetry_flowing,
            enrollment_hook_completed=model.enrollment_hook_completed,
            runtime_adapter_ack_state=AdapterAckState(model.runtime_adapter_ack_state),
            last_seen_at=model.last_seen_at,
            last_synthetic_at=model.last_synthetic_at,
            last_runtime_ack_at=model.last_runtime_ack_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _health_signal_from_model(model: HealthSignalModel) -> HealthSignalRecord:
        return HealthSignalRecord(
            signal_id=model.signal_id,
            node_id=model.node_id,
            signal_type=model.signal_type,
            severity=SignalSeverity(model.severity),
            source=model.source,
            component=model.component,
            observed_at=model.observed_at,
            details=dict(model.details or {}),
        )

    @staticmethod
    def _synthetic_check_from_model(model: SyntheticCheckModel) -> SyntheticCheckRecord:
        return SyntheticCheckRecord(
            synthetic_check_id=model.synthetic_check_id,
            node_id=model.node_id,
            probe=model.probe,
            status=SyntheticStatus(model.status),
            source=model.source,
            observed_at=model.observed_at,
            details=dict(model.details or {}),
        )

    @staticmethod
    def _runtime_readiness_from_model(model: RuntimeReadinessModel) -> RuntimeReadinessRecord:
        return RuntimeReadinessRecord(
            readiness_id=model.readiness_id,
            node_id=model.node_id,
            adapter_slug=model.adapter_slug,
            ack_state=AdapterAckState(model.ack_state),
            observed_at=model.observed_at,
            details=dict(model.details or {}),
        )

    @staticmethod
    def _traffic_eligibility_from_model(model: TrafficEligibilityModel) -> TrafficEligibilityRecord:
        reasons = tuple(str(item) for item in list(model.blocked_reasons or []))
        return TrafficEligibilityRecord(
            node_id=model.node_id,
            eligibility_state=TrafficEligibilityState(model.eligibility_state),
            adapter_ack_state=AdapterAckState(model.adapter_ack_state),
            blocked_reasons=reasons,
            eligible_at=model.eligible_at,
            last_evaluated_at=model.last_evaluated_at,
        )
