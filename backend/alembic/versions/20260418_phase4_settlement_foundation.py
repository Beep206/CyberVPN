"""Phase 4 canonical settlement foundation."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260418_phase4_settlement_foundation"
down_revision = "20260418_phase3_renewal_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "earning_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=True),
        sa.Column("partner_user_id", sa.Uuid(), nullable=False),
        sa.Column("client_user_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=True),
        sa.Column("partner_code_id", sa.Uuid(), nullable=True),
        sa.Column("legacy_partner_earning_id", sa.Uuid(), nullable=True),
        sa.Column("order_attribution_result_id", sa.Uuid(), nullable=True),
        sa.Column("owner_type", sa.String(length=30), nullable=False),
        sa.Column("event_status", sa.String(length=20), nullable=False, server_default="on_hold"),
        sa.Column("commission_base_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("markup_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("commission_pct", sa.Numeric(8, 2), nullable=False),
        sa.Column("commission_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["legacy_partner_earning_id"], ["partner_earnings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_attribution_result_id"], ["order_attribution_results.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_code_id"], ["partner_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_earning_events_partner_account_id", "earning_events", ["partner_account_id"])
    op.create_index("ix_earning_events_partner_user_id", "earning_events", ["partner_user_id"])
    op.create_index("ix_earning_events_client_user_id", "earning_events", ["client_user_id"])
    op.create_index("ix_earning_events_order_id", "earning_events", ["order_id"], unique=True)
    op.create_index("ix_earning_events_payment_id", "earning_events", ["payment_id"])
    op.create_index("ix_earning_events_partner_code_id", "earning_events", ["partner_code_id"])
    op.create_index("ix_earning_events_legacy_partner_earning_id", "earning_events", ["legacy_partner_earning_id"])
    op.create_index(
        "ix_earning_events_order_attribution_result_id",
        "earning_events",
        ["order_attribution_result_id"],
    )
    op.create_index("ix_earning_events_owner_type", "earning_events", ["owner_type"])
    op.create_index("ix_earning_events_event_status", "earning_events", ["event_status"])
    op.create_index("ix_earning_events_available_at", "earning_events", ["available_at"])

    op.create_table(
        "earning_holds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("earning_event_id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=True),
        sa.Column("hold_reason_type", sa.String(length=30), nullable=False),
        sa.Column("hold_status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("hold_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("hold_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["earning_event_id"], ["earning_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["released_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_earning_holds_earning_event_id", "earning_holds", ["earning_event_id"])
    op.create_index("ix_earning_holds_partner_account_id", "earning_holds", ["partner_account_id"])
    op.create_index("ix_earning_holds_hold_reason_type", "earning_holds", ["hold_reason_type"])
    op.create_index("ix_earning_holds_hold_status", "earning_holds", ["hold_status"])
    op.create_index("ix_earning_holds_hold_until", "earning_holds", ["hold_until"])
    op.create_index("ix_earning_holds_released_at", "earning_holds", ["released_at"])
    op.create_index(
        "ix_earning_holds_released_by_admin_user_id",
        "earning_holds",
        ["released_by_admin_user_id"],
    )
    op.create_index(
        "ix_earning_holds_created_by_admin_user_id",
        "earning_holds",
        ["created_by_admin_user_id"],
    )

    op.create_table(
        "reserves",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("source_earning_event_id", sa.Uuid(), nullable=True),
        sa.Column("reserve_scope", sa.String(length=30), nullable=False),
        sa.Column("reserve_reason_type", sa.String(length=30), nullable=False),
        sa.Column("reserve_status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("reserve_payload", sa.JSON(), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["released_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_earning_event_id"], ["earning_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reserves_partner_account_id", "reserves", ["partner_account_id"])
    op.create_index("ix_reserves_source_earning_event_id", "reserves", ["source_earning_event_id"])
    op.create_index("ix_reserves_reserve_scope", "reserves", ["reserve_scope"])
    op.create_index("ix_reserves_reserve_reason_type", "reserves", ["reserve_reason_type"])
    op.create_index("ix_reserves_reserve_status", "reserves", ["reserve_status"])
    op.create_index("ix_reserves_released_at", "reserves", ["released_at"])
    op.create_index("ix_reserves_released_by_admin_user_id", "reserves", ["released_by_admin_user_id"])
    op.create_index("ix_reserves_created_by_admin_user_id", "reserves", ["created_by_admin_user_id"])


def downgrade() -> None:
    op.drop_index("ix_reserves_created_by_admin_user_id", table_name="reserves")
    op.drop_index("ix_reserves_released_by_admin_user_id", table_name="reserves")
    op.drop_index("ix_reserves_released_at", table_name="reserves")
    op.drop_index("ix_reserves_reserve_status", table_name="reserves")
    op.drop_index("ix_reserves_reserve_reason_type", table_name="reserves")
    op.drop_index("ix_reserves_reserve_scope", table_name="reserves")
    op.drop_index("ix_reserves_source_earning_event_id", table_name="reserves")
    op.drop_index("ix_reserves_partner_account_id", table_name="reserves")
    op.drop_table("reserves")

    op.drop_index("ix_earning_holds_created_by_admin_user_id", table_name="earning_holds")
    op.drop_index("ix_earning_holds_released_by_admin_user_id", table_name="earning_holds")
    op.drop_index("ix_earning_holds_released_at", table_name="earning_holds")
    op.drop_index("ix_earning_holds_hold_until", table_name="earning_holds")
    op.drop_index("ix_earning_holds_hold_status", table_name="earning_holds")
    op.drop_index("ix_earning_holds_hold_reason_type", table_name="earning_holds")
    op.drop_index("ix_earning_holds_partner_account_id", table_name="earning_holds")
    op.drop_index("ix_earning_holds_earning_event_id", table_name="earning_holds")
    op.drop_table("earning_holds")

    op.drop_index("ix_earning_events_available_at", table_name="earning_events")
    op.drop_index("ix_earning_events_event_status", table_name="earning_events")
    op.drop_index("ix_earning_events_owner_type", table_name="earning_events")
    op.drop_index("ix_earning_events_order_attribution_result_id", table_name="earning_events")
    op.drop_index("ix_earning_events_legacy_partner_earning_id", table_name="earning_events")
    op.drop_index("ix_earning_events_partner_code_id", table_name="earning_events")
    op.drop_index("ix_earning_events_payment_id", table_name="earning_events")
    op.drop_index("ix_earning_events_order_id", table_name="earning_events")
    op.drop_index("ix_earning_events_client_user_id", table_name="earning_events")
    op.drop_index("ix_earning_events_partner_user_id", table_name="earning_events")
    op.drop_index("ix_earning_events_partner_account_id", table_name="earning_events")
    op.drop_table("earning_events")
