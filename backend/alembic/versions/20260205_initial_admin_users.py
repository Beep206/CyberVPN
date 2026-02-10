"""Create initial admin_users table.

Revision ID: 20260205_initial
Revises:
Create Date: 2026-02-05 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260205_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create admin_users table."""
    op.create_table(
        "admin_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("login", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=True, index=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("role", sa.String(20), default="viewer", nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), unique=True, nullable=True, index=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("totp_secret", sa.String(32), nullable=True),
        sa.Column("totp_enabled", sa.Boolean(), default=False, nullable=False),
        sa.Column("backup_codes_hash", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("anti_phishing_code", sa.String(50), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_email_verified", sa.Boolean(), default=False, nullable=False),
    )

    # Indexes are created automatically by SQLAlchemy from column definitions


def downgrade() -> None:
    """Drop admin_users table."""
    op.drop_table("admin_users")
