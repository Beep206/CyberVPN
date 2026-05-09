"""Add Telegram OIDC subject to mobile users.

Revision ID: 20260421_p14_tg_oidc_subject
Revises: 20260421_p13_code_quote_res
Create Date: 2026-04-21 18:10:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260421_p14_tg_oidc_subject"
down_revision = "20260421_p13_code_quote_res"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mobile_users", sa.Column("telegram_subject", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_mobile_users_telegram_subject"), "mobile_users", ["telegram_subject"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_mobile_users_telegram_subject"), table_name="mobile_users")
    op.drop_column("mobile_users", "telegram_subject")
