"""Customer growth notification delivery history ledger."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260422_p18_cust_notif_events"
down_revision = "20260422_p17_cust_notif_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_growth_notification_delivery_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("delivery_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("delivery_status", sa.String(length=20), nullable=False),
        sa.Column("reason_code", sa.String(length=120), nullable=True),
        sa.Column("event_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("event_note", sa.Text(), nullable=True),
        sa.Column("notification_queue_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["delivery_id"],
            ["customer_growth_notification_deliveries.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["notification_queue_id"], ["notification_queue.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_growth_notification_delivery_events_delivery_id",
        "customer_growth_notification_delivery_events",
        ["delivery_id"],
    )
    op.create_index(
        "ix_customer_growth_notification_delivery_events_event_type",
        "customer_growth_notification_delivery_events",
        ["event_type"],
    )
    op.create_index(
        "ix_customer_growth_notification_delivery_events_delivery_status",
        "customer_growth_notification_delivery_events",
        ["delivery_status"],
    )
    op.create_index(
        "ix_cust_growth_notif_event_queue_id",
        "customer_growth_notification_delivery_events",
        ["notification_queue_id"],
    )
    op.create_index(
        "ix_cust_growth_notif_event_admin_id",
        "customer_growth_notification_delivery_events",
        ["created_by_admin_user_id"],
    )
    op.create_index(
        "ix_customer_growth_notification_delivery_events_occurred_at",
        "customer_growth_notification_delivery_events",
        ["occurred_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customer_growth_notification_delivery_events_occurred_at",
        table_name="customer_growth_notification_delivery_events",
    )
    op.drop_index(
        "ix_cust_growth_notif_event_admin_id",
        table_name="customer_growth_notification_delivery_events",
    )
    op.drop_index(
        "ix_cust_growth_notif_event_queue_id",
        table_name="customer_growth_notification_delivery_events",
    )
    op.drop_index(
        "ix_customer_growth_notification_delivery_events_delivery_status",
        table_name="customer_growth_notification_delivery_events",
    )
    op.drop_index(
        "ix_customer_growth_notification_delivery_events_event_type",
        table_name="customer_growth_notification_delivery_events",
    )
    op.drop_index(
        "ix_customer_growth_notification_delivery_events_delivery_id",
        table_name="customer_growth_notification_delivery_events",
    )
    op.drop_table("customer_growth_notification_delivery_events")
