"""Phase 3 canonical renewal orders."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260418_phase3_renewal_orders"
down_revision = "20260418_phase3_growth_reward_allocations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "renewal_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("initial_order_id", sa.Uuid(), nullable=False),
        sa.Column("prior_order_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("auth_realm_id", sa.Uuid(), nullable=False),
        sa.Column("storefront_id", sa.Uuid(), nullable=False),
        sa.Column("originating_attribution_result_id", sa.Uuid(), nullable=True),
        sa.Column("winning_binding_id", sa.Uuid(), nullable=True),
        sa.Column("renewal_sequence_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("renewal_mode", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("provenance_owner_type", sa.String(length=30), nullable=False, server_default="none"),
        sa.Column("provenance_owner_source", sa.String(length=40), nullable=True),
        sa.Column("provenance_partner_account_id", sa.Uuid(), nullable=True),
        sa.Column("provenance_partner_code_id", sa.Uuid(), nullable=True),
        sa.Column("effective_owner_type", sa.String(length=30), nullable=False, server_default="none"),
        sa.Column("effective_owner_source", sa.String(length=40), nullable=True),
        sa.Column("effective_partner_account_id", sa.Uuid(), nullable=True),
        sa.Column("effective_partner_code_id", sa.Uuid(), nullable=True),
        sa.Column("payout_eligible", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("payout_block_reason_codes", sa.JSON(), nullable=False),
        sa.Column("lineage_snapshot", sa.JSON(), nullable=False),
        sa.Column("explainability_snapshot", sa.JSON(), nullable=False),
        sa.Column("policy_snapshot", sa.JSON(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["effective_partner_account_id"], ["partner_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["effective_partner_code_id"], ["partner_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["initial_order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["originating_attribution_result_id"],
            ["order_attribution_results.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prior_order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["provenance_partner_account_id"], ["partner_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["provenance_partner_code_id"], ["partner_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winning_binding_id"], ["customer_commercial_bindings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_renewal_orders_order_id", "renewal_orders", ["order_id"], unique=True)
    op.create_index("ix_renewal_orders_initial_order_id", "renewal_orders", ["initial_order_id"])
    op.create_index("ix_renewal_orders_prior_order_id", "renewal_orders", ["prior_order_id"])
    op.create_index("ix_renewal_orders_user_id", "renewal_orders", ["user_id"])
    op.create_index("ix_renewal_orders_auth_realm_id", "renewal_orders", ["auth_realm_id"])
    op.create_index("ix_renewal_orders_storefront_id", "renewal_orders", ["storefront_id"])
    op.create_index(
        "ix_renewal_orders_originating_attribution_result_id",
        "renewal_orders",
        ["originating_attribution_result_id"],
    )
    op.create_index("ix_renewal_orders_winning_binding_id", "renewal_orders", ["winning_binding_id"])
    op.create_index("ix_renewal_orders_provenance_owner_type", "renewal_orders", ["provenance_owner_type"])
    op.create_index("ix_renewal_orders_provenance_owner_source", "renewal_orders", ["provenance_owner_source"])
    op.create_index(
        "ix_renewal_orders_provenance_partner_account_id",
        "renewal_orders",
        ["provenance_partner_account_id"],
    )
    op.create_index(
        "ix_renewal_orders_provenance_partner_code_id",
        "renewal_orders",
        ["provenance_partner_code_id"],
    )
    op.create_index("ix_renewal_orders_effective_owner_type", "renewal_orders", ["effective_owner_type"])
    op.create_index("ix_renewal_orders_effective_owner_source", "renewal_orders", ["effective_owner_source"])
    op.create_index(
        "ix_renewal_orders_effective_partner_account_id",
        "renewal_orders",
        ["effective_partner_account_id"],
    )
    op.create_index(
        "ix_renewal_orders_effective_partner_code_id",
        "renewal_orders",
        ["effective_partner_code_id"],
    )
    op.create_index("ix_renewal_orders_payout_eligible", "renewal_orders", ["payout_eligible"])
    op.create_index("ix_renewal_orders_resolved_at", "renewal_orders", ["resolved_at"])


def downgrade() -> None:
    op.drop_index("ix_renewal_orders_resolved_at", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_payout_eligible", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_effective_partner_code_id", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_effective_partner_account_id", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_effective_owner_source", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_effective_owner_type", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_provenance_partner_code_id", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_provenance_partner_account_id", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_provenance_owner_source", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_provenance_owner_type", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_winning_binding_id", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_originating_attribution_result_id", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_storefront_id", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_auth_realm_id", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_user_id", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_prior_order_id", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_initial_order_id", table_name="renewal_orders")
    op.drop_index("ix_renewal_orders_order_id", table_name="renewal_orders")
    op.drop_table("renewal_orders")
