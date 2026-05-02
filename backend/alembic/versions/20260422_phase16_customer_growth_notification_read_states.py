"""Customer growth notification read/archive state for rewards inbox."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260422_phase16_customer_growth_notification_read_states"
down_revision = "20260421_phase15_mobile_telegram_pending_2fa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_growth_notification_read_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("mobile_user_id", sa.Uuid(), nullable=False),
        sa.Column("notification_key", sa.String(length=255), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["mobile_user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mobile_user_id",
            "notification_key",
            name="uq_customer_growth_notification_read_state_user_key",
        ),
    )
    op.create_index(
        "ix_customer_growth_notification_read_states_mobile_user_id",
        "customer_growth_notification_read_states",
        ["mobile_user_id"],
    )
    op.create_index(
        "ix_customer_growth_notification_read_states_notification_key",
        "customer_growth_notification_read_states",
        ["notification_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customer_growth_notification_read_states_notification_key",
        table_name="customer_growth_notification_read_states",
    )
    op.drop_index(
        "ix_customer_growth_notification_read_states_mobile_user_id",
        table_name="customer_growth_notification_read_states",
    )
    op.drop_table("customer_growth_notification_read_states")
