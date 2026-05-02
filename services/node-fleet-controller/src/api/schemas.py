from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.domain.entities import (
    ApprovalPolicyRecord,
    AuditEntryRecord,
    BaselineProfile,
    BootstrapTokenRecord,
    BudgetPolicyRecord,
    ExecutionPreview,
    FailoverEvaluationRecord,
    FailoverGuardrailPolicyRecord,
    FailoverPolicyBundleRecord,
    FleetRequestRecord,
    HealthSignalRecord,
    NodeCertificateRecord,
    NodeObservedStateRecord,
    NodePoolRecord,
    NodeRecord,
    OperatorCommandResult,
    OperationRunRecord,
    RateLimitPolicyRecord,
    ReconcileExecutionResult,
    ReconcileWorkItem,
    RuntimeReadinessRecord,
    SyntheticCheckRecord,
    TrafficEligibilityEvaluation,
    TrafficEligibilityRecord,
)
from src.domain.enums import (
    AdapterAckState,
    BootstrapState,
    CertificateState,
    ComponentStatus,
    EnrollmentStatus,
    HealthState,
    LifecycleState,
    OperationStatus,
    ProviderResourceState,
    RequestStatus,
    RequestType,
    SignalSeverity,
    SyntheticStatus,
    TrafficEligibilityState,
)


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


class SentryContractResponse(BaseModel):
    runtime_surface: str
    service: str
    environment: str
    release: str
    dsn_configured: bool


class CreateFleetRequestRequest(BaseModel):
    request_type: RequestType
    requested_by: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    environment: str = "nonprod"
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
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)


class FleetRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    approval_mode: str
    requested_capacity_delta: int
    correlation_id: str | None = None
    signal_group_id: str | None = None
    confidence_score: float | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, record: FleetRequestRecord) -> "FleetRequestResponse":
        return cls.model_validate(record)


class OperationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    operation_run_id: str
    request_id: str
    operation_name: str
    status: OperationStatus
    current_step: str | None = None
    started_at: datetime
    finished_at: datetime | None = None

    @classmethod
    def from_entity(cls, record: OperationRunRecord) -> "OperationRunResponse":
        return cls.model_validate(record)


class AuditEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_entry_id: str
    event_type: str
    actor: str
    payload: dict[str, object]
    request_id: str | None = None
    operation_run_id: str | None = None
    created_at: datetime

    @classmethod
    def from_entity(cls, record: AuditEntryRecord) -> "AuditEntryResponse":
        return cls.model_validate(record)


class CreateFleetRequestResponse(BaseModel):
    request: FleetRequestResponse
    operation_run: OperationRunResponse


class ReconcilePreviewItemResponse(BaseModel):
    request: FleetRequestResponse
    operation_run: OperationRunResponse | None = None
    planned_steps: list[str]

    @classmethod
    def from_entity(cls, item: ReconcileWorkItem) -> "ReconcilePreviewItemResponse":
        return cls(
            request=FleetRequestResponse.from_entity(item.request),
            operation_run=(
                OperationRunResponse.from_entity(item.operation_run)
                if item.operation_run is not None
                else None
            ),
            planned_steps=[step.step_name for step in item.planned_steps],
        )


class ReconcilePreviewResponse(BaseModel):
    items: list[ReconcilePreviewItemResponse]


class ReconcileRunResultResponse(BaseModel):
    request: FleetRequestResponse
    operation_run: OperationRunResponse | None = None
    executed_steps: list[str]
    blocked_on_external_dependency: bool

    @classmethod
    def from_entity(cls, item: ReconcileExecutionResult) -> "ReconcileRunResultResponse":
        return cls(
            request=FleetRequestResponse.from_entity(item.request),
            operation_run=(
                OperationRunResponse.from_entity(item.operation_run)
                if item.operation_run is not None
                else None
            ),
            executed_steps=list(item.executed_steps),
            blocked_on_external_dependency=item.blocked_on_external_dependency,
        )


class ReconcileRunOnceResponse(BaseModel):
    items: list[ReconcileRunResultResponse]


class CreateNodeRequest(BaseModel):
    node_id: str
    environment: str = "nonprod"
    role: str
    country: str
    provider: str
    region: str
    node_class: str
    request_id: str | None = None
    operation_run_id: str | None = None


class NodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    node_id: str
    environment: str
    role: str
    country: str
    provider: str
    region: str
    node_class: str
    current_lifecycle_state: LifecycleState
    enrollment_status: EnrollmentStatus
    bootstrap_state: BootstrapState
    certificate_state: CertificateState
    provider_resource_state: ProviderResourceState
    request_id: str | None = None
    operation_run_id: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, record: NodeRecord) -> "NodeResponse":
        return cls.model_validate(record)


class ExecutorPreviewRequest(BaseModel):
    stack_slug: str
    workspace_key: str
    variables: dict[str, object] = Field(default_factory=dict)


class ExecutorPreviewResponse(BaseModel):
    operation_run_id: str
    mode: str
    stack_dir: str
    workspace_key: str
    runner_pool: str
    state_lock_required: bool
    policy_check_required: bool
    plan_artifact_ref: str
    redacted_variables: dict[str, object]
    command_preview: list[str]

    @classmethod
    def from_entity(cls, preview: ExecutionPreview) -> "ExecutorPreviewResponse":
        return cls(
            operation_run_id=preview.operation_run_id,
            mode=preview.mode,
            stack_dir=preview.stack_dir,
            workspace_key=preview.workspace_key,
            runner_pool=preview.runner_pool,
            state_lock_required=preview.state_lock_required,
            policy_check_required=preview.policy_check_required,
            plan_artifact_ref=preview.plan_artifact_ref,
            redacted_variables=preview.redacted_variables,
            command_preview=list(preview.command_preview),
        )


class IssueBootstrapTokenRequest(BaseModel):
    operation_run_id: str


class BootstrapTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    token_id: str
    node_id: str
    operation_run_id: str
    wrapped_ref: str
    role_name: str
    wrap_ttl: str
    expires_at: datetime
    consumed_at: datetime | None = None
    created_at: datetime

    @classmethod
    def from_entity(cls, record: BootstrapTokenRecord) -> "BootstrapTokenResponse":
        return cls.model_validate(record)


class EnrollmentCompleteRequest(BaseModel):
    bootstrap_token_id: str
    reported_role: str
    certificate_common_name: str
    certificate_ttl_hours: int = 24


class NodeCertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    certificate_id: str
    node_id: str
    role_name: str
    serial: str
    common_name: str
    state: CertificateState
    issued_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None

    @classmethod
    def from_entity(cls, record: NodeCertificateRecord) -> "NodeCertificateResponse":
        return cls.model_validate(record)


class EnrollmentCompleteResponse(BaseModel):
    node: NodeResponse
    certificate: NodeCertificateResponse


class RotateCertificateRequest(BaseModel):
    common_name: str
    ttl_hours: int = 24


class RotateCertificateResponse(BaseModel):
    node: NodeResponse
    certificate: NodeCertificateResponse


class NodePoolUpsertRequest(BaseModel):
    environment: str = "nonprod"
    country: str
    role: str
    node_class: str
    provider_selector: str | None = None
    region_selector: str | None = None
    desired_capacity: int = Field(default=0, ge=0)
    current_capacity: int = Field(default=0, ge=0)


class NodePoolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    node_pool_id: str
    environment: str
    country: str
    role: str
    node_class: str
    provider_selector: str | None = None
    region_selector: str | None = None
    desired_capacity: int
    current_capacity: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, record: NodePoolRecord) -> "NodePoolResponse":
        return cls.model_validate(record)


class NodeAddCommandRequest(BaseModel):
    requested_by: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    environment: str = "nonprod"
    country: str
    role: str = "vpn"
    node_class: str
    provider_selector: str | None = "auto"
    region_selector: str | None = None
    requested_capacity_delta: int = Field(default=1, ge=1)
    approval_mode: str = "automatic"
    node_pool_id: str | None = None


class NodeReplaceCommandRequest(BaseModel):
    requested_by: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    target_node_id: str
    reason_code: str
    approval_mode: str = "automatic"


class NodeDrainCommandRequest(BaseModel):
    requested_by: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    target_node_id: str
    reason_code: str
    approval_mode: str = "automatic"


class NodeQuarantineCommandRequest(BaseModel):
    requested_by: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    target_node_id: str
    reason_code: str
    approval_mode: str = "automatic"


class FailoverBudgetPolicyRequest(BaseModel):
    monthly_limit: int = Field(ge=0)
    burst_limit: int = Field(ge=0)
    current_month_spend: int = Field(default=0, ge=0)


class FailoverRateLimitPolicyRequest(BaseModel):
    max_actions_per_window: int = Field(ge=0)
    window_seconds: int = Field(default=3600, ge=0)
    cooldown_seconds: int = Field(default=0, ge=0)
    max_parallel_failovers: int = Field(default=1, ge=0)


class FailoverApprovalPolicyRequest(BaseModel):
    risk_threshold: float = Field(ge=0.0, le=1.0)
    budget_approval_threshold: int = Field(default=0, ge=0)
    approval_mode: str = "automatic"
    require_human_above_threshold: bool = True


class FailoverGuardrailPolicyRequest(BaseModel):
    confidence_score_threshold: float = Field(ge=0.0, le=1.0)
    minimum_independent_signal_sources: int = Field(default=1, ge=1)
    country_emergency_stop: bool = False
    node_class_allowlist: list[str] = Field(default_factory=list)
    provider_exclusion_window_seconds: int = Field(default=0, ge=0)
    traffic_canary_required: bool = True
    rollback_and_drain_policy: str = "parallel_replace_then_drain"


class FailoverPolicyBundleUpsertRequest(BaseModel):
    environment: str = "nonprod"
    country: str
    provider_selector: str | None = "auto"
    budget_policy: FailoverBudgetPolicyRequest
    rate_limit_policy: FailoverRateLimitPolicyRequest
    approval_policy: FailoverApprovalPolicyRequest
    guardrail_policy: FailoverGuardrailPolicyRequest


class FailoverBudgetPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    budget_policy_id: str
    scope_id: str
    environment: str
    country: str | None = None
    provider_selector: str | None = None
    monthly_limit: int
    burst_limit: int
    current_month_spend: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, record: BudgetPolicyRecord) -> "FailoverBudgetPolicyResponse":
        return cls.model_validate(record)


class FailoverRateLimitPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rate_limit_policy_id: str
    scope_id: str
    environment: str
    country: str | None = None
    provider_selector: str | None = None
    max_actions_per_window: int
    window_seconds: int
    cooldown_seconds: int
    max_parallel_failovers: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, record: RateLimitPolicyRecord) -> "FailoverRateLimitPolicyResponse":
        return cls.model_validate(record)


class FailoverApprovalPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    approval_policy_id: str
    scope_id: str
    environment: str
    country: str | None = None
    provider_selector: str | None = None
    risk_threshold: float
    budget_approval_threshold: int
    approval_mode: str
    require_human_above_threshold: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, record: ApprovalPolicyRecord) -> "FailoverApprovalPolicyResponse":
        return cls.model_validate(record)


class FailoverGuardrailPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    failover_policy_id: str
    scope_id: str
    environment: str
    country: str | None = None
    provider_selector: str | None = None
    confidence_score_threshold: float
    minimum_independent_signal_sources: int
    country_emergency_stop: bool
    node_class_allowlist: list[str]
    provider_exclusion_window_seconds: int
    traffic_canary_required: bool
    rollback_and_drain_policy: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, record: FailoverGuardrailPolicyRecord) -> "FailoverGuardrailPolicyResponse":
        return cls(
            failover_policy_id=record.failover_policy_id,
            scope_id=record.scope_id,
            environment=record.environment,
            country=record.country,
            provider_selector=record.provider_selector,
            confidence_score_threshold=record.confidence_score_threshold,
            minimum_independent_signal_sources=record.minimum_independent_signal_sources,
            country_emergency_stop=record.country_emergency_stop,
            node_class_allowlist=list(record.node_class_allowlist),
            provider_exclusion_window_seconds=record.provider_exclusion_window_seconds,
            traffic_canary_required=record.traffic_canary_required,
            rollback_and_drain_policy=record.rollback_and_drain_policy,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class FailoverPolicyBundleResponse(BaseModel):
    scope_id: str
    budget_policy: FailoverBudgetPolicyResponse
    rate_limit_policy: FailoverRateLimitPolicyResponse
    approval_policy: FailoverApprovalPolicyResponse
    guardrail_policy: FailoverGuardrailPolicyResponse

    @classmethod
    def from_entity(cls, bundle: FailoverPolicyBundleRecord) -> "FailoverPolicyBundleResponse":
        return cls(
            scope_id=bundle.scope_id,
            budget_policy=FailoverBudgetPolicyResponse.from_entity(bundle.budget_policy),
            rate_limit_policy=FailoverRateLimitPolicyResponse.from_entity(bundle.rate_limit_policy),
            approval_policy=FailoverApprovalPolicyResponse.from_entity(bundle.approval_policy),
            guardrail_policy=FailoverGuardrailPolicyResponse.from_entity(bundle.guardrail_policy),
        )


class NodeFailoverCommandRequest(BaseModel):
    requested_by: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    environment: str = "nonprod"
    country: str
    node_class: str
    provider_selector: str | None = "auto"
    region_selector: str | None = None
    requested_capacity_delta: int = Field(default=1, ge=1)
    approval_mode: str = "automatic"
    signal_group_id: str = Field(min_length=1)
    confidence_score: float = Field(ge=0.0, le=1.0)
    independent_signal_sources: int = Field(default=1, ge=1)
    budget_impact: int = Field(default=1, ge=0)
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    reason_code: str = "dpi_detected"
    node_pool_id: str | None = None
    target_node_id: str | None = None


class FailoverEvaluationResponse(BaseModel):
    scope_id: str
    decision_status: RequestStatus
    confidence_score: float
    independent_signal_sources: int
    risk_score: float
    budget_impact: int
    requires_human_approval: bool
    blocked_reasons: list[str]
    cooldown_remaining_seconds: int
    actions_in_window: int
    active_parallel_failovers: int
    canary_required: bool

    @classmethod
    def from_entity(cls, record: FailoverEvaluationRecord) -> "FailoverEvaluationResponse":
        return cls(
            scope_id=record.scope_id,
            decision_status=record.decision_status,
            confidence_score=record.confidence_score,
            independent_signal_sources=record.independent_signal_sources,
            risk_score=record.risk_score,
            budget_impact=record.budget_impact,
            requires_human_approval=record.requires_human_approval,
            blocked_reasons=list(record.blocked_reasons),
            cooldown_remaining_seconds=record.cooldown_remaining_seconds,
            actions_in_window=record.actions_in_window,
            active_parallel_failovers=record.active_parallel_failovers,
            canary_required=record.canary_required,
        )


class CapacityAdjustmentRequest(BaseModel):
    requested_by: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    target_desired_capacity: int = Field(ge=0)
    reason_code: str = "capacity_adjustment"
    approval_mode: str = "automatic"


class OperatorCommandResponse(BaseModel):
    command_name: str
    request: FleetRequestResponse | None = None
    operation_run: OperationRunResponse | None = None
    node_pool: NodePoolResponse | None = None
    policy_evaluation: FailoverEvaluationResponse | None = None
    no_op_reason: str | None = None

    @classmethod
    def from_entity(cls, result: OperatorCommandResult) -> "OperatorCommandResponse":
        return cls(
            command_name=result.command_name,
            request=FleetRequestResponse.from_entity(result.request) if result.request is not None else None,
            operation_run=OperationRunResponse.from_entity(result.operation_run) if result.operation_run is not None else None,
            node_pool=NodePoolResponse.from_entity(result.node_pool) if result.node_pool is not None else None,
            policy_evaluation=(
                FailoverEvaluationResponse.from_entity(result.policy_evaluation)
                if result.policy_evaluation is not None
                else None
            ),
            no_op_reason=result.no_op_reason,
        )


class BaselineProfileResponse(BaseModel):
    node_id: str
    role: str
    runtime_adapter_slug: str
    required_services: list[str]
    required_hooks: list[str]
    synthetic_probe: str

    @classmethod
    def from_entity(cls, profile: BaselineProfile) -> "BaselineProfileResponse":
        return cls(
            node_id=profile.node_id,
            role=profile.role,
            runtime_adapter_slug=profile.runtime_adapter_slug,
            required_services=list(profile.required_services),
            required_hooks=list(profile.required_hooks),
            synthetic_probe=profile.synthetic_probe,
        )


class ReportObservedStateRequest(BaseModel):
    services_status: dict[str, ComponentStatus] = Field(default_factory=dict)
    alloy_telemetry_flowing: bool
    enrollment_hook_completed: bool


class NodeObservedStateResponse(BaseModel):
    node_id: str
    observed_lifecycle_state: LifecycleState
    enrollment_status: EnrollmentStatus
    services_status: dict[str, str]
    synthetic_status: SyntheticStatus
    health_state: HealthState
    alloy_telemetry_flowing: bool
    enrollment_hook_completed: bool
    runtime_adapter_ack_state: AdapterAckState
    last_seen_at: datetime
    last_synthetic_at: datetime | None = None
    last_runtime_ack_at: datetime | None = None
    updated_at: datetime

    @classmethod
    def from_entity(cls, observed: NodeObservedStateRecord) -> "NodeObservedStateResponse":
        return cls(
            node_id=observed.node_id,
            observed_lifecycle_state=observed.observed_lifecycle_state,
            enrollment_status=observed.enrollment_status,
            services_status=dict(observed.services_status),
            synthetic_status=observed.synthetic_status,
            health_state=observed.health_state,
            alloy_telemetry_flowing=observed.alloy_telemetry_flowing,
            enrollment_hook_completed=observed.enrollment_hook_completed,
            runtime_adapter_ack_state=observed.runtime_adapter_ack_state,
            last_seen_at=observed.last_seen_at,
            last_synthetic_at=observed.last_synthetic_at,
            last_runtime_ack_at=observed.last_runtime_ack_at,
            updated_at=observed.updated_at,
        )


class HealthSignalRequest(BaseModel):
    signal_type: str
    severity: SignalSeverity
    source: str
    component: str
    details: dict[str, object] = Field(default_factory=dict)


class HealthSignalResponse(BaseModel):
    signal_id: str
    node_id: str
    signal_type: str
    severity: SignalSeverity
    source: str
    component: str
    observed_at: datetime
    details: dict[str, object]

    @classmethod
    def from_entity(cls, signal: HealthSignalRecord) -> "HealthSignalResponse":
        return cls(
            signal_id=signal.signal_id,
            node_id=signal.node_id,
            signal_type=signal.signal_type,
            severity=signal.severity,
            source=signal.source,
            component=signal.component,
            observed_at=signal.observed_at,
            details=dict(signal.details),
        )


class HealthSignalIngestionResponse(BaseModel):
    signal: HealthSignalResponse
    observed_state: NodeObservedStateResponse


class SyntheticCheckRequest(BaseModel):
    probe: str
    status: SyntheticStatus
    source: str
    details: dict[str, object] = Field(default_factory=dict)


class SyntheticCheckResponse(BaseModel):
    synthetic_check_id: str
    node_id: str
    probe: str
    status: SyntheticStatus
    source: str
    observed_at: datetime
    details: dict[str, object]

    @classmethod
    def from_entity(cls, check: SyntheticCheckRecord) -> "SyntheticCheckResponse":
        return cls(
            synthetic_check_id=check.synthetic_check_id,
            node_id=check.node_id,
            probe=check.probe,
            status=check.status,
            source=check.source,
            observed_at=check.observed_at,
            details=dict(check.details),
        )


class SyntheticCheckIngestionResponse(BaseModel):
    check: SyntheticCheckResponse
    observed_state: NodeObservedStateResponse


class RuntimeReadinessRequest(BaseModel):
    adapter_slug: str
    ack_state: AdapterAckState
    details: dict[str, object] = Field(default_factory=dict)


class RuntimeReadinessResponse(BaseModel):
    readiness_id: str
    node_id: str
    adapter_slug: str
    ack_state: AdapterAckState
    observed_at: datetime
    details: dict[str, object]

    @classmethod
    def from_entity(cls, readiness: RuntimeReadinessRecord) -> "RuntimeReadinessResponse":
        return cls(
            readiness_id=readiness.readiness_id,
            node_id=readiness.node_id,
            adapter_slug=readiness.adapter_slug,
            ack_state=readiness.ack_state,
            observed_at=readiness.observed_at,
            details=dict(readiness.details),
        )


class RuntimeReadinessIngestionResponse(BaseModel):
    readiness: RuntimeReadinessResponse
    observed_state: NodeObservedStateResponse


class TrafficEligibilityResponse(BaseModel):
    node_id: str
    eligibility_state: TrafficEligibilityState
    adapter_ack_state: AdapterAckState
    blocked_reasons: list[str]
    eligible_at: datetime | None = None
    last_evaluated_at: datetime

    @classmethod
    def from_entity(cls, record: TrafficEligibilityRecord) -> "TrafficEligibilityResponse":
        return cls(
            node_id=record.node_id,
            eligibility_state=record.eligibility_state,
            adapter_ack_state=record.adapter_ack_state,
            blocked_reasons=list(record.blocked_reasons),
            eligible_at=record.eligible_at,
            last_evaluated_at=record.last_evaluated_at,
        )


class TrafficEligibilityEvaluationResponse(BaseModel):
    node: NodeResponse
    observed_state: NodeObservedStateResponse
    eligibility: TrafficEligibilityResponse
    baseline_profile: BaselineProfileResponse

    @classmethod
    def from_entity(cls, evaluation: TrafficEligibilityEvaluation) -> "TrafficEligibilityEvaluationResponse":
        return cls(
            node=NodeResponse.from_entity(evaluation.node),
            observed_state=NodeObservedStateResponse.from_entity(evaluation.observed_state),
            eligibility=TrafficEligibilityResponse.from_entity(evaluation.eligibility),
            baseline_profile=BaselineProfileResponse.from_entity(evaluation.baseline_profile),
        )
