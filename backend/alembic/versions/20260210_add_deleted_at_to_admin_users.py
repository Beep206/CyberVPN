"""Add deleted_at column to admin_users for soft-delete (FEAT-03).

Revision ID: 20260210_deleted_at
Revises: 20260205_refresh_tokens
Create Date: 2026-02-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260210_deleted_at"
down_revision: str | None = "20260205_refresh_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add deleted_at nullable timestamp column for soft-delete."""
    op.add_column(
        "admin_users",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove deleted_at column."""
    op.drop_column("admin_users", "deleted_at")
