"""add_profile_fields_to_admin_users

Revision ID: 3d4a3384664c
Revises: a7f8e9b3c2d1
Create Date: 2026-02-11 10:14:35.091230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d4a3384664c'
down_revision: Union[str, Sequence[str], None] = 'a7f8e9b3c2d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add profile fields to admin_users table."""
    # Add display_name (nullable, max 100 chars)
    op.add_column('admin_users', sa.Column('display_name', sa.String(length=100), nullable=True))

    # Add language (default 'en', max 10 chars)
    op.add_column('admin_users', sa.Column('language', sa.String(length=10), nullable=False, server_default='en'))

    # Add timezone (default 'UTC', max 50 chars)
    op.add_column('admin_users', sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'))


def downgrade() -> None:
    """Remove profile fields from admin_users table."""
    op.drop_column('admin_users', 'timezone')
    op.drop_column('admin_users', 'language')
    op.drop_column('admin_users', 'display_name')
