"""Create subscription plans and payments foundation tables.

Revision ID: 20260210_billing_core
Revises: 20260210_deleted_at
Create Date: 2026-02-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260210_billing_core"
down_revision: str | None = "20260210_deleted_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subscription_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("traffic_limit_bytes", sa.Integer(), nullable=True),
        sa.Column("device_limit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("price_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_rub", sa.Numeric(10, 2), nullable=True),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name", name="uq_subscription_plans_name"),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("user_uuid", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("subscription_days", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payments_external_id", "payments", ["external_id"], unique=False)
    op.create_index("ix_payments_user_uuid", "payments", ["user_uuid"], unique=False)
    op.create_index("ix_payments_status", "payments", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_user_uuid", table_name="payments")
    op.drop_index("ix_payments_external_id", table_name="payments")
    op.drop_table("payments")

    op.drop_table("subscription_plans")
