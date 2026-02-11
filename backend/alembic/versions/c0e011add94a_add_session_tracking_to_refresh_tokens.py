"""add_session_tracking_to_refresh_tokens

Revision ID: c0e011add94a
Revises: 3d4a3384664c
Create Date: 2026-02-11 10:15:55.829473

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0e011add94a'
down_revision: Union[str, Sequence[str], None] = '3d4a3384664c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add session tracking fields to refresh_tokens table."""
    # Add device_id (nullable, max 255 chars, indexed)
    op.add_column('refresh_tokens', sa.Column('device_id', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_refresh_tokens_device_id'), 'refresh_tokens', ['device_id'], unique=False)

    # Add ip_address (nullable, max 45 chars for IPv6)
    op.add_column('refresh_tokens', sa.Column('ip_address', sa.String(length=45), nullable=True))

    # Add user_agent (nullable, max 512 chars)
    op.add_column('refresh_tokens', sa.Column('user_agent', sa.String(length=512), nullable=True))

    # Add last_used_at (default to now, updates on use)
    op.add_column('refresh_tokens', sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))


def downgrade() -> None:
    """Remove session tracking fields from refresh_tokens table."""
    op.drop_column('refresh_tokens', 'last_used_at')
    op.drop_column('refresh_tokens', 'user_agent')
    op.drop_column('refresh_tokens', 'ip_address')
    op.drop_index(op.f('ix_refresh_tokens_device_id'), table_name='refresh_tokens')
    op.drop_column('refresh_tokens', 'device_id')
