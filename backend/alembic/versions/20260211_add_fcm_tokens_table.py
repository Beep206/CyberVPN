"""Add fcm_tokens table for push notification management.

Revision ID: 20260211_fcm_tokens
Revises: bfeb3e8e3ff2
Create Date: 2026-02-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260211_fcm_tokens"
down_revision: str | None = "bfeb3e8e3ff2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create fcm_tokens table."""
    op.create_table(
        "fcm_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(4096), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "device_id", name="uq_fcm_tokens_user_device"),
    )

    op.create_index(
        "ix_fcm_tokens_user_id",
        "fcm_tokens",
        ["user_id"],
    )


def downgrade() -> None:
    """Drop fcm_tokens table."""
    op.drop_index("ix_fcm_tokens_user_id", table_name="fcm_tokens")
    op.drop_table("fcm_tokens")
