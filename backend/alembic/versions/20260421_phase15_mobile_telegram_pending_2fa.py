"""Add mobile TOTP fields for pending Telegram 2FA logins.

Revision ID: 20260421_phase15_mobile_telegram_pending_2fa
Revises: 20260421_phase14_mobile_telegram_oidc_subject
Create Date: 2026-04-21 23:10:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260421_phase15_mobile_telegram_pending_2fa"
down_revision = "20260421_phase14_mobile_telegram_oidc_subject"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mobile_users", sa.Column("totp_secret", sa.String(length=255), nullable=True))
    op.add_column(
        "mobile_users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("mobile_users", "totp_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("mobile_users", "totp_enabled")
    op.drop_column("mobile_users", "totp_secret")
