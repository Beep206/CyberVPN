"""Partner notification read/archive state for workspace-scoped inbox feed."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260420_phase11_partner_notification_read_states"
down_revision = "20260420_phase10_partner_workspace_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partner_notification_read_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("admin_user_id", sa.Uuid(), nullable=False),
        sa.Column("notification_key", sa.String(length=255), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "partner_account_id",
            "admin_user_id",
            "notification_key",
            name="uq_partner_notification_read_state_workspace_actor_key",
        ),
    )
    op.create_index(
        "ix_partner_notification_read_states_partner_account_id",
        "partner_notification_read_states",
        ["partner_account_id"],
    )
    op.create_index(
        "ix_partner_notification_read_states_admin_user_id",
        "partner_notification_read_states",
        ["admin_user_id"],
    )
    op.create_index(
        "ix_partner_notification_read_states_notification_key",
        "partner_notification_read_states",
        ["notification_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_partner_notification_read_states_notification_key",
        table_name="partner_notification_read_states",
    )
    op.drop_index(
        "ix_partner_notification_read_states_admin_user_id",
        table_name="partner_notification_read_states",
    )
    op.drop_index(
        "ix_partner_notification_read_states_partner_account_id",
        table_name="partner_notification_read_states",
    )
    op.drop_table("partner_notification_read_states")
