"""Add CyberVPN VPN Tester persistence.

Revision ID: 20260701_vpn_tester_aaa_v2
Revises: 20260629_invite_multi_use_v751
Create Date: 2026-07-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260701_vpn_tester_aaa_v2"
down_revision: str | Sequence[str] | None = "20260629_invite_multi_use_v751"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RUN_STATUSES = "'queued', 'running', 'pass', 'fail', 'degraded', 'cancelled'"
RESULT_STATUSES = "'pass', 'fail', 'degraded', 'skipped'"


def _uuid_type(bind: sa.engine.Connection) -> sa.types.TypeEngine:
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.Uuid(as_uuid=True)


def _json_type(bind: sa.engine.Connection) -> sa.types.TypeEngine:
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_default(bind: sa.engine.Connection, value: str) -> sa.text:
    if bind.dialect.name == "postgresql":
        return sa.text(f"'{value}'::jsonb")
    return sa.text(f"'{value}'")


def _uuid_default(bind: sa.engine.Connection) -> sa.text | None:
    if bind.dialect.name == "postgresql":
        return sa.text("gen_random_uuid()")
    return None


def upgrade() -> None:
    bind = op.get_bind()
    uuid_type = _uuid_type(bind)
    json_type = _json_type(bind)
    uuid_default = _uuid_default(bind)
    json_object = _json_default(bind, "{}")
    json_array = _json_default(bind, "[]")

    op.create_table(
        "vpn_test_suites",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("suite_key", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False, server_default="v1"),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=False, server_default="contract"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("spec", json_type, nullable=False, server_default=json_object),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("suite_key", "version", name="uq_vpn_test_suites_key_version"),
        sa.CheckConstraint(
            "mode IN ('contract', 'runtime', 'all_tariffs', 'balancer_preview')", name="ck_vpn_test_suites_mode"
        ),
    )
    op.create_index("ix_vpn_test_suites_enabled_mode", "vpn_test_suites", ["enabled", "mode"])

    op.create_table(
        "vpn_test_runs",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("suite_key", sa.String(length=80), nullable=False),
        sa.Column("suite_version", sa.String(length=40), nullable=False, server_default="v1"),
        sa.Column("mode", sa.String(length=40), nullable=False, server_default="contract"),
        sa.Column("trigger", sa.String(length=40), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column(
            "requested_by_admin_id", uuid_type, sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("idempotency_key", sa.String(length=160), nullable=True),
        sa.Column("request_context", json_type, nullable=False, server_default=json_object),
        sa.Column("summary", json_type, nullable=False, server_default=json_object),
        sa.Column("pass_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("degraded_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("idempotency_key", name="uq_vpn_test_runs_idempotency_key"),
        sa.CheckConstraint(f"status IN ({RUN_STATUSES})", name="ck_vpn_test_runs_status"),
        sa.CheckConstraint(
            "mode IN ('contract', 'runtime', 'all_tariffs', 'balancer_preview')", name="ck_vpn_test_runs_mode"
        ),
    )
    op.create_index("ix_vpn_test_runs_requested_by_admin_id", "vpn_test_runs", ["requested_by_admin_id"])
    op.create_index("ix_vpn_test_runs_status_created_at", "vpn_test_runs", ["status", "created_at"])
    op.create_index("ix_vpn_test_runs_suite_key", "vpn_test_runs", ["suite_key"])
    op.create_index("ix_vpn_test_runs_suite_key_created_at", "vpn_test_runs", ["suite_key", "created_at"])

    op.create_table(
        "vpn_test_results",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("run_id", uuid_type, sa.ForeignKey("vpn_test_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("check_key", sa.String(length=120), nullable=False),
        sa.Column("check_name", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False, server_default="contract"),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False, server_default="error"),
        sa.Column("target", sa.String(length=180), nullable=False, server_default="global"),
        sa.Column("safe_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("details", json_type, nullable=False, server_default=json_object),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", "check_key", "target", name="uq_vpn_test_results_run_check_target"),
        sa.CheckConstraint(f"status IN ({RESULT_STATUSES})", name="ck_vpn_test_results_status"),
    )
    op.create_index("ix_vpn_test_results_run_id", "vpn_test_results", ["run_id"])
    op.create_index("ix_vpn_test_results_run_status", "vpn_test_results", ["run_id", "status"])
    op.create_index("ix_vpn_test_results_category_status", "vpn_test_results", ["category", "status"])

    op.create_table(
        "vpn_route_registry_entries",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("registry_key", sa.String(length=80), nullable=False),
        sa.Column("route_key", sa.String(length=120), nullable=False),
        sa.Column("suite_key", sa.String(length=80), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False, server_default=""),
        sa.Column("node_tags", json_type, nullable=False, server_default=json_array),
        sa.Column("expected_modes", json_type, nullable=False, server_default=json_array),
        sa.Column("metadata", json_type, nullable=False, server_default=json_object),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("registry_key", "route_key", name="uq_vpn_route_registry_key_route"),
    )
    op.create_index("ix_vpn_route_registry_suite_enabled", "vpn_route_registry_entries", ["suite_key", "enabled"])

    op.create_table(
        "vpn_test_schedules",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("schedule_key", sa.String(length=100), nullable=False),
        sa.Column("suite_key", sa.String(length=80), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=False, server_default="contract"),
        sa.Column("cron", sa.String(length=80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("settings", json_type, nullable=False, server_default=json_object),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_id", uuid_type, sa.ForeignKey("vpn_test_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_status", sa.String(length=24), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("schedule_key", name="uq_vpn_test_schedules_key"),
        sa.CheckConstraint(
            "mode IN ('contract', 'runtime', 'all_tariffs', 'balancer_preview')", name="ck_vpn_test_schedules_mode"
        ),
    )
    op.create_index("ix_vpn_test_schedules_enabled_next_run", "vpn_test_schedules", ["enabled", "next_run_at"])

    op.create_table(
        "vpn_test_evidence_artifacts",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("run_id", uuid_type, sa.ForeignKey("vpn_test_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_key", sa.String(length=120), nullable=False),
        sa.Column("artifact_type", sa.String(length=60), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("preview", json_type, nullable=False, server_default=json_object),
        sa.Column("storage_uri", sa.String(length=300), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", "artifact_key", name="uq_vpn_test_evidence_run_artifact"),
    )
    op.create_index("ix_vpn_test_evidence_run_id", "vpn_test_evidence_artifacts", ["run_id"])
    op.create_index("ix_vpn_test_evidence_run_created", "vpn_test_evidence_artifacts", ["run_id", "created_at"])
    op.create_index("ix_vpn_test_evidence_expires_at", "vpn_test_evidence_artifacts", ["expires_at"])

    op.create_table(
        "vpn_balancer_recommendations",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("recommendation_key", sa.String(length=140), nullable=False),
        sa.Column("run_id", uuid_type, sa.ForeignKey("vpn_test_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("scope", sa.String(length=80), nullable=False, server_default="global"),
        sa.Column("safe_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("candidate_changes", json_type, nullable=False, server_default=json_object),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("recommendation_key", name="uq_vpn_balancer_recommendation_key"),
    )
    op.create_index("ix_vpn_balancer_recommendations_run_id", "vpn_balancer_recommendations", ["run_id"])
    op.create_index(
        "ix_vpn_balancer_recommendations_status_created",
        "vpn_balancer_recommendations",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_vpn_balancer_recommendations_status_created", table_name="vpn_balancer_recommendations")
    op.drop_index("ix_vpn_balancer_recommendations_run_id", table_name="vpn_balancer_recommendations")
    op.drop_table("vpn_balancer_recommendations")

    op.drop_index("ix_vpn_test_evidence_expires_at", table_name="vpn_test_evidence_artifacts")
    op.drop_index("ix_vpn_test_evidence_run_created", table_name="vpn_test_evidence_artifacts")
    op.drop_index("ix_vpn_test_evidence_run_id", table_name="vpn_test_evidence_artifacts")
    op.drop_table("vpn_test_evidence_artifacts")

    op.drop_index("ix_vpn_test_schedules_enabled_next_run", table_name="vpn_test_schedules")
    op.drop_table("vpn_test_schedules")

    op.drop_index("ix_vpn_route_registry_suite_enabled", table_name="vpn_route_registry_entries")
    op.drop_table("vpn_route_registry_entries")

    op.drop_index("ix_vpn_test_results_category_status", table_name="vpn_test_results")
    op.drop_index("ix_vpn_test_results_run_status", table_name="vpn_test_results")
    op.drop_index("ix_vpn_test_results_run_id", table_name="vpn_test_results")
    op.drop_table("vpn_test_results")

    op.drop_index("ix_vpn_test_runs_suite_key_created_at", table_name="vpn_test_runs")
    op.drop_index("ix_vpn_test_runs_suite_key", table_name="vpn_test_runs")
    op.drop_index("ix_vpn_test_runs_status_created_at", table_name="vpn_test_runs")
    op.drop_index("ix_vpn_test_runs_requested_by_admin_id", table_name="vpn_test_runs")
    op.drop_table("vpn_test_runs")

    op.drop_index("ix_vpn_test_suites_enabled_mode", table_name="vpn_test_suites")
    op.drop_table("vpn_test_suites")
