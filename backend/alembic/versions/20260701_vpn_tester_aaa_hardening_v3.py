"""Harden CyberVPN VPN Tester AAA v3 persistence.

Revision ID: 20260701_vpn_tester_aaa_hardening_v3
Revises: 20260701_vpn_tester_aaa_v2
Create Date: 2026-07-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260701_vpn_tester_aaa_hardening_v3"
down_revision: str | Sequence[str] | None = "20260701_vpn_tester_aaa_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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

    if bind.dialect.name == "postgresql":
        op.drop_constraint("ck_vpn_test_runs_status", "vpn_test_runs", type_="check")
        op.execute("UPDATE vpn_test_runs SET status = 'degraded' WHERE status = 'skipped'")
        op.create_check_constraint(
            "ck_vpn_test_runs_status",
            "vpn_test_runs",
            "status IN ('queued', 'running', 'pass', 'fail', 'degraded', 'skipped', 'cancelled')",
        )

    with op.batch_alter_table("vpn_test_runs") as batch:
        batch.add_column(sa.Column("agent_id", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("runtime_mode", sa.String(length=40), nullable=True))
        batch.add_column(sa.Column("route_registry_version", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("blocking", sa.Boolean(), nullable=False, server_default=sa.false()))

    with op.batch_alter_table("vpn_test_schedules") as batch:
        batch.add_column(sa.Column("last_skipped_reason", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("schedule_source", sa.String(length=40), nullable=False, server_default="seeded"))

    with op.batch_alter_table("vpn_balancer_recommendations") as batch:
        batch.add_column(sa.Column("recommendation_hash", sa.String(length=64), nullable=True))
        batch.add_column(
            sa.Column(
                "acknowledged_by_admin_id",
                uuid_type,
                sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch.add_column(sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column(
                "dismissed_by_admin_id",
                uuid_type,
                sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch.add_column(sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("dismissed_reason", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column(
                "applied_manually_by_admin_id",
                uuid_type,
                sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch.add_column(sa.Column("applied_manually_at", sa.DateTime(timezone=True), nullable=True))

    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "UPDATE vpn_balancer_recommendations "
                "SET recommendation_hash = substring(recommendation_key from 1 for 64) "
                "WHERE recommendation_hash IS NULL"
            )
        )
    else:
        op.execute(
            sa.text(
                "UPDATE vpn_balancer_recommendations "
                "SET recommendation_hash = substr(recommendation_key, 1, 64) "
                "WHERE recommendation_hash IS NULL"
            )
        )
    with op.batch_alter_table("vpn_balancer_recommendations") as batch:
        batch.alter_column("recommendation_hash", nullable=False, existing_type=sa.String(length=64))
    op.create_unique_constraint(
        "uq_vpn_balancer_recommendation_hash",
        "vpn_balancer_recommendations",
        ["recommendation_hash"],
    )
    op.create_index(
        "ix_vpn_balancer_recommendations_scope_status",
        "vpn_balancer_recommendations",
        ["scope", "status"],
    )
    op.create_index(
        "ix_vpn_balancer_recommendations_ack_admin",
        "vpn_balancer_recommendations",
        ["acknowledged_by_admin_id"],
    )
    op.create_index(
        "ix_vpn_balancer_recommendations_dismiss_admin",
        "vpn_balancer_recommendations",
        ["dismissed_by_admin_id"],
    )

    op.create_table(
        "vpn_test_release_gate_overrides",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("latest_run_id", uuid_type, sa.ForeignKey("vpn_test_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "overridden_by_admin_id",
            uuid_type,
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("previous_status", sa.String(length=40), nullable=False),
        sa.Column("previous_blocking", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_context", json_type, nullable=False, server_default=json_object),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_vpn_test_release_gate_overrides_latest_run",
        "vpn_test_release_gate_overrides",
        ["latest_run_id"],
    )
    op.create_index(
        "ix_vpn_test_release_gate_overrides_admin",
        "vpn_test_release_gate_overrides",
        ["overridden_by_admin_id"],
    )
    op.create_index(
        "ix_vpn_test_release_gate_overrides_expires",
        "vpn_test_release_gate_overrides",
        ["expires_at"],
    )
    op.create_index(
        "ix_vpn_test_release_gate_overrides_created",
        "vpn_test_release_gate_overrides",
        ["created_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("ck_vpn_test_runs_status", "vpn_test_runs", type_="check")
        op.create_check_constraint(
            "ck_vpn_test_runs_status",
            "vpn_test_runs",
            "status IN ('queued', 'running', 'pass', 'fail', 'degraded', 'cancelled')",
        )

    op.drop_index("ix_vpn_test_release_gate_overrides_created", table_name="vpn_test_release_gate_overrides")
    op.drop_index("ix_vpn_test_release_gate_overrides_expires", table_name="vpn_test_release_gate_overrides")
    op.drop_index("ix_vpn_test_release_gate_overrides_admin", table_name="vpn_test_release_gate_overrides")
    op.drop_index("ix_vpn_test_release_gate_overrides_latest_run", table_name="vpn_test_release_gate_overrides")
    op.drop_table("vpn_test_release_gate_overrides")

    op.drop_index("ix_vpn_balancer_recommendations_dismiss_admin", table_name="vpn_balancer_recommendations")
    op.drop_index("ix_vpn_balancer_recommendations_ack_admin", table_name="vpn_balancer_recommendations")
    op.drop_index("ix_vpn_balancer_recommendations_scope_status", table_name="vpn_balancer_recommendations")
    op.drop_constraint(
        "uq_vpn_balancer_recommendation_hash",
        "vpn_balancer_recommendations",
        type_="unique",
    )
    with op.batch_alter_table("vpn_balancer_recommendations") as batch:
        batch.drop_column("applied_manually_at")
        batch.drop_column("applied_manually_by_admin_id")
        batch.drop_column("dismissed_reason")
        batch.drop_column("dismissed_at")
        batch.drop_column("dismissed_by_admin_id")
        batch.drop_column("acknowledged_at")
        batch.drop_column("acknowledged_by_admin_id")
        batch.drop_column("recommendation_hash")

    with op.batch_alter_table("vpn_test_schedules") as batch:
        batch.drop_column("schedule_source")
        batch.drop_column("last_triggered_at")
        batch.drop_column("last_checked_at")
        batch.drop_column("last_skipped_reason")

    with op.batch_alter_table("vpn_test_runs") as batch:
        batch.drop_column("blocking")
        batch.drop_column("route_registry_version")
        batch.drop_column("runtime_mode")
        batch.drop_column("agent_id")
