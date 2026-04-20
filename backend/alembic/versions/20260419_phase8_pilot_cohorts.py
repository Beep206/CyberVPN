"""Phase 8 pilot cohorts and rollout windows."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260419_phase8_pilot_cohorts"
down_revision = "20260419_phase8_operational_overlays"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pilot_cohorts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cohort_key", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("lane_key", sa.String(length=40), nullable=False),
        sa.Column("surface_key", sa.String(length=40), nullable=False),
        sa.Column("cohort_status", sa.String(length=30), nullable=False, server_default="scheduled"),
        sa.Column("partner_account_id", sa.Uuid(), nullable=True),
        sa.Column("owner_team", sa.String(length=40), nullable=False),
        sa.Column("owner_admin_user_id", sa.Uuid(), nullable=False),
        sa.Column("rollback_trigger_code", sa.String(length=120), nullable=False),
        sa.Column("shadow_gate_payload", sa.JSON(), nullable=False),
        sa.Column("monitoring_payload", sa.JSON(), nullable=False),
        sa.Column("notes_payload", sa.JSON(), nullable=False),
        sa.Column("scheduled_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pause_reason_code", sa.String(length=120), nullable=True),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("activated_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("paused_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_admin_user_id"], ["admin_users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["activated_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["paused_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cohort_key"),
    )
    op.create_index("ix_pilot_cohorts_cohort_key", "pilot_cohorts", ["cohort_key"])
    op.create_index("ix_pilot_cohorts_lane_key", "pilot_cohorts", ["lane_key"])
    op.create_index("ix_pilot_cohorts_surface_key", "pilot_cohorts", ["surface_key"])
    op.create_index("ix_pilot_cohorts_cohort_status", "pilot_cohorts", ["cohort_status"])
    op.create_index("ix_pilot_cohorts_partner_account_id", "pilot_cohorts", ["partner_account_id"])
    op.create_index("ix_pilot_cohorts_owner_team", "pilot_cohorts", ["owner_team"])
    op.create_index("ix_pilot_cohorts_owner_admin_user_id", "pilot_cohorts", ["owner_admin_user_id"])
    op.create_index("ix_pilot_cohorts_scheduled_start_at", "pilot_cohorts", ["scheduled_start_at"])
    op.create_index("ix_pilot_cohorts_scheduled_end_at", "pilot_cohorts", ["scheduled_end_at"])
    op.create_index("ix_pilot_cohorts_activated_at", "pilot_cohorts", ["activated_at"])
    op.create_index("ix_pilot_cohorts_paused_at", "pilot_cohorts", ["paused_at"])
    op.create_index("ix_pilot_cohorts_completed_at", "pilot_cohorts", ["completed_at"])
    op.create_index(
        "ix_pilot_cohorts_created_by_admin_user_id",
        "pilot_cohorts",
        ["created_by_admin_user_id"],
    )
    op.create_index(
        "ix_pilot_cohorts_activated_by_admin_user_id",
        "pilot_cohorts",
        ["activated_by_admin_user_id"],
    )
    op.create_index(
        "ix_pilot_cohorts_paused_by_admin_user_id",
        "pilot_cohorts",
        ["paused_by_admin_user_id"],
    )

    op.create_table(
        "pilot_rollout_windows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pilot_cohort_id", sa.Uuid(), nullable=False),
        sa.Column("window_kind", sa.String(length=30), nullable=False),
        sa.Column("target_ref", sa.String(length=255), nullable=False),
        sa.Column("window_status", sa.String(length=30), nullable=False, server_default="scheduled"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes_payload", sa.JSON(), nullable=False),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("closed_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pilot_cohort_id"], ["pilot_cohorts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["closed_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pilot_rollout_windows_pilot_cohort_id", "pilot_rollout_windows", ["pilot_cohort_id"])
    op.create_index("ix_pilot_rollout_windows_window_kind", "pilot_rollout_windows", ["window_kind"])
    op.create_index("ix_pilot_rollout_windows_target_ref", "pilot_rollout_windows", ["target_ref"])
    op.create_index("ix_pilot_rollout_windows_window_status", "pilot_rollout_windows", ["window_status"])
    op.create_index("ix_pilot_rollout_windows_starts_at", "pilot_rollout_windows", ["starts_at"])
    op.create_index("ix_pilot_rollout_windows_ends_at", "pilot_rollout_windows", ["ends_at"])
    op.create_index(
        "ix_pilot_rollout_windows_created_by_admin_user_id",
        "pilot_rollout_windows",
        ["created_by_admin_user_id"],
    )
    op.create_index(
        "ix_pilot_rollout_windows_closed_by_admin_user_id",
        "pilot_rollout_windows",
        ["closed_by_admin_user_id"],
    )
    op.create_index("ix_pilot_rollout_windows_closed_at", "pilot_rollout_windows", ["closed_at"])


def downgrade() -> None:
    op.drop_index("ix_pilot_rollout_windows_closed_at", table_name="pilot_rollout_windows")
    op.drop_index(
        "ix_pilot_rollout_windows_closed_by_admin_user_id",
        table_name="pilot_rollout_windows",
    )
    op.drop_index(
        "ix_pilot_rollout_windows_created_by_admin_user_id",
        table_name="pilot_rollout_windows",
    )
    op.drop_index("ix_pilot_rollout_windows_ends_at", table_name="pilot_rollout_windows")
    op.drop_index("ix_pilot_rollout_windows_starts_at", table_name="pilot_rollout_windows")
    op.drop_index("ix_pilot_rollout_windows_window_status", table_name="pilot_rollout_windows")
    op.drop_index("ix_pilot_rollout_windows_target_ref", table_name="pilot_rollout_windows")
    op.drop_index("ix_pilot_rollout_windows_window_kind", table_name="pilot_rollout_windows")
    op.drop_index("ix_pilot_rollout_windows_pilot_cohort_id", table_name="pilot_rollout_windows")
    op.drop_table("pilot_rollout_windows")

    op.drop_index("ix_pilot_cohorts_paused_by_admin_user_id", table_name="pilot_cohorts")
    op.drop_index("ix_pilot_cohorts_activated_by_admin_user_id", table_name="pilot_cohorts")
    op.drop_index("ix_pilot_cohorts_created_by_admin_user_id", table_name="pilot_cohorts")
    op.drop_index("ix_pilot_cohorts_completed_at", table_name="pilot_cohorts")
    op.drop_index("ix_pilot_cohorts_paused_at", table_name="pilot_cohorts")
    op.drop_index("ix_pilot_cohorts_activated_at", table_name="pilot_cohorts")
    op.drop_index("ix_pilot_cohorts_scheduled_end_at", table_name="pilot_cohorts")
    op.drop_index("ix_pilot_cohorts_scheduled_start_at", table_name="pilot_cohorts")
    op.drop_index("ix_pilot_cohorts_owner_admin_user_id", table_name="pilot_cohorts")
    op.drop_index("ix_pilot_cohorts_owner_team", table_name="pilot_cohorts")
    op.drop_index("ix_pilot_cohorts_partner_account_id", table_name="pilot_cohorts")
    op.drop_index("ix_pilot_cohorts_cohort_status", table_name="pilot_cohorts")
    op.drop_index("ix_pilot_cohorts_surface_key", table_name="pilot_cohorts")
    op.drop_index("ix_pilot_cohorts_lane_key", table_name="pilot_cohorts")
    op.drop_index("ix_pilot_cohorts_cohort_key", table_name="pilot_cohorts")
    op.drop_table("pilot_cohorts")
