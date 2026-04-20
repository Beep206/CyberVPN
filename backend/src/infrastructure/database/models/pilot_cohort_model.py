"""Canonical pilot cohort and rollout window models for Phase 8 activation controls."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PilotCohortModel(Base):
    __tablename__ = "pilot_cohorts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cohort_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    lane_key: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    surface_key: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    cohort_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="scheduled",
        server_default="scheduled",
        index=True,
    )
    partner_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    owner_team: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    owner_admin_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admin_users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    rollback_trigger_code: Mapped[str] = mapped_column(String(120), nullable=False)
    shadow_gate_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    monitoring_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    notes_payload: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    scheduled_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    pause_reason_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    activated_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    paused_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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


class PilotRolloutWindowModel(Base):
    __tablename__ = "pilot_rollout_windows"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pilot_cohort_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pilot_cohorts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    window_kind: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    target_ref: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    window_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="scheduled",
        server_default="scheduled",
        index=True,
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    notes_payload: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    closed_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
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


class PilotOwnerAcknowledgementModel(Base):
    __tablename__ = "pilot_owner_acknowledgements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pilot_cohort_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pilot_cohorts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_team: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    acknowledgement_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="acknowledged",
        server_default="acknowledged",
        index=True,
    )
    runbook_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    notes_payload: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    acknowledged_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
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


class PilotRollbackDrillModel(Base):
    __tablename__ = "pilot_rollback_drills"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pilot_cohort_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pilot_cohorts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cutover_unit_key: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    rollback_scope_class: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    trigger_code: Mapped[str] = mapped_column(String(120), nullable=False)
    drill_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    runbook_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    observed_metric_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    notes_payload: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    executed_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
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


class PilotGoNoGoDecisionModel(Base):
    __tablename__ = "pilot_go_no_go_decisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pilot_cohort_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pilot_cohorts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    decision_reason_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    release_ring: Mapped[str] = mapped_column(String(10), nullable=False, default="R3", server_default="R3")
    rollback_scope_class: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    cutover_unit_keys_payload: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    evidence_links_payload: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    acknowledged_owner_teams_payload: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    monitoring_snapshot_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    notes_payload: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    decided_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
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
