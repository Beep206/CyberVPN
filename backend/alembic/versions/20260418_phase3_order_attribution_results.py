"""Phase 3 canonical order attribution results."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260418_phase3_order_attribution_results"
down_revision = "20260418_phase3_customer_commercial_bindings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_attribution_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("auth_realm_id", sa.Uuid(), nullable=False),
        sa.Column("storefront_id", sa.Uuid(), nullable=False),
        sa.Column("owner_type", sa.String(length=30), nullable=False),
        sa.Column("owner_source", sa.String(length=40), nullable=True),
        sa.Column("partner_account_id", sa.Uuid(), nullable=True),
        sa.Column("partner_code_id", sa.Uuid(), nullable=True),
        sa.Column("winning_touchpoint_id", sa.Uuid(), nullable=True),
        sa.Column("winning_binding_id", sa.Uuid(), nullable=True),
        sa.Column("rule_path", sa.JSON(), nullable=False),
        sa.Column("evidence_snapshot", sa.JSON(), nullable=False),
        sa.Column("explainability_snapshot", sa.JSON(), nullable=False),
        sa.Column("policy_snapshot", sa.JSON(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_code_id"], ["partner_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winning_binding_id"], ["customer_commercial_bindings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["winning_touchpoint_id"], ["attribution_touchpoints.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index(
        "ix_order_attribution_results_order_id",
        "order_attribution_results",
        ["order_id"],
        unique=True,
    )
    op.create_index("ix_order_attribution_results_user_id", "order_attribution_results", ["user_id"])
    op.create_index("ix_order_attribution_results_auth_realm_id", "order_attribution_results", ["auth_realm_id"])
    op.create_index("ix_order_attribution_results_storefront_id", "order_attribution_results", ["storefront_id"])
    op.create_index("ix_order_attribution_results_owner_type", "order_attribution_results", ["owner_type"])
    op.create_index("ix_order_attribution_results_owner_source", "order_attribution_results", ["owner_source"])
    op.create_index(
        "ix_order_attribution_results_partner_account_id",
        "order_attribution_results",
        ["partner_account_id"],
    )
    op.create_index(
        "ix_order_attribution_results_partner_code_id",
        "order_attribution_results",
        ["partner_code_id"],
    )
    op.create_index(
        "ix_order_attribution_results_winning_touchpoint_id",
        "order_attribution_results",
        ["winning_touchpoint_id"],
    )
    op.create_index(
        "ix_order_attribution_results_winning_binding_id",
        "order_attribution_results",
        ["winning_binding_id"],
    )
    op.create_index("ix_order_attribution_results_resolved_at", "order_attribution_results", ["resolved_at"])


def downgrade() -> None:
    op.drop_index("ix_order_attribution_results_resolved_at", table_name="order_attribution_results")
    op.drop_index("ix_order_attribution_results_winning_binding_id", table_name="order_attribution_results")
    op.drop_index("ix_order_attribution_results_winning_touchpoint_id", table_name="order_attribution_results")
    op.drop_index("ix_order_attribution_results_partner_code_id", table_name="order_attribution_results")
    op.drop_index("ix_order_attribution_results_partner_account_id", table_name="order_attribution_results")
    op.drop_index("ix_order_attribution_results_owner_source", table_name="order_attribution_results")
    op.drop_index("ix_order_attribution_results_owner_type", table_name="order_attribution_results")
    op.drop_index("ix_order_attribution_results_storefront_id", table_name="order_attribution_results")
    op.drop_index("ix_order_attribution_results_auth_realm_id", table_name="order_attribution_results")
    op.drop_index("ix_order_attribution_results_user_id", table_name="order_attribution_results")
    op.drop_index("ix_order_attribution_results_order_id", table_name="order_attribution_results")
    op.drop_table("order_attribution_results")
