"""add_notification_prefs_to_admin_users

Revision ID: bfeb3e8e3ff2
Revises: c0e011add94a
Create Date: 2026-02-11 10:17:53.928490

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bfeb3e8e3ff2'
down_revision: str | Sequence[str] | None = 'c0e011add94a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add notification_prefs JSON column to admin_users table."""
    # Add notification preferences as JSON (nullable)
    op.add_column('admin_users', sa.Column('notification_prefs', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove notification_prefs column from admin_users table."""
    op.drop_column('admin_users', 'notification_prefs')
