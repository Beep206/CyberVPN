"""Phase 8 operational overlays."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260419_phase8_operational_overlays"
down_revision = "20260419_phase8_risk_governance_workflows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partner_traffic_declarations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("declaration_kind", sa.String(length=40), nullable=False),
        sa.Column("declaration_status", sa.String(length=30), nullable=False, server_default="submitted"),
        sa.Column("scope_label", sa.String(length=120), nullable=False),
        sa.Column("declaration_payload", sa.JSON(), nullable=False),
        sa.Column("notes_payload", sa.JSON(), nullable=False),
        sa.Column("submitted_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_partner_traffic_declarations_partner_account_id",
        "partner_traffic_declarations",
        ["partner_account_id"],
    )
    op.create_index(
        "ix_partner_traffic_declarations_declaration_kind",
        "partner_traffic_declarations",
        ["declaration_kind"],
    )
    op.create_index(
        "ix_partner_traffic_declarations_declaration_status",
        "partner_traffic_declarations",
        ["declaration_status"],
    )
    op.create_index(
        "ix_partner_traffic_declarations_submitted_by_admin_user_id",
        "partner_traffic_declarations",
        ["submitted_by_admin_user_id"],
    )
    op.create_index(
        "ix_partner_traffic_declarations_reviewed_by_admin_user_id",
        "partner_traffic_declarations",
        ["reviewed_by_admin_user_id"],
    )
    op.create_index(
        "ix_partner_traffic_declarations_reviewed_at",
        "partner_traffic_declarations",
        ["reviewed_at"],
    )

    op.create_table(
        "creative_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("approval_kind", sa.String(length=40), nullable=False),
        sa.Column("approval_status", sa.String(length=30), nullable=False, server_default="under_review"),
        sa.Column("scope_label", sa.String(length=120), nullable=False),
        sa.Column("creative_ref", sa.String(length=255), nullable=True),
        sa.Column("approval_payload", sa.JSON(), nullable=False),
        sa.Column("notes_payload", sa.JSON(), nullable=False),
        sa.Column("submitted_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_creative_approvals_partner_account_id", "creative_approvals", ["partner_account_id"])
    op.create_index("ix_creative_approvals_approval_kind", "creative_approvals", ["approval_kind"])
    op.create_index("ix_creative_approvals_approval_status", "creative_approvals", ["approval_status"])
    op.create_index("ix_creative_approvals_creative_ref", "creative_approvals", ["creative_ref"])
    op.create_index(
        "ix_creative_approvals_submitted_by_admin_user_id",
        "creative_approvals",
        ["submitted_by_admin_user_id"],
    )
    op.create_index(
        "ix_creative_approvals_reviewed_by_admin_user_id",
        "creative_approvals",
        ["reviewed_by_admin_user_id"],
    )
    op.create_index("ix_creative_approvals_reviewed_at", "creative_approvals", ["reviewed_at"])
    op.create_index("ix_creative_approvals_expires_at", "creative_approvals", ["expires_at"])

    op.create_table(
        "dispute_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("payment_dispute_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("case_kind", sa.String(length=40), nullable=False),
        sa.Column("case_status", sa.String(length=30), nullable=False, server_default="open"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("case_payload", sa.JSON(), nullable=False),
        sa.Column("notes_payload", sa.JSON(), nullable=False),
        sa.Column("opened_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_to_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("closed_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payment_dispute_id"], ["payment_disputes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opened_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["closed_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dispute_cases_partner_account_id", "dispute_cases", ["partner_account_id"])
    op.create_index("ix_dispute_cases_payment_dispute_id", "dispute_cases", ["payment_dispute_id"])
    op.create_index("ix_dispute_cases_order_id", "dispute_cases", ["order_id"])
    op.create_index("ix_dispute_cases_case_kind", "dispute_cases", ["case_kind"])
    op.create_index("ix_dispute_cases_case_status", "dispute_cases", ["case_status"])
    op.create_index(
        "ix_dispute_cases_opened_by_admin_user_id",
        "dispute_cases",
        ["opened_by_admin_user_id"],
    )
    op.create_index(
        "ix_dispute_cases_assigned_to_admin_user_id",
        "dispute_cases",
        ["assigned_to_admin_user_id"],
    )
    op.create_index(
        "ix_dispute_cases_closed_by_admin_user_id",
        "dispute_cases",
        ["closed_by_admin_user_id"],
    )
    op.create_index("ix_dispute_cases_closed_at", "dispute_cases", ["closed_at"])


def downgrade() -> None:
    op.drop_index("ix_dispute_cases_closed_at", table_name="dispute_cases")
    op.drop_index(
        "ix_dispute_cases_closed_by_admin_user_id",
        table_name="dispute_cases",
    )
    op.drop_index(
        "ix_dispute_cases_assigned_to_admin_user_id",
        table_name="dispute_cases",
    )
    op.drop_index(
        "ix_dispute_cases_opened_by_admin_user_id",
        table_name="dispute_cases",
    )
    op.drop_index("ix_dispute_cases_case_status", table_name="dispute_cases")
    op.drop_index("ix_dispute_cases_case_kind", table_name="dispute_cases")
    op.drop_index("ix_dispute_cases_order_id", table_name="dispute_cases")
    op.drop_index("ix_dispute_cases_payment_dispute_id", table_name="dispute_cases")
    op.drop_index("ix_dispute_cases_partner_account_id", table_name="dispute_cases")
    op.drop_table("dispute_cases")

    op.drop_index("ix_creative_approvals_expires_at", table_name="creative_approvals")
    op.drop_index("ix_creative_approvals_reviewed_at", table_name="creative_approvals")
    op.drop_index(
        "ix_creative_approvals_reviewed_by_admin_user_id",
        table_name="creative_approvals",
    )
    op.drop_index(
        "ix_creative_approvals_submitted_by_admin_user_id",
        table_name="creative_approvals",
    )
    op.drop_index("ix_creative_approvals_creative_ref", table_name="creative_approvals")
    op.drop_index("ix_creative_approvals_approval_status", table_name="creative_approvals")
    op.drop_index("ix_creative_approvals_approval_kind", table_name="creative_approvals")
    op.drop_index("ix_creative_approvals_partner_account_id", table_name="creative_approvals")
    op.drop_table("creative_approvals")

    op.drop_index(
        "ix_partner_traffic_declarations_reviewed_at",
        table_name="partner_traffic_declarations",
    )
    op.drop_index(
        "ix_partner_traffic_declarations_reviewed_by_admin_user_id",
        table_name="partner_traffic_declarations",
    )
    op.drop_index(
        "ix_partner_traffic_declarations_submitted_by_admin_user_id",
        table_name="partner_traffic_declarations",
    )
    op.drop_index(
        "ix_partner_traffic_declarations_declaration_status",
        table_name="partner_traffic_declarations",
    )
    op.drop_index(
        "ix_partner_traffic_declarations_declaration_kind",
        table_name="partner_traffic_declarations",
    )
    op.drop_index(
        "ix_partner_traffic_declarations_partner_account_id",
        table_name="partner_traffic_declarations",
    )
    op.drop_table("partner_traffic_declarations")
