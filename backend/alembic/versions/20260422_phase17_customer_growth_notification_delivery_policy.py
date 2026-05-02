"""Customer growth notification prefs and delivery planning records."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260422_phase17_customer_growth_notification_delivery_policy"
down_revision = "20260422_phase16_customer_growth_notification_read_states"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mobile_users",
        sa.Column(
            "notification_prefs",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )

    op.create_table(
        "customer_growth_notification_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("mobile_user_id", sa.Uuid(), nullable=False),
        sa.Column("notification_key", sa.String(length=255), nullable=False),
        sa.Column("notification_kind", sa.String(length=80), nullable=False),
        sa.Column("delivery_channel", sa.String(length=20), nullable=False),
        sa.Column("delivery_status", sa.String(length=20), nullable=False),
        sa.Column("status_reason", sa.String(length=120), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column("delivery_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source_kind", sa.String(length=80), nullable=True),
        sa.Column("source_id", sa.String(length=80), nullable=True),
        sa.Column("notification_queue_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("planned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mobile_user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["notification_queue_id"], ["notification_queue.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mobile_user_id",
            "notification_key",
            "delivery_channel",
            name="uq_customer_growth_notification_delivery_user_key_channel",
        ),
    )
    op.create_index(
        "ix_customer_growth_notification_deliveries_mobile_user_id",
        "customer_growth_notification_deliveries",
        ["mobile_user_id"],
    )
    op.create_index(
        "ix_customer_growth_notification_deliveries_notification_key",
        "customer_growth_notification_deliveries",
        ["notification_key"],
    )
    op.create_index(
        "ix_customer_growth_notification_deliveries_notification_kind",
        "customer_growth_notification_deliveries",
        ["notification_kind"],
    )
    op.create_index(
        "ix_customer_growth_notification_deliveries_delivery_channel",
        "customer_growth_notification_deliveries",
        ["delivery_channel"],
    )
    op.create_index(
        "ix_customer_growth_notification_deliveries_delivery_status",
        "customer_growth_notification_deliveries",
        ["delivery_status"],
    )
    op.create_index(
        "ix_customer_growth_notification_deliveries_notification_queue_id",
        "customer_growth_notification_deliveries",
        ["notification_queue_id"],
    )
    op.create_index(
        "ix_customer_growth_notification_deliveries_created_by_admin_user_id",
        "customer_growth_notification_deliveries",
        ["created_by_admin_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customer_growth_notification_deliveries_created_by_admin_user_id",
        table_name="customer_growth_notification_deliveries",
    )
    op.drop_index(
        "ix_customer_growth_notification_deliveries_notification_queue_id",
        table_name="customer_growth_notification_deliveries",
    )
    op.drop_index(
        "ix_customer_growth_notification_deliveries_delivery_status",
        table_name="customer_growth_notification_deliveries",
    )
    op.drop_index(
        "ix_customer_growth_notification_deliveries_delivery_channel",
        table_name="customer_growth_notification_deliveries",
    )
    op.drop_index(
        "ix_customer_growth_notification_deliveries_notification_kind",
        table_name="customer_growth_notification_deliveries",
    )
    op.drop_index(
        "ix_customer_growth_notification_deliveries_notification_key",
        table_name="customer_growth_notification_deliveries",
    )
    op.drop_index(
        "ix_customer_growth_notification_deliveries_mobile_user_id",
        table_name="customer_growth_notification_deliveries",
    )
    op.drop_table("customer_growth_notification_deliveries")
    op.drop_column("mobile_users", "notification_prefs")
