"""Phase 5 entitlement grants."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260418_phase5_entitlement_grants"
down_revision = "20260418_phase5_service_identity_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entitlement_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("grant_key", sa.String(length=160), nullable=False),
        sa.Column("service_identity_id", sa.Uuid(), nullable=False),
        sa.Column("customer_account_id", sa.Uuid(), nullable=False),
        sa.Column("auth_realm_id", sa.Uuid(), nullable=False),
        sa.Column("origin_storefront_id", sa.Uuid(), nullable=True),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_order_id", sa.Uuid(), nullable=True),
        sa.Column("source_growth_reward_allocation_id", sa.Uuid(), nullable=True),
        sa.Column("source_renewal_order_id", sa.Uuid(), nullable=True),
        sa.Column("manual_source_key", sa.String(length=160), nullable=True),
        sa.Column("grant_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("grant_snapshot", sa.JSON(), nullable=False),
        sa.Column("source_snapshot", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("suspension_reason_code", sa.String(length=80), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("revoke_reason_code", sa.String(length=80), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("expiry_reason_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["service_identity_id"], ["service_identities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_account_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["origin_storefront_id"], ["storefronts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["source_growth_reward_allocation_id"],
            ["growth_reward_allocations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["source_renewal_order_id"], ["renewal_orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["activated_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suspended_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["revoked_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["expired_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grant_key"),
        sa.UniqueConstraint("source_order_id"),
        sa.UniqueConstraint("source_growth_reward_allocation_id"),
        sa.UniqueConstraint("source_renewal_order_id"),
        sa.UniqueConstraint("manual_source_key"),
    )
    op.create_index("ix_entitlement_grants_grant_key", "entitlement_grants", ["grant_key"], unique=True)
    op.create_index(
        "ix_entitlement_grants_service_identity_id",
        "entitlement_grants",
        ["service_identity_id"],
    )
    op.create_index(
        "ix_entitlement_grants_customer_account_id",
        "entitlement_grants",
        ["customer_account_id"],
    )
    op.create_index("ix_entitlement_grants_auth_realm_id", "entitlement_grants", ["auth_realm_id"])
    op.create_index(
        "ix_entitlement_grants_origin_storefront_id",
        "entitlement_grants",
        ["origin_storefront_id"],
    )
    op.create_index("ix_entitlement_grants_source_type", "entitlement_grants", ["source_type"])
    op.create_index("ix_entitlement_grants_source_order_id", "entitlement_grants", ["source_order_id"], unique=True)
    op.create_index(
        "ix_entitlement_grants_source_growth_reward_allocation_id",
        "entitlement_grants",
        ["source_growth_reward_allocation_id"],
        unique=True,
    )
    op.create_index(
        "ix_entitlement_grants_source_renewal_order_id",
        "entitlement_grants",
        ["source_renewal_order_id"],
        unique=True,
    )
    op.create_index(
        "ix_entitlement_grants_manual_source_key",
        "entitlement_grants",
        ["manual_source_key"],
        unique=True,
    )
    op.create_index("ix_entitlement_grants_grant_status", "entitlement_grants", ["grant_status"])
    op.create_index("ix_entitlement_grants_effective_from", "entitlement_grants", ["effective_from"])
    op.create_index("ix_entitlement_grants_expires_at", "entitlement_grants", ["expires_at"])
    op.create_index(
        "ix_entitlement_grants_created_by_admin_user_id",
        "entitlement_grants",
        ["created_by_admin_user_id"],
    )
    op.create_index("ix_entitlement_grants_activated_at", "entitlement_grants", ["activated_at"])
    op.create_index(
        "ix_entitlement_grants_activated_by_admin_user_id",
        "entitlement_grants",
        ["activated_by_admin_user_id"],
    )
    op.create_index("ix_entitlement_grants_suspended_at", "entitlement_grants", ["suspended_at"])
    op.create_index(
        "ix_entitlement_grants_suspended_by_admin_user_id",
        "entitlement_grants",
        ["suspended_by_admin_user_id"],
    )
    op.create_index("ix_entitlement_grants_revoked_at", "entitlement_grants", ["revoked_at"])
    op.create_index(
        "ix_entitlement_grants_revoked_by_admin_user_id",
        "entitlement_grants",
        ["revoked_by_admin_user_id"],
    )
    op.create_index("ix_entitlement_grants_expired_at", "entitlement_grants", ["expired_at"])
    op.create_index(
        "ix_entitlement_grants_expired_by_admin_user_id",
        "entitlement_grants",
        ["expired_by_admin_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_entitlement_grants_expired_by_admin_user_id", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_expired_at", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_revoked_by_admin_user_id", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_revoked_at", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_suspended_by_admin_user_id", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_suspended_at", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_activated_by_admin_user_id", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_activated_at", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_created_by_admin_user_id", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_expires_at", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_effective_from", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_grant_status", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_manual_source_key", table_name="entitlement_grants")
    op.drop_index(
        "ix_entitlement_grants_source_renewal_order_id",
        table_name="entitlement_grants",
    )
    op.drop_index(
        "ix_entitlement_grants_source_growth_reward_allocation_id",
        table_name="entitlement_grants",
    )
    op.drop_index("ix_entitlement_grants_source_order_id", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_source_type", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_origin_storefront_id", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_auth_realm_id", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_customer_account_id", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_service_identity_id", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_grant_key", table_name="entitlement_grants")
    op.drop_table("entitlement_grants")
