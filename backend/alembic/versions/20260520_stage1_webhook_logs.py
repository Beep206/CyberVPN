"""Create webhook logs table for payment and VPN callbacks.

Revision ID: 20260520_stage1_webhook_logs
Revises: 20260423_p27_partner_events
Create Date: 2026-05-20 14:45:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260520_stage1_webhook_logs"
down_revision: str | Sequence[str] | None = "20260423_p27_partner_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def _json_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB()
    return sa.JSON()


def upgrade() -> None:
    op.create_table(
        "webhook_logs",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=True),
        sa.Column("payload", _json_type(), nullable=False),
        sa.Column("signature", sa.String(length=255), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_logs_source", "webhook_logs", ["source"], unique=False)
    op.create_index("ix_webhook_logs_created_at", "webhook_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_webhook_logs_created_at", table_name="webhook_logs")
    op.drop_index("ix_webhook_logs_source", table_name="webhook_logs")
    op.drop_table("webhook_logs")
