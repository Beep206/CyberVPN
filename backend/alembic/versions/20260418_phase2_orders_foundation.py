"""Add orders and order items for Phase 2.

Revision ID: 20260418_phase2_orders_foundation
Revises: 20260418_phase2_quote_checkout_sessions
Create Date: 2026-04-18 10:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260418_phase2_orders_foundation"
down_revision: str | None = "20260418_phase2_quote_checkout_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("checkout_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("auth_realm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storefront_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("merchant_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invoice_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("billing_descriptor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pricebook_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pricebook_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("legal_document_set_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("program_eligibility_policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subscription_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("promo_code_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("partner_code_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sale_channel", sa.String(length=30), nullable=False, server_default="web"),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("order_status", sa.String(length=20), nullable=False, server_default="committed"),
        sa.Column("settlement_status", sa.String(length=20), nullable=False, server_default="pending_payment"),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("addon_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("displayed_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("wallet_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("gateway_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("partner_markup", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("commission_base_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("merchant_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("pricing_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("policy_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("entitlements_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["billing_descriptor_id"], ["billing_descriptors.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["checkout_session_id"], ["checkout_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_profile_id"], ["invoice_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["legal_document_set_id"], ["storefront_legal_doc_sets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["merchant_profile_id"], ["merchant_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["offer_id"], ["offer_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pricebook_entry_id"], ["pricebook_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pricebook_id"], ["pricebook_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["program_eligibility_policy_id"],
            ["program_eligibility_versions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["quote_session_id"], ["quote_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_plan_id"], ["subscription_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checkout_session_id", name="uq_orders_checkout_session_id"),
    )
    for column_name in (
        "quote_session_id",
        "checkout_session_id",
        "user_id",
        "auth_realm_id",
        "storefront_id",
        "merchant_profile_id",
        "invoice_profile_id",
        "billing_descriptor_id",
        "pricebook_id",
        "pricebook_entry_id",
        "offer_id",
        "legal_document_set_id",
        "program_eligibility_policy_id",
        "subscription_plan_id",
        "promo_code_id",
        "partner_code_id",
        "order_status",
        "settlement_status",
    ):
        op.create_index(op.f(f"ix_orders_{column_name}"), "orders", [column_name], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject_code", sa.String(length=80), nullable=True),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("item_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column_name in ("order_id", "item_type", "subject_id", "subject_code"):
        op.create_index(op.f(f"ix_order_items_{column_name}"), "order_items", [column_name], unique=False)


def downgrade() -> None:
    for column_name in ("subject_code", "subject_id", "item_type", "order_id"):
        op.drop_index(op.f(f"ix_order_items_{column_name}"), table_name="order_items")
    op.drop_table("order_items")

    for column_name in (
        "settlement_status",
        "order_status",
        "partner_code_id",
        "promo_code_id",
        "subscription_plan_id",
        "program_eligibility_policy_id",
        "legal_document_set_id",
        "offer_id",
        "pricebook_entry_id",
        "pricebook_id",
        "billing_descriptor_id",
        "invoice_profile_id",
        "merchant_profile_id",
        "storefront_id",
        "auth_realm_id",
        "user_id",
        "checkout_session_id",
        "quote_session_id",
    ):
        op.drop_index(op.f(f"ix_orders_{column_name}"), table_name="orders")
    op.drop_table("orders")
