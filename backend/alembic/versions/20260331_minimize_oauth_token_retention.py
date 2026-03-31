"""Minimize OAuth token retention.

Revision ID: 20260331_oauth_token_retention
Revises: 20260213_audit_logs
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa

revision: str = "20260331_oauth_token_retention"
down_revision: str | None = "20260213_audit_logs"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("oauth_accounts"):
        return

    with op.batch_alter_table("oauth_accounts") as batch_op:
        batch_op.alter_column(
            "access_token",
            existing_type=sa.Text(),
            nullable=True,
        )

    bind.execute(sa.text("UPDATE oauth_accounts SET access_token = NULL, refresh_token = NULL"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("oauth_accounts"):
        return

    bind.execute(sa.text("UPDATE oauth_accounts SET access_token = '' WHERE access_token IS NULL"))
    bind.execute(sa.text("UPDATE oauth_accounts SET refresh_token = NULL"))

    with op.batch_alter_table("oauth_accounts") as batch_op:
        batch_op.alter_column(
            "access_token",
            existing_type=sa.Text(),
            nullable=False,
        )
