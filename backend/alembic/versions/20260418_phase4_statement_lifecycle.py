"""Phase 4 settlement periods and partner statements."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260418_phase4_statement_lifecycle"
down_revision = "20260418_phase4_settlement_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "settlement_periods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("period_key", sa.String(length=80), nullable=False),
        sa.Column("period_status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopened_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["closed_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reopened_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("partner_account_id", "period_key", name="uq_settlement_period_partner_key"),
    )
    op.create_index("ix_settlement_periods_partner_account_id", "settlement_periods", ["partner_account_id"])
    op.create_index("ix_settlement_periods_period_key", "settlement_periods", ["period_key"])
    op.create_index("ix_settlement_periods_window_start", "settlement_periods", ["window_start"])
    op.create_index("ix_settlement_periods_window_end", "settlement_periods", ["window_end"])
    op.create_index("ix_settlement_periods_closed_at", "settlement_periods", ["closed_at"])
    op.create_index(
        "ix_settlement_periods_closed_by_admin_user_id",
        "settlement_periods",
        ["closed_by_admin_user_id"],
    )
    op.create_index("ix_settlement_periods_reopened_at", "settlement_periods", ["reopened_at"])
    op.create_index(
        "ix_settlement_periods_reopened_by_admin_user_id",
        "settlement_periods",
        ["reopened_by_admin_user_id"],
    )

    op.create_table(
        "partner_statements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("settlement_period_id", sa.Uuid(), nullable=False),
        sa.Column("statement_key", sa.String(length=120), nullable=False),
        sa.Column("statement_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("statement_status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("reopened_from_statement_id", sa.Uuid(), nullable=True),
        sa.Column("superseded_by_statement_id", sa.Uuid(), nullable=True),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("accrual_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("on_hold_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("reserve_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("adjustment_net_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("available_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("source_event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("held_event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_reserve_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("adjustment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("statement_snapshot", sa.JSON(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["closed_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reopened_from_statement_id"], ["partner_statements.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_period_id"], ["settlement_periods.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["superseded_by_statement_id"], ["partner_statements.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("statement_key"),
        sa.UniqueConstraint(
            "partner_account_id",
            "settlement_period_id",
            "statement_version",
            name="uq_partner_statement_period_version",
        ),
    )
    op.create_index("ix_partner_statements_partner_account_id", "partner_statements", ["partner_account_id"])
    op.create_index("ix_partner_statements_settlement_period_id", "partner_statements", ["settlement_period_id"])
    op.create_index("ix_partner_statements_statement_key", "partner_statements", ["statement_key"], unique=True)
    op.create_index("ix_partner_statements_closed_at", "partner_statements", ["closed_at"])
    op.create_index(
        "ix_partner_statements_closed_by_admin_user_id",
        "partner_statements",
        ["closed_by_admin_user_id"],
    )
    op.create_index(
        "ix_partner_statements_reopened_from_statement_id",
        "partner_statements",
        ["reopened_from_statement_id"],
    )
    op.create_index(
        "ix_partner_statements_superseded_by_statement_id",
        "partner_statements",
        ["superseded_by_statement_id"],
    )

    op.create_table(
        "statement_adjustments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_statement_id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("source_reference_type", sa.String(length=40), nullable=True),
        sa.Column("source_reference_id", sa.Uuid(), nullable=True),
        sa.Column("carried_from_adjustment_id", sa.Uuid(), nullable=True),
        sa.Column("adjustment_type", sa.String(length=40), nullable=False),
        sa.Column("adjustment_direction", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("adjustment_payload", sa.JSON(), nullable=False),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["carried_from_adjustment_id"], ["statement_adjustments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_statement_id"], ["partner_statements.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_statement_adjustments_partner_statement_id",
        "statement_adjustments",
        ["partner_statement_id"],
    )
    op.create_index(
        "ix_statement_adjustments_partner_account_id",
        "statement_adjustments",
        ["partner_account_id"],
    )
    op.create_index(
        "ix_statement_adjustments_source_reference_type",
        "statement_adjustments",
        ["source_reference_type"],
    )
    op.create_index(
        "ix_statement_adjustments_source_reference_id",
        "statement_adjustments",
        ["source_reference_id"],
    )
    op.create_index(
        "ix_statement_adjustments_carried_from_adjustment_id",
        "statement_adjustments",
        ["carried_from_adjustment_id"],
    )
    op.create_index("ix_statement_adjustments_adjustment_type", "statement_adjustments", ["adjustment_type"])
    op.create_index(
        "ix_statement_adjustments_created_by_admin_user_id",
        "statement_adjustments",
        ["created_by_admin_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_statement_adjustments_created_by_admin_user_id", table_name="statement_adjustments")
    op.drop_index("ix_statement_adjustments_adjustment_type", table_name="statement_adjustments")
    op.drop_index(
        "ix_statement_adjustments_carried_from_adjustment_id",
        table_name="statement_adjustments",
    )
    op.drop_index("ix_statement_adjustments_source_reference_id", table_name="statement_adjustments")
    op.drop_index("ix_statement_adjustments_source_reference_type", table_name="statement_adjustments")
    op.drop_index("ix_statement_adjustments_partner_account_id", table_name="statement_adjustments")
    op.drop_index("ix_statement_adjustments_partner_statement_id", table_name="statement_adjustments")
    op.drop_table("statement_adjustments")

    op.drop_index(
        "ix_partner_statements_superseded_by_statement_id",
        table_name="partner_statements",
    )
    op.drop_index(
        "ix_partner_statements_reopened_from_statement_id",
        table_name="partner_statements",
    )
    op.drop_index(
        "ix_partner_statements_closed_by_admin_user_id",
        table_name="partner_statements",
    )
    op.drop_index("ix_partner_statements_closed_at", table_name="partner_statements")
    op.drop_index("ix_partner_statements_statement_key", table_name="partner_statements")
    op.drop_index("ix_partner_statements_settlement_period_id", table_name="partner_statements")
    op.drop_index("ix_partner_statements_partner_account_id", table_name="partner_statements")
    op.drop_table("partner_statements")

    op.drop_index(
        "ix_settlement_periods_reopened_by_admin_user_id",
        table_name="settlement_periods",
    )
    op.drop_index("ix_settlement_periods_reopened_at", table_name="settlement_periods")
    op.drop_index(
        "ix_settlement_periods_closed_by_admin_user_id",
        table_name="settlement_periods",
    )
    op.drop_index("ix_settlement_periods_closed_at", table_name="settlement_periods")
    op.drop_index("ix_settlement_periods_window_end", table_name="settlement_periods")
    op.drop_index("ix_settlement_periods_window_start", table_name="settlement_periods")
    op.drop_index("ix_settlement_periods_period_key", table_name="settlement_periods")
    op.drop_index("ix_settlement_periods_partner_account_id", table_name="settlement_periods")
    op.drop_table("settlement_periods")
