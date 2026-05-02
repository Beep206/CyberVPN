from __future__ import annotations

import uuid
from datetime import UTC, datetime

from src.domain.entities import (
    BaselineProfile,
    HealthSignalRecord,
    NodeObservedStateRecord,
    NodeRecord,
    RuntimeReadinessRecord,
    SyntheticCheckRecord,
    TrafficEligibilityEvaluation,
    TrafficEligibilityRecord,
)
from src.domain.enums import (
    AdapterAckState,
    CertificateState,
    ComponentStatus,
    EnrollmentStatus,
    HealthState,
    LifecycleState,
    ProviderResourceState,
    SignalSeverity,
    SyntheticStatus,
    TrafficEligibilityState,
)
from src.domain.exceptions import NodeNotFoundError
from src.infra.database.repositories import FleetRequestRepository

BASELINE_RUNTIME_ADAPTER_BY_ROLE = {
    "vpn": "helix-adapter",
    "edge": "helix-adapter",
}
BASELINE_PRIMARY_SERVICE_BY_ROLE = {
    "vpn": "vpn-daemon",
    "edge": "edge-daemon",
}
BASELINE_SHARED_SERVICES = ("alloy", "fleet-health-agent")
BASELINE_REQUIRED_HOOKS = ("node-enrollment-hook",)
BASELINE_SYNTHETIC_PROBE = "egress-connectivity"


class ExternalNodeBaselineService:
    def __init__(self, repository: FleetRequestRepository) -> None:
        self._repository = repository

    async def get_baseline_profile(self, *, node_id: str) -> BaselineProfile:
        node = await self._get_node(node_id)
        return self._baseline_for_node(node)

    async def report_observed_state(
        self,
        *,
        node_id: str,
        services_status: dict[str, str],
        alloy_telemetry_flowing: bool,
        enrollment_hook_completed: bool,
    ) -> NodeObservedStateRecord:
        node = await self._get_node(node_id)
        existing = await self._get_or_create_observed_state(node)
        observed = NodeObservedStateRecord(
            node_id=node.node_id,
            observed_lifecycle_state=LifecycleState.VERIFYING,
            enrollment_status=node.enrollment_status,
            services_status={str(key): str(value) for key, value in services_status.items()},
            synthetic_status=existing.synthetic_status,
            health_state=existing.health_state,
            alloy_telemetry_flowing=alloy_telemetry_flowing,
            enrollment_hook_completed=enrollment_hook_completed,
            runtime_adapter_ack_state=existing.runtime_adapter_ack_state,
            last_seen_at=datetime.now(UTC),
            last_synthetic_at=existing.last_synthetic_at,
            last_runtime_ack_at=existing.last_runtime_ack_at,
        )
        return await self._repository.upsert_node_observed_state(observed)

    async def ingest_health_signal(
        self,
        *,
        node_id: str,
        signal_type: str,
        severity: SignalSeverity,
        source: str,
        component: str,
        details: dict[str, object] | None = None,
    ) -> tuple[HealthSignalRecord, NodeObservedStateRecord]:
        node = await self._get_node(node_id)
        existing = await self._get_or_create_observed_state(node)
        observed_at = datetime.now(UTC)
        signal = HealthSignalRecord(
            signal_id=f"hs_{uuid.uuid4().hex}",
            node_id=node_id,
            signal_type=signal_type,
            severity=severity,
            source=source,
            component=component,
            observed_at=observed_at,
            details=dict(details or {}),
        )
        await self._repository.create_health_signal(signal)
        updated_services = dict(existing.services_status)
        updated_services[component] = self._component_state_for_signal(severity).value
        observed = NodeObservedStateRecord(
            node_id=node.node_id,
            observed_lifecycle_state=existing.observed_lifecycle_state,
            enrollment_status=node.enrollment_status,
            services_status=updated_services,
            synthetic_status=existing.synthetic_status,
            health_state=self._health_state_for_signal(severity),
            alloy_telemetry_flowing=existing.alloy_telemetry_flowing,
            enrollment_hook_completed=existing.enrollment_hook_completed,
            runtime_adapter_ack_state=existing.runtime_adapter_ack_state,
            last_seen_at=observed_at,
            last_synthetic_at=existing.last_synthetic_at,
            last_runtime_ack_at=existing.last_runtime_ack_at,
        )
        stored = await self._repository.upsert_node_observed_state(observed)
        return signal, stored

    async def record_synthetic_check(
        self,
        *,
        node_id: str,
        probe: str,
        status: SyntheticStatus,
        source: str,
        details: dict[str, object] | None = None,
    ) -> tuple[SyntheticCheckRecord, NodeObservedStateRecord]:
        node = await self._get_node(node_id)
        existing = await self._get_or_create_observed_state(node)
        observed_at = datetime.now(UTC)
        check = SyntheticCheckRecord(
            synthetic_check_id=f"syn_{uuid.uuid4().hex}",
            node_id=node_id,
            probe=probe,
            status=status,
            source=source,
            observed_at=observed_at,
            details=dict(details or {}),
        )
        await self._repository.create_synthetic_check(check)
        observed = NodeObservedStateRecord(
            node_id=node.node_id,
            observed_lifecycle_state=existing.observed_lifecycle_state,
            enrollment_status=node.enrollment_status,
            services_status=dict(existing.services_status),
            synthetic_status=status,
            health_state=existing.health_state,
            alloy_telemetry_flowing=existing.alloy_telemetry_flowing,
            enrollment_hook_completed=existing.enrollment_hook_completed,
            runtime_adapter_ack_state=existing.runtime_adapter_ack_state,
            last_seen_at=existing.last_seen_at,
            last_synthetic_at=observed_at,
            last_runtime_ack_at=existing.last_runtime_ack_at,
        )
        stored = await self._repository.upsert_node_observed_state(observed)
        return check, stored

    async def record_runtime_readiness(
        self,
        *,
        node_id: str,
        adapter_slug: str,
        ack_state: AdapterAckState,
        details: dict[str, object] | None = None,
    ) -> tuple[RuntimeReadinessRecord, NodeObservedStateRecord]:
        node = await self._get_node(node_id)
        existing = await self._get_or_create_observed_state(node)
        observed_at = datetime.now(UTC)
        readiness = RuntimeReadinessRecord(
            readiness_id=f"rr_{uuid.uuid4().hex}",
            node_id=node_id,
            adapter_slug=adapter_slug,
            ack_state=ack_state,
            observed_at=observed_at,
            details=dict(details or {}),
        )
        await self._repository.create_runtime_readiness(readiness)
        observed = NodeObservedStateRecord(
            node_id=node.node_id,
            observed_lifecycle_state=existing.observed_lifecycle_state,
            enrollment_status=node.enrollment_status,
            services_status=dict(existing.services_status),
            synthetic_status=existing.synthetic_status,
            health_state=existing.health_state,
            alloy_telemetry_flowing=existing.alloy_telemetry_flowing,
            enrollment_hook_completed=existing.enrollment_hook_completed,
            runtime_adapter_ack_state=ack_state,
            last_seen_at=existing.last_seen_at,
            last_synthetic_at=existing.last_synthetic_at,
            last_runtime_ack_at=observed_at,
        )
        stored = await self._repository.upsert_node_observed_state(observed)
        return readiness, stored

    async def evaluate_traffic_eligibility(self, *, node_id: str) -> TrafficEligibilityEvaluation:
        node = await self._get_node(node_id)
        observed = await self._get_or_create_observed_state(node)
        baseline = self._baseline_for_node(node)
        reasons: list[str] = []

        if node.enrollment_status not in {EnrollmentStatus.ACCEPTED, EnrollmentStatus.CONFIGURED}:
            reasons.append("enrollment_not_complete")
        if not observed.enrollment_hook_completed:
            reasons.append("enrollment_hook_incomplete")
        for service_name in baseline.required_services:
            if observed.services_status.get(service_name) != ComponentStatus.RUNNING.value:
                reasons.append(f"service_not_running:{service_name}")
        if not observed.alloy_telemetry_flowing:
            reasons.append("alloy_telemetry_not_flowing")
        if observed.health_state != HealthState.HEALTHY:
            reasons.append("node_health_not_green")
        if node.certificate_state != CertificateState.ACTIVE:
            reasons.append("certificate_not_active")
        if node.provider_resource_state != ProviderResourceState.ACTIVE:
            reasons.append("provider_resource_not_active")
        if observed.synthetic_status != SyntheticStatus.PASSED:
            reasons.append("synthetic_checks_not_passing")
        if node.current_lifecycle_state == LifecycleState.QUARANTINED:
            reasons.append("node_quarantined")

        adapter_reason = None
        if observed.runtime_adapter_ack_state != AdapterAckState.ACKNOWLEDGED:
            adapter_reason = "runtime_adapter_not_acknowledged"

        now = datetime.now(UTC)
        if reasons:
            eligibility_state = TrafficEligibilityState.BLOCKED
            next_lifecycle = LifecycleState.VERIFYING
            blocked_reasons = tuple(reasons + ([adapter_reason] if adapter_reason else []))
            eligible_at = None
        elif adapter_reason is not None:
            eligibility_state = TrafficEligibilityState.READY
            next_lifecycle = LifecycleState.READY
            blocked_reasons = (adapter_reason,)
            eligible_at = None
        else:
            eligibility_state = TrafficEligibilityState.ELIGIBLE
            next_lifecycle = LifecycleState.TRAFFIC_ELIGIBLE
            blocked_reasons = ()
            eligible_at = now

        eligibility = await self._repository.upsert_traffic_eligibility(
            TrafficEligibilityRecord(
                node_id=node.node_id,
                eligibility_state=eligibility_state,
                adapter_ack_state=observed.runtime_adapter_ack_state,
                blocked_reasons=blocked_reasons,
                eligible_at=eligible_at,
                last_evaluated_at=now,
            )
        )
        updated_node = await self._repository.upsert_node(
            NodeRecord(
                node_id=node.node_id,
                environment=node.environment,
                role=node.role,
                country=node.country,
                provider=node.provider,
                region=node.region,
                node_class=node.node_class,
                current_lifecycle_state=next_lifecycle,
                enrollment_status=node.enrollment_status,
                bootstrap_state=node.bootstrap_state,
                certificate_state=node.certificate_state,
                provider_resource_state=node.provider_resource_state,
                request_id=node.request_id,
                operation_run_id=node.operation_run_id,
                created_at=node.created_at,
            )
        )
        return TrafficEligibilityEvaluation(
            node=updated_node,
            observed_state=observed,
            eligibility=eligibility,
            baseline_profile=baseline,
        )

    async def get_traffic_eligibility(self, *, node_id: str) -> TrafficEligibilityRecord | None:
        await self._get_node(node_id)
        return await self._repository.get_traffic_eligibility(node_id)

    async def _get_node(self, node_id: str) -> NodeRecord:
        node = await self._repository.get_node(node_id)
        if node is None:
            raise NodeNotFoundError(f"Node not found: {node_id}")
        return node

    async def _get_or_create_observed_state(self, node: NodeRecord) -> NodeObservedStateRecord:
        observed = await self._repository.get_node_observed_state(node.node_id)
        if observed is not None:
            return observed
        return NodeObservedStateRecord(
            node_id=node.node_id,
            observed_lifecycle_state=node.current_lifecycle_state,
            enrollment_status=node.enrollment_status,
            services_status={},
            synthetic_status=SyntheticStatus.PENDING,
            health_state=HealthState.UNKNOWN,
            alloy_telemetry_flowing=False,
            enrollment_hook_completed=False,
            runtime_adapter_ack_state=AdapterAckState.PENDING,
        )

    @staticmethod
    def _baseline_for_node(node: NodeRecord) -> BaselineProfile:
        primary_service = BASELINE_PRIMARY_SERVICE_BY_ROLE.get(node.role, "vpn-daemon")
        runtime_adapter = BASELINE_RUNTIME_ADAPTER_BY_ROLE.get(node.role, "helix-adapter")
        return BaselineProfile(
            node_id=node.node_id,
            role=node.role,
            runtime_adapter_slug=runtime_adapter,
            required_services=(*BASELINE_SHARED_SERVICES, primary_service),
            required_hooks=BASELINE_REQUIRED_HOOKS,
            synthetic_probe=BASELINE_SYNTHETIC_PROBE,
        )

    @staticmethod
    def _health_state_for_signal(severity: SignalSeverity) -> HealthState:
        if severity is SignalSeverity.CRITICAL:
            return HealthState.FAILED
        if severity is SignalSeverity.WARNING:
            return HealthState.DEGRADED
        return HealthState.HEALTHY

    @staticmethod
    def _component_state_for_signal(severity: SignalSeverity) -> ComponentStatus:
        if severity is SignalSeverity.CRITICAL:
            return ComponentStatus.FAILED
        if severity is SignalSeverity.WARNING:
            return ComponentStatus.DEGRADED
        return ComponentStatus.RUNNING
