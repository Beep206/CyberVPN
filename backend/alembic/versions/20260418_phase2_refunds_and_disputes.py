"""Add refunds and canonical payment disputes for Phase 2.

Revision ID: 20260418_phase2_refunds_and_disputes
Revises: 20260418_phase2_payment_attempts
Create Date: 2026-04-18 13:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260418_phase2_refunds_and_disputes"
down_revision: str | None = "20260418_phase2_payment_attempts"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "refunds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("payment_attempt_id", sa.Uuid(), nullable=True),
        sa.Column("payment_id", sa.Uuid(), nullable=True),
        sa.Column("refund_status", sa.String(length=20), nullable=False, server_default="requested"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("provider", sa.String(length=30), nullable=True),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("reason_text", sa.String(length=500), nullable=True),
        sa.Column("external_reference", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("provider_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("request_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payment_attempt_id"], ["payment_attempts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "idempotency_key", name="uq_refunds_order_idempotency_key"),
    )
    for column_name in (
        "order_id",
        "payment_attempt_id",
        "payment_id",
        "refund_status",
        "provider",
        "reason_code",
        "external_reference",
        "idempotency_key",
    ):
        op.create_index(op.f(f"ix_refunds_{column_name}"), "refunds", [column_name], unique=False)

    op.create_table(
        "payment_disputes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("payment_attempt_id", sa.Uuid(), nullable=True),
        sa.Column("payment_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(length=30), nullable=True),
        sa.Column("external_reference", sa.String(length=255), nullable=True),
        sa.Column("subtype", sa.String(length=40), nullable=False),
        sa.Column("outcome_class", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("lifecycle_status", sa.String(length=40), nullable=False, server_default="opened"),
        sa.Column("disputed_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("fee_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("fee_status", sa.String(length=40), nullable=False, server_default="none"),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("evidence_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("provider_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payment_attempt_id"], ["payment_attempts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column_name in (
        "order_id",
        "payment_attempt_id",
        "payment_id",
        "provider",
        "external_reference",
        "subtype",
        "outcome_class",
        "lifecycle_status",
        "reason_code",
    ):
        op.create_index(
            op.f(f"ix_payment_disputes_{column_name}"),
            "payment_disputes",
            [column_name],
            unique=False,
        )


def downgrade() -> None:
    for column_name in (
        "reason_code",
        "lifecycle_status",
        "outcome_class",
        "subtype",
        "external_reference",
        "provider",
        "payment_id",
        "payment_attempt_id",
        "order_id",
    ):
        op.drop_index(op.f(f"ix_payment_disputes_{column_name}"), table_name="payment_disputes")
    op.drop_table("payment_disputes")

    for column_name in (
        "idempotency_key",
        "external_reference",
        "reason_code",
        "provider",
        "refund_status",
        "payment_id",
        "payment_attempt_id",
        "order_id",
    ):
        op.drop_index(op.f(f"ix_refunds_{column_name}"), table_name="refunds")
    op.drop_table("refunds")
