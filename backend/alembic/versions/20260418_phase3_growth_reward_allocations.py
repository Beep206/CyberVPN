"""Phase 3 canonical growth reward allocations."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260418_phase3_growth_reward_allocations"
down_revision = "20260418_phase3_order_attribution_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "growth_reward_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reward_type", sa.String(length=40), nullable=False),
        sa.Column("allocation_status", sa.String(length=20), nullable=False),
        sa.Column("beneficiary_user_id", sa.Uuid(), nullable=False),
        sa.Column("auth_realm_id", sa.Uuid(), nullable=False),
        sa.Column("storefront_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("invite_code_id", sa.Uuid(), nullable=True),
        sa.Column("referral_commission_id", sa.Uuid(), nullable=True),
        sa.Column("source_key", sa.String(length=160), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("currency_code", sa.String(length=12), nullable=True),
        sa.Column("reward_payload", sa.JSON(), nullable=False),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("allocated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["beneficiary_user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invite_code_id"], ["invite_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["referral_commission_id"], ["referral_commissions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referral_commission_id"),
        sa.UniqueConstraint("source_key"),
    )
    op.create_index(
        "ix_growth_reward_allocations_reward_type",
        "growth_reward_allocations",
        ["reward_type"],
        unique=False,
    )
    op.create_index(
        "ix_growth_reward_allocations_allocation_status",
        "growth_reward_allocations",
        ["allocation_status"],
        unique=False,
    )
    op.create_index(
        "ix_growth_reward_allocations_beneficiary_user_id",
        "growth_reward_allocations",
        ["beneficiary_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_growth_reward_allocations_auth_realm_id",
        "growth_reward_allocations",
        ["auth_realm_id"],
        unique=False,
    )
    op.create_index(
        "ix_growth_reward_allocations_storefront_id",
        "growth_reward_allocations",
        ["storefront_id"],
        unique=False,
    )
    op.create_index(
        "ix_growth_reward_allocations_order_id",
        "growth_reward_allocations",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        "ix_growth_reward_allocations_invite_code_id",
        "growth_reward_allocations",
        ["invite_code_id"],
        unique=False,
    )
    op.create_index(
        "ix_growth_reward_allocations_referral_commission_id",
        "growth_reward_allocations",
        ["referral_commission_id"],
        unique=True,
    )
    op.create_index(
        "ix_growth_reward_allocations_source_key",
        "growth_reward_allocations",
        ["source_key"],
        unique=True,
    )
    op.create_index(
        "ix_growth_reward_allocations_created_by_admin_user_id",
        "growth_reward_allocations",
        ["created_by_admin_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_growth_reward_allocations_allocated_at",
        "growth_reward_allocations",
        ["allocated_at"],
        unique=False,
    )
    op.create_index(
        "ix_growth_reward_allocations_reversed_at",
        "growth_reward_allocations",
        ["reversed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_growth_reward_allocations_reversed_at", table_name="growth_reward_allocations")
    op.drop_index("ix_growth_reward_allocations_allocated_at", table_name="growth_reward_allocations")
    op.drop_index(
        "ix_growth_reward_allocations_created_by_admin_user_id",
        table_name="growth_reward_allocations",
    )
    op.drop_index("ix_growth_reward_allocations_source_key", table_name="growth_reward_allocations")
    op.drop_index(
        "ix_growth_reward_allocations_referral_commission_id",
        table_name="growth_reward_allocations",
    )
    op.drop_index("ix_growth_reward_allocations_invite_code_id", table_name="growth_reward_allocations")
    op.drop_index("ix_growth_reward_allocations_order_id", table_name="growth_reward_allocations")
    op.drop_index("ix_growth_reward_allocations_storefront_id", table_name="growth_reward_allocations")
    op.drop_index("ix_growth_reward_allocations_auth_realm_id", table_name="growth_reward_allocations")
    op.drop_index(
        "ix_growth_reward_allocations_beneficiary_user_id",
        table_name="growth_reward_allocations",
    )
    op.drop_index(
        "ix_growth_reward_allocations_allocation_status",
        table_name="growth_reward_allocations",
    )
    op.drop_index("ix_growth_reward_allocations_reward_type", table_name="growth_reward_allocations")
    op.drop_table("growth_reward_allocations")
