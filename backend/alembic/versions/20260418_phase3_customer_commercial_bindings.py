"""Add customer commercial bindings for Phase 3.

Revision ID: 20260418_phase3_customer_commercial_bindings
Revises: 20260418_phase3_attribution_touchpoints
Create Date: 2026-04-18 20:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260418_phase3_customer_commercial_bindings"
down_revision: str | None = "20260418_phase3_attribution_touchpoints"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_commercial_bindings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("auth_realm_id", sa.Uuid(), nullable=False),
        sa.Column("storefront_id", sa.Uuid(), nullable=True),
        sa.Column("binding_type", sa.String(length=40), nullable=False),
        sa.Column("binding_status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("owner_type", sa.String(length=30), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=True),
        sa.Column("partner_code_id", sa.Uuid(), nullable=True),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("evidence_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_code_id"], ["partner_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_customer_commercial_bindings_user_id"),
        "customer_commercial_bindings",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_customer_commercial_bindings_auth_realm_id"),
        "customer_commercial_bindings",
        ["auth_realm_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_customer_commercial_bindings_storefront_id"),
        "customer_commercial_bindings",
        ["storefront_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_customer_commercial_bindings_binding_type"),
        "customer_commercial_bindings",
        ["binding_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_customer_commercial_bindings_binding_status"),
        "customer_commercial_bindings",
        ["binding_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_customer_commercial_bindings_owner_type"),
        "customer_commercial_bindings",
        ["owner_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_customer_commercial_bindings_partner_account_id"),
        "customer_commercial_bindings",
        ["partner_account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_customer_commercial_bindings_partner_code_id"),
        "customer_commercial_bindings",
        ["partner_code_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_customer_commercial_bindings_created_by_admin_user_id"),
        "customer_commercial_bindings",
        ["created_by_admin_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_customer_commercial_bindings_effective_from"),
        "customer_commercial_bindings",
        ["effective_from"],
        unique=False,
    )
    op.create_index(
        op.f("ix_customer_commercial_bindings_effective_to"),
        "customer_commercial_bindings",
        ["effective_to"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_customer_commercial_bindings_effective_to"), table_name="customer_commercial_bindings")
    op.drop_index(op.f("ix_customer_commercial_bindings_effective_from"), table_name="customer_commercial_bindings")
    op.drop_index(
        op.f("ix_customer_commercial_bindings_created_by_admin_user_id"),
        table_name="customer_commercial_bindings",
    )
    op.drop_index(op.f("ix_customer_commercial_bindings_partner_code_id"), table_name="customer_commercial_bindings")
    op.drop_index(
        op.f("ix_customer_commercial_bindings_partner_account_id"),
        table_name="customer_commercial_bindings",
    )
    op.drop_index(op.f("ix_customer_commercial_bindings_owner_type"), table_name="customer_commercial_bindings")
    op.drop_index(op.f("ix_customer_commercial_bindings_binding_status"), table_name="customer_commercial_bindings")
    op.drop_index(op.f("ix_customer_commercial_bindings_binding_type"), table_name="customer_commercial_bindings")
    op.drop_index(op.f("ix_customer_commercial_bindings_storefront_id"), table_name="customer_commercial_bindings")
    op.drop_index(op.f("ix_customer_commercial_bindings_auth_realm_id"), table_name="customer_commercial_bindings")
    op.drop_index(op.f("ix_customer_commercial_bindings_user_id"), table_name="customer_commercial_bindings")
    op.drop_table("customer_commercial_bindings")
