from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class FleetRequestModel(Base):
    __tablename__ = "fleet_requests"

    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    country: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_selector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    region_selector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    node_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    node_pool_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_node_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approval_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="automatic")
    requested_capacity_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signal_group_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class OperationRunModel(Base):
    __tablename__ = "operation_runs"

    operation_run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("fleet_requests.request_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    operation_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OperationStepModel(Base):
    __tablename__ = "operation_steps"

    operation_step_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    operation_run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("operation_runs.operation_run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    artifact_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class NodeModel(Base):
    __tablename__ = "nodes"

    node_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    node_class: Mapped[str] = mapped_column(String(64), nullable=False)
    current_lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False)
    enrollment_status: Mapped[str] = mapped_column(String(32), nullable=False)
    bootstrap_state: Mapped[str] = mapped_column(String(32), nullable=False)
    certificate_state: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_resource_state: Mapped[str] = mapped_column(String(32), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    operation_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class NodePoolModel(Base):
    __tablename__ = "node_pools"

    node_pool_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    country: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    node_class: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_selector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    region_selector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    desired_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class BudgetPolicyModel(Base):
    __tablename__ = "budget_policies"

    budget_policy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    scope_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    country: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_selector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    monthly_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    burst_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_month_spend: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class RateLimitPolicyModel(Base):
    __tablename__ = "rate_limit_policies"

    rate_limit_policy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    scope_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    country: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_selector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_actions_per_window: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_parallel_failovers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class ApprovalPolicyModel(Base):
    __tablename__ = "approval_policies"

    approval_policy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    scope_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    country: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_selector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_threshold: Mapped[float] = mapped_column(nullable=False, default=1.0)
    budget_approval_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approval_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="automatic")
    require_human_above_threshold: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class FailoverGuardrailPolicyModel(Base):
    __tablename__ = "failover_guardrail_policies"

    failover_policy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    scope_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    country: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_selector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_score_threshold: Mapped[float] = mapped_column(nullable=False, default=0.7)
    minimum_independent_signal_sources: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    country_emergency_stop: Mapped[bool] = mapped_column(nullable=False, default=False)
    node_class_allowlist: Mapped[list[object]] = mapped_column(JSON, nullable=False, default=list)
    provider_exclusion_window_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    traffic_canary_required: Mapped[bool] = mapped_column(nullable=False, default=True)
    rollback_and_drain_policy: Mapped[str] = mapped_column(String(128), nullable=False, default="parallel_replace_then_drain")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class BootstrapTokenModel(Base):
    __tablename__ = "bootstrap_tokens"

    token_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    node_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    operation_run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    wrapped_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    role_name: Mapped[str] = mapped_column(String(128), nullable=False)
    wrap_ttl: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class NodeCertificateModel(Base):
    __tablename__ = "node_certificates"

    certificate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    node_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_name: Mapped[str] = mapped_column(String(128), nullable=False)
    serial: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    common_name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NodeObservedStateModel(Base):
    __tablename__ = "node_observed_states"

    node_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("nodes.node_id", ondelete="CASCADE"),
        primary_key=True,
    )
    observed_lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False)
    enrollment_status: Mapped[str] = mapped_column(String(32), nullable=False)
    services_status: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    synthetic_status: Mapped[str] = mapped_column(String(32), nullable=False)
    health_state: Mapped[str] = mapped_column(String(32), nullable=False)
    alloy_telemetry_flowing: Mapped[bool] = mapped_column(nullable=False, default=False)
    enrollment_hook_completed: Mapped[bool] = mapped_column(nullable=False, default=False)
    runtime_adapter_ack_state: Mapped[str] = mapped_column(String(32), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_synthetic_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_runtime_ack_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class HealthSignalModel(Base):
    __tablename__ = "health_signals"

    signal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    node_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    component: Mapped[str] = mapped_column(String(128), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class SyntheticCheckModel(Base):
    __tablename__ = "synthetic_checks"

    synthetic_check_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    node_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    probe: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RuntimeReadinessModel(Base):
    __tablename__ = "runtime_readiness"

    readiness_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    node_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    adapter_slug: Mapped[str] = mapped_column(String(128), nullable=False)
    ack_state: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class TrafficEligibilityModel(Base):
    __tablename__ = "traffic_eligibility"

    node_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("nodes.node_id", ondelete="CASCADE"),
        primary_key=True,
    )
    eligibility_state: Mapped[str] = mapped_column(String(32), nullable=False)
    adapter_ack_state: Mapped[str] = mapped_column(String(32), nullable=False)
    blocked_reasons: Mapped[list[object]] = mapped_column(JSON, nullable=False, default=list)
    eligible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class AuditEntryModel(Base):
    __tablename__ = "audit_entries"

    audit_entry_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    operation_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
