"""Phase 8 pilot runbook hardening resources."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260419_phase8_pilot_runbook_hardening"
down_revision = "20260419_phase8_pilot_cohorts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pilot_owner_acknowledgements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pilot_cohort_id", sa.Uuid(), nullable=False),
        sa.Column("owner_team", sa.String(length=40), nullable=False),
        sa.Column(
            "acknowledgement_status",
            sa.String(length=30),
            nullable=False,
            server_default="acknowledged",
        ),
        sa.Column("runbook_reference", sa.String(length=255), nullable=False),
        sa.Column("notes_payload", sa.JSON(), nullable=False),
        sa.Column("acknowledged_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pilot_cohort_id"], ["pilot_cohorts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["acknowledged_by_admin_user_id"],
            ["admin_users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pilot_owner_acknowledgements_pilot_cohort_id",
        "pilot_owner_acknowledgements",
        ["pilot_cohort_id"],
    )
    op.create_index(
        "ix_pilot_owner_acknowledgements_owner_team",
        "pilot_owner_acknowledgements",
        ["owner_team"],
    )
    op.create_index(
        "ix_pilot_owner_acknowledgements_acknowledgement_status",
        "pilot_owner_acknowledgements",
        ["acknowledgement_status"],
    )
    op.create_index(
        "ix_pilot_owner_acknowledgements_acknowledged_by_admin_user_id",
        "pilot_owner_acknowledgements",
        ["acknowledged_by_admin_user_id"],
    )
    op.create_index(
        "ix_pilot_owner_acknowledgements_acknowledged_at",
        "pilot_owner_acknowledgements",
        ["acknowledged_at"],
    )

    op.create_table(
        "pilot_rollback_drills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pilot_cohort_id", sa.Uuid(), nullable=False),
        sa.Column("cutover_unit_key", sa.String(length=40), nullable=False),
        sa.Column("rollback_scope_class", sa.String(length=40), nullable=False),
        sa.Column("trigger_code", sa.String(length=120), nullable=False),
        sa.Column("drill_status", sa.String(length=20), nullable=False),
        sa.Column("runbook_reference", sa.String(length=255), nullable=False),
        sa.Column("observed_metric_payload", sa.JSON(), nullable=False),
        sa.Column("notes_payload", sa.JSON(), nullable=False),
        sa.Column("executed_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pilot_cohort_id"], ["pilot_cohorts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["executed_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pilot_rollback_drills_pilot_cohort_id",
        "pilot_rollback_drills",
        ["pilot_cohort_id"],
    )
    op.create_index(
        "ix_pilot_rollback_drills_cutover_unit_key",
        "pilot_rollback_drills",
        ["cutover_unit_key"],
    )
    op.create_index(
        "ix_pilot_rollback_drills_rollback_scope_class",
        "pilot_rollback_drills",
        ["rollback_scope_class"],
    )
    op.create_index(
        "ix_pilot_rollback_drills_drill_status",
        "pilot_rollback_drills",
        ["drill_status"],
    )
    op.create_index(
        "ix_pilot_rollback_drills_executed_by_admin_user_id",
        "pilot_rollback_drills",
        ["executed_by_admin_user_id"],
    )
    op.create_index(
        "ix_pilot_rollback_drills_executed_at",
        "pilot_rollback_drills",
        ["executed_at"],
    )

    op.create_table(
        "pilot_go_no_go_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pilot_cohort_id", sa.Uuid(), nullable=False),
        sa.Column("decision_status", sa.String(length=20), nullable=False),
        sa.Column("decision_reason_code", sa.String(length=120), nullable=True),
        sa.Column("release_ring", sa.String(length=10), nullable=False, server_default="R3"),
        sa.Column("rollback_scope_class", sa.String(length=40), nullable=False),
        sa.Column("cutover_unit_keys_payload", sa.JSON(), nullable=False),
        sa.Column("evidence_links_payload", sa.JSON(), nullable=False),
        sa.Column("acknowledged_owner_teams_payload", sa.JSON(), nullable=False),
        sa.Column("monitoring_snapshot_payload", sa.JSON(), nullable=False),
        sa.Column("notes_payload", sa.JSON(), nullable=False),
        sa.Column("decided_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pilot_cohort_id"], ["pilot_cohorts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pilot_go_no_go_decisions_pilot_cohort_id",
        "pilot_go_no_go_decisions",
        ["pilot_cohort_id"],
    )
    op.create_index(
        "ix_pilot_go_no_go_decisions_decision_status",
        "pilot_go_no_go_decisions",
        ["decision_status"],
    )
    op.create_index(
        "ix_pilot_go_no_go_decisions_rollback_scope_class",
        "pilot_go_no_go_decisions",
        ["rollback_scope_class"],
    )
    op.create_index(
        "ix_pilot_go_no_go_decisions_decided_by_admin_user_id",
        "pilot_go_no_go_decisions",
        ["decided_by_admin_user_id"],
    )
    op.create_index(
        "ix_pilot_go_no_go_decisions_decided_at",
        "pilot_go_no_go_decisions",
        ["decided_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pilot_go_no_go_decisions_decided_at", table_name="pilot_go_no_go_decisions")
    op.drop_index(
        "ix_pilot_go_no_go_decisions_decided_by_admin_user_id",
        table_name="pilot_go_no_go_decisions",
    )
    op.drop_index(
        "ix_pilot_go_no_go_decisions_rollback_scope_class",
        table_name="pilot_go_no_go_decisions",
    )
    op.drop_index(
        "ix_pilot_go_no_go_decisions_decision_status",
        table_name="pilot_go_no_go_decisions",
    )
    op.drop_index(
        "ix_pilot_go_no_go_decisions_pilot_cohort_id",
        table_name="pilot_go_no_go_decisions",
    )
    op.drop_table("pilot_go_no_go_decisions")

    op.drop_index("ix_pilot_rollback_drills_executed_at", table_name="pilot_rollback_drills")
    op.drop_index(
        "ix_pilot_rollback_drills_executed_by_admin_user_id",
        table_name="pilot_rollback_drills",
    )
    op.drop_index(
        "ix_pilot_rollback_drills_drill_status",
        table_name="pilot_rollback_drills",
    )
    op.drop_index(
        "ix_pilot_rollback_drills_rollback_scope_class",
        table_name="pilot_rollback_drills",
    )
    op.drop_index(
        "ix_pilot_rollback_drills_cutover_unit_key",
        table_name="pilot_rollback_drills",
    )
    op.drop_index(
        "ix_pilot_rollback_drills_pilot_cohort_id",
        table_name="pilot_rollback_drills",
    )
    op.drop_table("pilot_rollback_drills")

    op.drop_index(
        "ix_pilot_owner_acknowledgements_acknowledged_at",
        table_name="pilot_owner_acknowledgements",
    )
    op.drop_index(
        "ix_pilot_owner_acknowledgements_acknowledged_by_admin_user_id",
        table_name="pilot_owner_acknowledgements",
    )
    op.drop_index(
        "ix_pilot_owner_acknowledgements_acknowledgement_status",
        table_name="pilot_owner_acknowledgements",
    )
    op.drop_index(
        "ix_pilot_owner_acknowledgements_owner_team",
        table_name="pilot_owner_acknowledgements",
    )
    op.drop_index(
        "ix_pilot_owner_acknowledgements_pilot_cohort_id",
        table_name="pilot_owner_acknowledgements",
    )
    op.drop_table("pilot_owner_acknowledgements")
