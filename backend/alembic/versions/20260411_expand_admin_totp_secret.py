"""Expand admin_users.totp_secret to support encrypted secrets.

Revision ID: 20260411_totp_secret
Revises: 20260410_customer_staff_notes
Create Date: 2026-04-11 12:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260411_totp_secret"
down_revision: str | None = "20260410_customer_staff_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow encrypted TOTP secrets to be stored in admin_users."""
    op.alter_column(
        "admin_users",
        "totp_secret",
        existing_type=sa.String(length=32),
        type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Restore the legacy TOTP secret column width."""
    op.alter_column(
        "admin_users",
        "totp_secret",
        existing_type=sa.String(length=255),
        type_=sa.String(length=32),
        existing_nullable=True,
    )
