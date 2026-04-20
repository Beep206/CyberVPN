"""Add quote sessions and checkout sessions for Phase 2.

Revision ID: 20260418_phase2_quote_checkout_sessions
Revises: 20260418_phase2_merchant_billing_foundation
Create Date: 2026-04-18 03:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260418_phase2_quote_checkout_sessions"
down_revision: str | None = "20260418_phase2_merchant_billing_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quote_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column("sale_channel", sa.String(length=30), nullable=False, server_default="web"),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("quote_status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("promo_code", sa.String(length=50), nullable=True),
        sa.Column("promo_code_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("partner_code_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("quote_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("context_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["billing_descriptor_id"], ["billing_descriptors.id"], ondelete="SET NULL"),
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
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_plan_id"], ["subscription_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column_name in (
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
        "quote_status",
        "promo_code_id",
        "partner_code_id",
        "expires_at",
    ):
        op.create_index(op.f(f"ix_quote_sessions_{column_name}"), "quote_sessions", [column_name], unique=False)

    op.create_table(
        "checkout_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_session_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column("sale_channel", sa.String(length=30), nullable=False, server_default="web"),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("checkout_status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("promo_code_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("partner_code_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("checkout_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("context_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["billing_descriptor_id"], ["billing_descriptors.id"], ondelete="SET NULL"),
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
        sa.ForeignKeyConstraint(["quote_session_id"], ["quote_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_plan_id"], ["subscription_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quote_session_id", name="uq_checkout_sessions_quote_session_id"),
    )
    for column_name in (
        "quote_session_id",
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
        "checkout_status",
        "idempotency_key",
        "promo_code_id",
        "partner_code_id",
        "expires_at",
    ):
        op.create_index(
            op.f(f"ix_checkout_sessions_{column_name}"),
            "checkout_sessions",
            [column_name],
            unique=False,
        )


def downgrade() -> None:
    for column_name in (
        "expires_at",
        "partner_code_id",
        "promo_code_id",
        "idempotency_key",
        "checkout_status",
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
        "quote_session_id",
    ):
        op.drop_index(op.f(f"ix_checkout_sessions_{column_name}"), table_name="checkout_sessions")
    op.drop_table("checkout_sessions")

    for column_name in (
        "expires_at",
        "partner_code_id",
        "promo_code_id",
        "quote_status",
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
    ):
        op.drop_index(op.f(f"ix_quote_sessions_{column_name}"), table_name="quote_sessions")
    op.drop_table("quote_sessions")
