"""Partner workspace workflow events for cases and review requests."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260419_rb002_partner_workspace_workflows"
down_revision = "20260419_phase8_pilot_runbook_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partner_workspace_workflow_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("subject_kind", sa.String(length=30), nullable=False),
        sa.Column("subject_id", sa.String(length=255), nullable=False),
        sa.Column("action_kind", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_partner_workspace_workflow_events_partner_account_id",
        "partner_workspace_workflow_events",
        ["partner_account_id"],
    )
    op.create_index(
        "ix_partner_workspace_workflow_events_subject_kind",
        "partner_workspace_workflow_events",
        ["subject_kind"],
    )
    op.create_index(
        "ix_partner_workspace_workflow_events_subject_id",
        "partner_workspace_workflow_events",
        ["subject_id"],
    )
    op.create_index(
        "ix_partner_workspace_workflow_events_action_kind",
        "partner_workspace_workflow_events",
        ["action_kind"],
    )
    op.create_index(
        "ix_partner_workspace_workflow_events_created_by_admin_user_id",
        "partner_workspace_workflow_events",
        ["created_by_admin_user_id"],
    )
    op.create_index(
        "ix_partner_workspace_workflow_events_created_at",
        "partner_workspace_workflow_events",
        ["created_at"],
    )
    op.create_index(
        "ix_partner_workspace_workflow_events_subject_scope",
        "partner_workspace_workflow_events",
        ["partner_account_id", "subject_kind", "subject_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_partner_workspace_workflow_events_subject_scope",
        table_name="partner_workspace_workflow_events",
    )
    op.drop_index(
        "ix_partner_workspace_workflow_events_created_at",
        table_name="partner_workspace_workflow_events",
    )
    op.drop_index(
        "ix_partner_workspace_workflow_events_created_by_admin_user_id",
        table_name="partner_workspace_workflow_events",
    )
    op.drop_index(
        "ix_partner_workspace_workflow_events_action_kind",
        table_name="partner_workspace_workflow_events",
    )
    op.drop_index(
        "ix_partner_workspace_workflow_events_subject_id",
        table_name="partner_workspace_workflow_events",
    )
    op.drop_index(
        "ix_partner_workspace_workflow_events_subject_kind",
        table_name="partner_workspace_workflow_events",
    )
    op.drop_index(
        "ix_partner_workspace_workflow_events_partner_account_id",
        table_name="partner_workspace_workflow_events",
    )
    op.drop_table("partner_workspace_workflow_events")
