"""Create notification queue table.

Revision ID: 20260422_notification_queue
Revises: 20260422_p16_cust_notif_reads
Create Date: 2026-04-22
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260422_notification_queue"
down_revision = "20260422_p16_cust_notif_reads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_queue",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_queue_status_scheduled",
        "notification_queue",
        ["status", "scheduled_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_queue_status_scheduled", table_name="notification_queue")
    op.drop_table("notification_queue")
