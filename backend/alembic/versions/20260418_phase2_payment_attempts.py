"""Add payment attempts for Phase 2.

Revision ID: 20260418_phase2_payment_attempts
Revises: 20260418_phase2_orders_foundation
Create Date: 2026-04-18 10:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260418_phase2_payment_attempts"
down_revision: str | None = "20260418_phase2_orders_foundation"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=True),
        sa.Column("supersedes_attempt_id", sa.Uuid(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("sale_channel", sa.String(length=30), nullable=False, server_default="web"),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("displayed_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("wallet_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("gateway_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("external_reference", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("provider_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("request_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("terminal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supersedes_attempt_id"], ["payment_attempts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_id", name="uq_payment_attempts_payment_id"),
        sa.UniqueConstraint("order_id", "idempotency_key", name="uq_payment_attempts_order_idempotency_key"),
    )
    for column_name in (
        "order_id",
        "payment_id",
        "supersedes_attempt_id",
        "status",
        "external_reference",
        "idempotency_key",
    ):
        op.create_index(op.f(f"ix_payment_attempts_{column_name}"), "payment_attempts", [column_name], unique=False)


def downgrade() -> None:
    for column_name in (
        "idempotency_key",
        "external_reference",
        "status",
        "supersedes_attempt_id",
        "payment_id",
        "order_id",
    ):
        op.drop_index(op.f(f"ix_payment_attempts_{column_name}"), table_name="payment_attempts")
    op.drop_table("payment_attempts")
