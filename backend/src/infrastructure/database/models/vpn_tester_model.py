"""SQLAlchemy models for the CyberVPN VPN Tester."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base


class VpnTestSuiteModel(Base):
    __tablename__ = "vpn_test_suites"
    __table_args__ = (
        UniqueConstraint("suite_key", "version", name="uq_vpn_test_suites_key_version"),
        Index("ix_vpn_test_suites_enabled_mode", "enabled", "mode"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    suite_key: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False, default="v1")
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    mode: Mapped[str] = mapped_column(String(40), nullable=False, default="contract")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    spec: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VpnTestRunModel(Base):
    __tablename__ = "vpn_test_runs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_vpn_test_runs_idempotency_key"),
        Index("ix_vpn_test_runs_status_created_at", "status", "created_at"),
        Index("ix_vpn_test_runs_suite_key_created_at", "suite_key", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    suite_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    suite_version: Mapped[str] = mapped_column(String(40), nullable=False, default="v1")
    mode: Mapped[str] = mapped_column(String(40), nullable=False, default="contract")
    trigger: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    requested_by_admin_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    request_context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    agent_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    runtime_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    route_registry_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pass_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    degraded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    results: Mapped[list[VpnTestResultModel]] = relationship(
        "VpnTestResultModel",
        cascade="all, delete-orphan",
        lazy="selectin",
        back_populates="run",
    )
    evidence_artifacts: Mapped[list[VpnTestEvidenceArtifactModel]] = relationship(
        "VpnTestEvidenceArtifactModel",
        cascade="all, delete-orphan",
        lazy="selectin",
        back_populates="run",
    )


class VpnTestResultModel(Base):
    __tablename__ = "vpn_test_results"
    __table_args__ = (
        UniqueConstraint("run_id", "check_key", "target", name="uq_vpn_test_results_run_check_target"),
        Index("ix_vpn_test_results_run_status", "run_id", "status"),
        Index("ix_vpn_test_results_category_status", "category", "status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vpn_test_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    check_key: Mapped[str] = mapped_column(String(120), nullable=False)
    check_name: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, default="contract")
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    severity: Mapped[str] = mapped_column(String(24), nullable=False, default="error")
    target: Mapped[str] = mapped_column(String(180), nullable=False, default="global")
    safe_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    run: Mapped[VpnTestRunModel] = relationship("VpnTestRunModel", lazy="raise", back_populates="results")


class VpnRouteRegistryEntryModel(Base):
    __tablename__ = "vpn_route_registry_entries"
    __table_args__ = (
        UniqueConstraint("registry_key", "route_key", name="uq_vpn_route_registry_key_route"),
        Index("ix_vpn_route_registry_suite_enabled", "suite_key", "enabled"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    registry_key: Mapped[str] = mapped_column(String(80), nullable=False)
    route_key: Mapped[str] = mapped_column(String(120), nullable=False)
    suite_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    node_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    expected_modes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VpnTestScheduleModel(Base):
    __tablename__ = "vpn_test_schedules"
    __table_args__ = (
        UniqueConstraint("schedule_key", name="uq_vpn_test_schedules_key"),
        Index("ix_vpn_test_schedules_enabled_next_run", "enabled", "next_run_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    schedule_key: Mapped[str] = mapped_column(String(100), nullable=False)
    suite_key: Mapped[str] = mapped_column(String(80), nullable=False)
    mode: Mapped[str] = mapped_column(String(40), nullable=False, default="contract")
    cron: Mapped[str] = mapped_column(String(80), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vpn_test_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    last_skipped_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    schedule_source: Mapped[str] = mapped_column(String(40), nullable=False, default="seeded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VpnTestEvidenceArtifactModel(Base):
    __tablename__ = "vpn_test_evidence_artifacts"
    __table_args__ = (
        UniqueConstraint("run_id", "artifact_key", name="uq_vpn_test_evidence_run_artifact"),
        Index("ix_vpn_test_evidence_run_created", "run_id", "created_at"),
        Index("ix_vpn_test_evidence_expires_at", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vpn_test_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(60), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    preview: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    storage_uri: Mapped[str | None] = mapped_column(String(300), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    run: Mapped[VpnTestRunModel] = relationship("VpnTestRunModel", lazy="raise", back_populates="evidence_artifacts")


class VpnBalancerRecommendationModel(Base):
    __tablename__ = "vpn_balancer_recommendations"
    __table_args__ = (
        UniqueConstraint("recommendation_key", name="uq_vpn_balancer_recommendation_key"),
        UniqueConstraint("recommendation_hash", name="uq_vpn_balancer_recommendation_hash"),
        Index("ix_vpn_balancer_recommendations_status_created", "status", "created_at"),
        Index("ix_vpn_balancer_recommendations_scope_status", "scope", "status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    recommendation_key: Mapped[str] = mapped_column(String(140), nullable=False)
    recommendation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vpn_test_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
    scope: Mapped[str] = mapped_column(String(80), nullable=False, default="global")
    safe_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    candidate_changes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    acknowledged_by_admin_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_by_admin_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_manually_by_admin_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    applied_manually_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VpnTestReleaseGateOverrideModel(Base):
    __tablename__ = "vpn_test_release_gate_overrides"
    __table_args__ = (
        Index("ix_vpn_test_release_gate_overrides_expires", "expires_at"),
        Index("ix_vpn_test_release_gate_overrides_created", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    latest_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vpn_test_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    overridden_by_admin_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    previous_status: Mapped[str] = mapped_column(String(40), nullable=False)
    previous_blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
