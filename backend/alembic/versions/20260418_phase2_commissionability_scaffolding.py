"""Add commissionability evaluations for Phase 2.

Revision ID: 20260418_phase2_commissionability_scaffolding
Revises: 20260418_phase2_refunds_and_disputes
Create Date: 2026-04-18 14:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260418_phase2_commissionability_scaffolding"
down_revision: str | None = "20260418_phase2_refunds_and_disputes"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "commissionability_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("commissionability_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("reason_codes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("partner_context_present", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("program_allows_commissionability", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("positive_commission_base", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("paid_status", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("fully_refunded", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("open_payment_dispute_present", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("risk_allowed", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("evaluation_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("explainability_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_commissionability_evaluations_order_id"),
    )
    op.create_index(
        op.f("ix_commissionability_evaluations_order_id"),
        "commissionability_evaluations",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commissionability_evaluations_commissionability_status"),
        "commissionability_evaluations",
        ["commissionability_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_commissionability_evaluations_commissionability_status"),
        table_name="commissionability_evaluations",
    )
    op.drop_index(op.f("ix_commissionability_evaluations_order_id"), table_name="commissionability_evaluations")
    op.drop_table("commissionability_evaluations")
