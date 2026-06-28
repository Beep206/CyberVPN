"""Growth Codes v6 risk and FX snapshot ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class RiskModelVersionModel(Base):
    """Immutable model registry record used by risk decisions."""

    __tablename__ = "risk_model_versions"
    __table_args__ = (UniqueConstraint("model_key", "version", name="uq_risk_model_versions_model_key_version"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    model_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    artifact_uri: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(60), nullable=False)
    model_type: Mapped[str] = mapped_column(String(40), nullable=False)
    training_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    training_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    calibration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    deployment_mode: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    approval_state: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RiskFeatureSnapshotModel(Base):
    """Privacy-filtered feature snapshot used for reproducible decisions."""

    __tablename__ = "risk_feature_snapshots"
    __table_args__ = (UniqueConstraint("feature_hash", name="uq_risk_feature_snapshots_feature_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    risk_subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_schema_version: Mapped[str] = mapped_column(String(60), nullable=False)
    features_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    feature_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_freshness: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class GrowthRiskDecisionModel(Base):
    """Immutable hybrid rules/ML decision for a growth-code checkpoint."""

    __tablename__ = "growth_risk_decisions"
    __table_args__ = (
        CheckConstraint("ml_score IS NULL OR (ml_score >= 0 AND ml_score <= 1)", name="ck_growth_risk_decisions_score"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    risk_subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_subjects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code_set_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("checkout_code_sets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    growth_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    private_grant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("private_catalog_access_grants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    quote_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quote_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action_context: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    rules_policy_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("risk_model_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    feature_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("risk_feature_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rules_outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    ml_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    risk_band: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    final_action: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reason_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    fallback_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    decision_trace: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class FxRateSnapshotModel(Base):
    """Versioned FX rate observation used by fixed-discount conversions."""

    __tablename__ = "fx_rate_snapshots"
    __table_args__ = (
        CheckConstraint("rate > 0", name="ck_fx_rate_snapshots_rate_positive"),
        CheckConstraint("inverse_rate IS NULL OR inverse_rate > 0", name="ck_fx_rate_snapshots_inverse_positive"),
        UniqueConstraint(
            "base_currency",
            "quote_currency",
            "source_type",
            "provider_key",
            "observed_at",
            name="uq_fx_rate_snapshots_pair_provider_observed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider_config_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fx_provider_configs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    base_currency: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    quote_currency: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(30, 14), nullable=False)
    inverse_rate: Mapped[Decimal | None] = mapped_column(Numeric(30, 14), nullable=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    provider_rate_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    approval_state: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    approved_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    raw_provider_payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class FxProviderConfigModel(Base):
    """Durable FX provider refresh configuration for managed rate snapshots."""

    __tablename__ = "fx_provider_configs"
    __table_args__ = (
        CheckConstraint("priority >= 0", name="ck_fx_provider_configs_priority_non_negative"),
        CheckConstraint("stale_after_seconds > 0", name="ck_fx_provider_configs_stale_after_positive"),
        CheckConstraint("rate_ttl_seconds > 0", name="ck_fx_provider_configs_rate_ttl_positive"),
        UniqueConstraint("provider_key", name="uq_fx_provider_configs_provider_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true", index=True)
    supported_pairs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    stale_after_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600, server_default="3600")
    rate_ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600, server_default="3600")
    requires_admin_approval: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class FxProviderRefreshRunModel(Base):
    """Idempotent FX provider refresh execution record."""

    __tablename__ = "fx_provider_refresh_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','running','succeeded','failed','partial','cancelled')",
            name="ck_fx_provider_refresh_runs_status",
        ),
        CheckConstraint(
            "trigger_type IN ('scheduled','admin','manual','system_retry')",
            name="ck_fx_provider_refresh_runs_trigger_type",
        ),
        UniqueConstraint("run_key", name="uq_fx_provider_refresh_runs_run_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider_config_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fx_provider_configs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    run_key: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    requested_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pairs_requested: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    pairs_succeeded: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    pairs_failed: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    created_snapshot_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    provider_payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class FxDiscountConversionModel(Base):
    """Immutable fixed-discount conversion snapshot for a code application."""

    __tablename__ = "fx_discount_conversions"
    __table_args__ = (
        CheckConstraint("source_amount >= 0", name="ck_fx_discount_conversions_source_non_negative"),
        CheckConstraint("raw_converted_amount >= 0", name="ck_fx_discount_conversions_raw_non_negative"),
        CheckConstraint("rounded_amount >= 0", name="ck_fx_discount_conversions_rounded_non_negative"),
        CheckConstraint("applied_amount >= 0", name="ck_fx_discount_conversions_applied_non_negative"),
        CheckConstraint("target_minor_units >= 0", name="ck_fx_discount_conversions_minor_units_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code_application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("checkout_code_applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    source_currency: Mapped[str] = mapped_column(String(12), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(12), nullable=False)
    conversion_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    fx_rate_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fx_rate_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    configured_rate_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    raw_converted_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    rounded_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    applied_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    target_minor_units: Mapped[int] = mapped_column(nullable=False)
    rounding_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
