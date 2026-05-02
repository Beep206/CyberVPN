from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .enums import (
    AdapterAckState,
    BootstrapState,
    CertificateState,
    EnrollmentStatus,
    HealthState,
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


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class FleetRequestSubmission:
    request_type: RequestType
    requested_by: str
    idempotency_key: str
    environment: str
    country: str | None = None
    provider_selector: str | None = None
    region_selector: str | None = None
    node_class: str | None = None
    node_pool_id: str | None = None
    target_node_id: str | None = None
    reason_code: str | None = None
    approval_mode: str = "automatic"
    requested_capacity_delta: int = 0
    correlation_id: str | None = None
    signal_group_id: str | None = None
    confidence_score: float | None = None


@dataclass(frozen=True)
class FleetRequestRecord:
    request_id: str
    request_type: RequestType
    requested_by: str
    idempotency_key: str
    status: RequestStatus
    environment: str
    country: str | None = None
    provider_selector: str | None = None
    region_selector: str | None = None
    node_class: str | None = None
    node_pool_id: str | None = None
    target_node_id: str | None = None
    reason_code: str | None = None
    approval_mode: str = "automatic"
    requested_capacity_delta: int = 0
    correlation_id: str | None = None
    signal_group_id: str | None = None
    confidence_score: float | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class OperationRunRecord:
    operation_run_id: str
    request_id: str
    operation_name: str
    status: OperationStatus
    current_step: str | None = None
    started_at: datetime = field(default_factory=utcnow)
    finished_at: datetime | None = None


@dataclass(frozen=True)
class AuditEntryRecord:
    audit_entry_id: str
    event_type: str
    actor: str
    payload: dict[str, object]
    request_id: str | None = None
    operation_run_id: str | None = None
    created_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class WorkflowStepDefinition:
    step_name: str
    target_lifecycle_state: LifecycleState | None = None
    requires_external_dependency: bool = False


@dataclass(frozen=True)
class ReconcileWorkItem:
    request: FleetRequestRecord
    operation_run: OperationRunRecord | None
    planned_steps: tuple[WorkflowStepDefinition, ...]


@dataclass(frozen=True)
class ReconcileExecutionResult:
    request: FleetRequestRecord
    operation_run: OperationRunRecord | None
    executed_steps: tuple[str, ...] = field(default_factory=tuple)
    blocked_on_external_dependency: bool = False


@dataclass(frozen=True)
class NodeRecord:
    node_id: str
    environment: str
    role: str
    country: str
    provider: str
    region: str
    node_class: str
    current_lifecycle_state: LifecycleState
    enrollment_status: EnrollmentStatus = EnrollmentStatus.PENDING
    bootstrap_state: BootstrapState = BootstrapState.NOT_ISSUED
    certificate_state: CertificateState = CertificateState.NOT_ISSUED
    provider_resource_state: ProviderResourceState = ProviderResourceState.PLANNED
    request_id: str | None = None
    operation_run_id: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class NodePoolRecord:
    node_pool_id: str
    environment: str
    country: str
    role: str
    node_class: str
    provider_selector: str | None = None
    region_selector: str | None = None
    desired_capacity: int = 0
    current_capacity: int = 0
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class BudgetPolicyRecord:
    budget_policy_id: str
    scope_id: str
    environment: str
    country: str | None = None
    provider_selector: str | None = None
    monthly_limit: int = 0
    burst_limit: int = 0
    current_month_spend: int = 0
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class RateLimitPolicyRecord:
    rate_limit_policy_id: str
    scope_id: str
    environment: str
    country: str | None = None
    provider_selector: str | None = None
    max_actions_per_window: int = 0
    window_seconds: int = 3600
    cooldown_seconds: int = 0
    max_parallel_failovers: int = 1
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class ApprovalPolicyRecord:
    approval_policy_id: str
    scope_id: str
    environment: str
    country: str | None = None
    provider_selector: str | None = None
    risk_threshold: float = 1.0
    budget_approval_threshold: int = 0
    approval_mode: str = "automatic"
    require_human_above_threshold: bool = True
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class FailoverGuardrailPolicyRecord:
    failover_policy_id: str
    scope_id: str
    environment: str
    country: str | None = None
    provider_selector: str | None = None
    confidence_score_threshold: float = 0.7
    minimum_independent_signal_sources: int = 2
    country_emergency_stop: bool = False
    node_class_allowlist: tuple[str, ...] = field(default_factory=tuple)
    provider_exclusion_window_seconds: int = 0
    traffic_canary_required: bool = True
    rollback_and_drain_policy: str = "parallel_replace_then_drain"
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class FailoverPolicyBundleRecord:
    scope_id: str
    budget_policy: BudgetPolicyRecord
    rate_limit_policy: RateLimitPolicyRecord
    approval_policy: ApprovalPolicyRecord
    guardrail_policy: FailoverGuardrailPolicyRecord


@dataclass(frozen=True)
class FailoverEvaluationRecord:
    scope_id: str
    decision_status: RequestStatus
    confidence_score: float
    independent_signal_sources: int
    risk_score: float
    budget_impact: int
    requires_human_approval: bool
    blocked_reasons: tuple[str, ...] = field(default_factory=tuple)
    cooldown_remaining_seconds: int = 0
    actions_in_window: int = 0
    active_parallel_failovers: int = 0
    canary_required: bool = True


@dataclass(frozen=True)
class BootstrapTokenRecord:
    token_id: str
    node_id: str
    operation_run_id: str
    wrapped_ref: str
    role_name: str
    wrap_ttl: str
    expires_at: datetime
    consumed_at: datetime | None = None
    created_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class NodeCertificateRecord:
    certificate_id: str
    node_id: str
    role_name: str
    serial: str
    common_name: str
    issued_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    state: CertificateState = CertificateState.ACTIVE


@dataclass(frozen=True)
class OperationStepRecord:
    operation_step_id: str
    operation_run_id: str
    step_name: str
    status: OperationStepStatus
    attempt: int
    error_code: str | None = None
    artifact_ref: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class ExecutionPreview:
    operation_run_id: str
    mode: str
    stack_dir: str
    workspace_key: str
    runner_pool: str
    state_lock_required: bool
    policy_check_required: bool
    plan_artifact_ref: str
    redacted_variables: dict[str, object]
    command_preview: tuple[str, ...]


@dataclass(frozen=True)
class EnrollmentCompletion:
    node_id: str
    reported_role: str
    certificate_common_name: str
    certificate_ttl_hours: int = 24


@dataclass(frozen=True)
class BaselineProfile:
    node_id: str
    role: str
    runtime_adapter_slug: str
    required_services: tuple[str, ...]
    required_hooks: tuple[str, ...]
    synthetic_probe: str


@dataclass(frozen=True)
class NodeObservedStateRecord:
    node_id: str
    observed_lifecycle_state: LifecycleState
    enrollment_status: EnrollmentStatus
    services_status: dict[str, str]
    synthetic_status: SyntheticStatus = SyntheticStatus.PENDING
    health_state: HealthState = HealthState.UNKNOWN
    alloy_telemetry_flowing: bool = False
    enrollment_hook_completed: bool = False
    runtime_adapter_ack_state: AdapterAckState = AdapterAckState.PENDING
    last_seen_at: datetime = field(default_factory=utcnow)
    last_synthetic_at: datetime | None = None
    last_runtime_ack_at: datetime | None = None
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class HealthSignalRecord:
    signal_id: str
    node_id: str
    signal_type: str
    severity: SignalSeverity
    source: str
    component: str
    observed_at: datetime
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SyntheticCheckRecord:
    synthetic_check_id: str
    node_id: str
    probe: str
    status: SyntheticStatus
    source: str
    observed_at: datetime
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeReadinessRecord:
    readiness_id: str
    node_id: str
    adapter_slug: str
    ack_state: AdapterAckState
    observed_at: datetime
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TrafficEligibilityRecord:
    node_id: str
    eligibility_state: TrafficEligibilityState
    adapter_ack_state: AdapterAckState
    blocked_reasons: tuple[str, ...]
    eligible_at: datetime | None = None
    last_evaluated_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class TrafficEligibilityEvaluation:
    node: NodeRecord
    observed_state: NodeObservedStateRecord
    eligibility: TrafficEligibilityRecord
    baseline_profile: BaselineProfile


@dataclass(frozen=True)
class OperatorCommandResult:
    command_name: str
    request: FleetRequestRecord | None
    operation_run: OperationRunRecord | None
    node_pool: NodePoolRecord | None = None
    policy_evaluation: FailoverEvaluationRecord | None = None
    no_op_reason: str | None = None
