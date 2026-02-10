"""Add invite_codes, promo_codes, promo_code_usages, partner_codes,
partner_earnings, referral_commissions, withdrawal_requests tables.

Revision ID: 20260210_codes_tables
Revises: 20260210_codes_wallet
Create Date: 2026-02-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260210_codes_tables"
down_revision: str | None = "20260210_codes_wallet"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all codes & partner tables."""

    # --- invite_codes ---
    op.create_table(
        "invite_codes",
        sa.Column(
            "id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column(
            "owner_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mobile_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("free_days", sa.Integer, nullable=False),
        sa.Column("plan_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column(
            "source_payment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("payments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "used_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mobile_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_invite_codes_code", "invite_codes", ["code"])
    op.create_index("ix_invite_codes_owner_user_id", "invite_codes", ["owner_user_id"])

    # --- promo_codes ---
    op.create_table(
        "promo_codes",
        sa.Column(
            "id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("discount_type", sa.String(10), nullable=False),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("max_uses", sa.Integer, nullable=True),
        sa.Column("current_uses", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_single_use", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("plan_ids", postgresql.ARRAY(sa.Uuid(as_uuid=True)), nullable=True),
        sa.Column("min_amount", sa.Numeric(20, 8), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("discount_value > 0", name="ck_promo_codes_discount_positive"),
        sa.CheckConstraint(
            "discount_type IN ('percent', 'fixed')",
            name="ck_promo_codes_discount_type",
        ),
    )
    op.create_index("ix_promo_codes_code", "promo_codes", ["code"])

    # --- promo_code_usages ---
    op.create_table(
        "promo_code_usages",
        sa.Column(
            "id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "promo_code_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("promo_codes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mobile_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "payment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("payments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("discount_applied", sa.Numeric(20, 8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_promo_code_usages_promo_code_id", "promo_code_usages", ["promo_code_id"])
    op.create_index("ix_promo_code_usages_user_id", "promo_code_usages", ["user_id"])

    # --- partner_codes ---
    op.create_table(
        "partner_codes",
        sa.Column(
            "id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("code", sa.String(30), unique=True, nullable=False),
        sa.Column(
            "partner_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mobile_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("markup_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("markup_pct >= 0", name="ck_partner_codes_markup_non_negative"),
    )
    op.create_index("ix_partner_codes_code", "partner_codes", ["code"])
    op.create_index("ix_partner_codes_partner_user_id", "partner_codes", ["partner_user_id"])

    # --- partner_earnings ---
    op.create_table(
        "partner_earnings",
        sa.Column(
            "id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "partner_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mobile_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mobile_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "payment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("payments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "partner_code_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("partner_codes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("base_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("markup_amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("commission_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("commission_amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("total_earning", sa.Numeric(20, 8), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column(
            "wallet_tx_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("wallet_transactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_partner_earnings_partner_user_id", "partner_earnings", ["partner_user_id"])
    op.create_index("ix_partner_earnings_client_user_id", "partner_earnings", ["client_user_id"])

    # --- referral_commissions ---
    op.create_table(
        "referral_commissions",
        sa.Column(
            "id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "referrer_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mobile_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "referred_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mobile_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "payment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("payments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("commission_rate", sa.Numeric(5, 4), nullable=False),
        sa.Column("base_amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("commission_amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column(
            "wallet_tx_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("wallet_transactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_referral_commissions_referrer_user_id", "referral_commissions", ["referrer_user_id"])
    op.create_index("ix_referral_commissions_referred_user_id", "referral_commissions", ["referred_user_id"])

    # --- withdrawal_requests ---
    op.create_table(
        "withdrawal_requests",
        sa.Column(
            "id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mobile_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "wallet_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("wallets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("admin_note", sa.Text, nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "processed_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "wallet_tx_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("wallet_transactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="ck_withdrawal_requests_amount_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')",
            name="ck_withdrawal_requests_status",
        ),
        sa.CheckConstraint(
            "method IN ('cryptobot', 'manual')",
            name="ck_withdrawal_requests_method",
        ),
    )
    op.create_index("ix_withdrawal_requests_user_id", "withdrawal_requests", ["user_id"])
    op.create_index("ix_withdrawal_requests_status", "withdrawal_requests", ["status"])


def downgrade() -> None:
    """Drop all codes & partner tables in reverse order."""

    op.drop_index("ix_withdrawal_requests_status", table_name="withdrawal_requests")
    op.drop_index("ix_withdrawal_requests_user_id", table_name="withdrawal_requests")
    op.drop_table("withdrawal_requests")

    op.drop_index("ix_referral_commissions_referred_user_id", table_name="referral_commissions")
    op.drop_index("ix_referral_commissions_referrer_user_id", table_name="referral_commissions")
    op.drop_table("referral_commissions")

    op.drop_index("ix_partner_earnings_client_user_id", table_name="partner_earnings")
    op.drop_index("ix_partner_earnings_partner_user_id", table_name="partner_earnings")
    op.drop_table("partner_earnings")

    op.drop_index("ix_partner_codes_partner_user_id", table_name="partner_codes")
    op.drop_index("ix_partner_codes_code", table_name="partner_codes")
    op.drop_table("partner_codes")

    op.drop_index("ix_promo_code_usages_user_id", table_name="promo_code_usages")
    op.drop_index("ix_promo_code_usages_promo_code_id", table_name="promo_code_usages")
    op.drop_table("promo_code_usages")

    op.drop_index("ix_promo_codes_code", table_name="promo_codes")
    op.drop_table("promo_codes")

    op.drop_index("ix_invite_codes_owner_user_id", table_name="invite_codes")
    op.drop_index("ix_invite_codes_code", table_name="invite_codes")
    op.drop_table("invite_codes")
