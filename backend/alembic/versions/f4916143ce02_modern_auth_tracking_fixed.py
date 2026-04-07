"""modern_auth_tracking_fixed

Revision ID: f4916143ce02
Revises: 20260331_oauth_token_retention
Create Date: 2026-04-07 17:59:54.299260

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f4916143ce02'
down_revision: Union[str, Sequence[str], None] = '20260331_oauth_token_retention'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # admin_users updates
    op.add_column('admin_users', sa.Column('failed_login_attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('admin_users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('admin_users', sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('admin_users', sa.Column('sign_in_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('admin_users', sa.Column('current_sign_in_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('admin_users', sa.Column('current_sign_in_ip', sa.String(length=45), nullable=True))
    op.add_column('admin_users', sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('admin_users', sa.Column('status', sa.String(length=20), server_default='active', nullable=False))
    op.add_column('admin_users', sa.Column('ban_reason', sa.Text(), nullable=True))
    op.add_column('admin_users', sa.Column('fraud_score', sa.Integer(), server_default='0', nullable=False))
    op.add_column('admin_users', sa.Column('risk_level', sa.String(length=20), server_default='low', nullable=False))
    op.add_column('admin_users', sa.Column('tos_accepted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('admin_users', sa.Column('marketing_consent', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('admin_users', sa.Column('referred_by_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_admin_users_referred_by_id', 'admin_users', 'admin_users', ['referred_by_id'], ['id'], ondelete='SET NULL')

    # oauth_accounts updates
    op.add_column('oauth_accounts', sa.Column('granted_scopes', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('oauth_accounts', sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('oauth_accounts', sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # oauth_accounts downgrade
    op.drop_column('oauth_accounts', 'revoked_at')
    op.drop_column('oauth_accounts', 'last_sync_at')
    op.drop_column('oauth_accounts', 'granted_scopes')

    # admin_users downgrade
    op.drop_constraint('fk_admin_users_referred_by_id', 'admin_users', type_='foreignkey')
    op.drop_column('admin_users', 'referred_by_id')
    op.drop_column('admin_users', 'marketing_consent')
    op.drop_column('admin_users', 'tos_accepted_at')
    op.drop_column('admin_users', 'risk_level')
    op.drop_column('admin_users', 'fraud_score')
    op.drop_column('admin_users', 'ban_reason')
    op.drop_column('admin_users', 'status')
    op.drop_column('admin_users', 'last_active_at')
    op.drop_column('admin_users', 'current_sign_in_ip')
    op.drop_column('admin_users', 'current_sign_in_at')
    op.drop_column('admin_users', 'sign_in_count')
    op.drop_column('admin_users', 'password_changed_at')
    op.drop_column('admin_users', 'locked_until')
    op.drop_column('admin_users', 'failed_login_attempts')
