"""Phase 4 partner payout accounts."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260418_phase4_partner_payout_accounts"
down_revision = "20260418_phase4_statement_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partner_payout_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("settlement_profile_id", sa.Uuid(), nullable=True),
        sa.Column("payout_rail", sa.String(length=40), nullable=False),
        sa.Column("display_label", sa.String(length=120), nullable=False),
        sa.Column("destination_reference", sa.String(length=255), nullable=False),
        sa.Column("masked_destination", sa.String(length=255), nullable=False),
        sa.Column("destination_metadata", sa.JSON(), nullable=False),
        sa.Column("verification_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("approval_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("account_status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("verified_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspension_reason_code", sa.String(length=80), nullable=True),
        sa.Column("archived_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archive_reason_code", sa.String(length=80), nullable=True),
        sa.Column("default_selected_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("default_selected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["verified_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suspended_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["archived_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["default_selected_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_partner_payout_accounts_partner_account_id",
        "partner_payout_accounts",
        ["partner_account_id"],
    )
    op.create_index(
        "ix_partner_payout_accounts_settlement_profile_id",
        "partner_payout_accounts",
        ["settlement_profile_id"],
    )
    op.create_index("ix_partner_payout_accounts_payout_rail", "partner_payout_accounts", ["payout_rail"])
    op.create_index(
        "ix_partner_payout_accounts_verification_status",
        "partner_payout_accounts",
        ["verification_status"],
    )
    op.create_index(
        "ix_partner_payout_accounts_approval_status",
        "partner_payout_accounts",
        ["approval_status"],
    )
    op.create_index(
        "ix_partner_payout_accounts_account_status",
        "partner_payout_accounts",
        ["account_status"],
    )
    op.create_index(
        "ix_partner_payout_accounts_created_by_admin_user_id",
        "partner_payout_accounts",
        ["created_by_admin_user_id"],
    )
    op.create_index(
        "ix_partner_payout_accounts_verified_by_admin_user_id",
        "partner_payout_accounts",
        ["verified_by_admin_user_id"],
    )
    op.create_index("ix_partner_payout_accounts_verified_at", "partner_payout_accounts", ["verified_at"])
    op.create_index(
        "ix_partner_payout_accounts_approved_by_admin_user_id",
        "partner_payout_accounts",
        ["approved_by_admin_user_id"],
    )
    op.create_index("ix_partner_payout_accounts_approved_at", "partner_payout_accounts", ["approved_at"])
    op.create_index(
        "ix_partner_payout_accounts_suspended_by_admin_user_id",
        "partner_payout_accounts",
        ["suspended_by_admin_user_id"],
    )
    op.create_index("ix_partner_payout_accounts_suspended_at", "partner_payout_accounts", ["suspended_at"])
    op.create_index(
        "ix_partner_payout_accounts_archived_by_admin_user_id",
        "partner_payout_accounts",
        ["archived_by_admin_user_id"],
    )
    op.create_index("ix_partner_payout_accounts_archived_at", "partner_payout_accounts", ["archived_at"])
    op.create_index(
        "ix_partner_payout_accounts_default_selected_by_admin_user_id",
        "partner_payout_accounts",
        ["default_selected_by_admin_user_id"],
    )
    op.create_index(
        "ix_partner_payout_accounts_default_selected_at",
        "partner_payout_accounts",
        ["default_selected_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_partner_payout_accounts_default_selected_at",
        table_name="partner_payout_accounts",
    )
    op.drop_index(
        "ix_partner_payout_accounts_default_selected_by_admin_user_id",
        table_name="partner_payout_accounts",
    )
    op.drop_index("ix_partner_payout_accounts_archived_at", table_name="partner_payout_accounts")
    op.drop_index(
        "ix_partner_payout_accounts_archived_by_admin_user_id",
        table_name="partner_payout_accounts",
    )
    op.drop_index("ix_partner_payout_accounts_suspended_at", table_name="partner_payout_accounts")
    op.drop_index(
        "ix_partner_payout_accounts_suspended_by_admin_user_id",
        table_name="partner_payout_accounts",
    )
    op.drop_index("ix_partner_payout_accounts_approved_at", table_name="partner_payout_accounts")
    op.drop_index(
        "ix_partner_payout_accounts_approved_by_admin_user_id",
        table_name="partner_payout_accounts",
    )
    op.drop_index("ix_partner_payout_accounts_verified_at", table_name="partner_payout_accounts")
    op.drop_index(
        "ix_partner_payout_accounts_verified_by_admin_user_id",
        table_name="partner_payout_accounts",
    )
    op.drop_index(
        "ix_partner_payout_accounts_created_by_admin_user_id",
        table_name="partner_payout_accounts",
    )
    op.drop_index("ix_partner_payout_accounts_account_status", table_name="partner_payout_accounts")
    op.drop_index("ix_partner_payout_accounts_approval_status", table_name="partner_payout_accounts")
    op.drop_index("ix_partner_payout_accounts_verification_status", table_name="partner_payout_accounts")
    op.drop_index("ix_partner_payout_accounts_payout_rail", table_name="partner_payout_accounts")
    op.drop_index(
        "ix_partner_payout_accounts_settlement_profile_id",
        table_name="partner_payout_accounts",
    )
    op.drop_index(
        "ix_partner_payout_accounts_partner_account_id",
        table_name="partner_payout_accounts",
    )
    op.drop_table("partner_payout_accounts")
