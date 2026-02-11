"""Add trial fields to admin_users

Revision ID: a7f8e9b3c2d1
Revises: 20260210_codes_tables
Create Date: 2026-02-10 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7f8e9b3c2d1'
down_revision = '20260210_codes_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add trial tracking fields to admin_users table
    op.add_column('admin_users', sa.Column('trial_activated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('admin_users', sa.Column('trial_expires_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove trial tracking fields from admin_users table
    op.drop_column('admin_users', 'trial_expires_at')
    op.drop_column('admin_users', 'trial_activated_at')
