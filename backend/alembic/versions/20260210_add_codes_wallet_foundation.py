"""Add system_config, wallets, wallet_transactions tables.
Add referral/partner columns to mobile_users.
Add codes/wallet columns to payments.

Revision ID: 20260210_codes_wallet
Revises: 20260210_deleted_at
Create Date: 2026-02-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260210_codes_wallet"
down_revision: str | None = "20260210_deleted_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create foundation tables and columns for codes & wallet system."""

    # --- system_config ---
    op.create_table(
        "system_config",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", postgresql.JSONB, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.Uuid(as_uuid=True), nullable=True),
    )

    # --- wallets ---
    op.create_table(
        "wallets",
        sa.Column(
            "id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mobile_users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("balance", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("frozen", sa.Numeric(20, 8), nullable=False, server_default="0"),
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
        sa.CheckConstraint("balance >= 0", name="ck_wallets_balance_non_negative"),
        sa.CheckConstraint("frozen >= 0", name="ck_wallets_frozen_non_negative"),
    )
    op.create_index("ix_wallets_user_id", "wallets", ["user_id"])

    # --- wallet_transactions ---
    op.create_table(
        "wallet_transactions",
        sa.Column(
            "id", sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "wallet_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("wallets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mobile_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("balance_after", sa.Numeric(20, 8), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("reference_type", sa.String(30), nullable=True),
        sa.Column("reference_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="ck_wallet_tx_amount_positive"),
        sa.CheckConstraint(
            "type IN ('credit', 'debit')",
            name="ck_wallet_tx_type",
        ),
        sa.CheckConstraint(
            "reason IN ("
            "'referral_commission', 'partner_earning', 'partner_markup', "
            "'admin_topup', 'subscription_payment', 'withdrawal', "
            "'withdrawal_fee', 'refund', 'adjustment')",
            name="ck_wallet_tx_reason",
        ),
    )
    op.create_index("ix_wallet_transactions_wallet_id", "wallet_transactions", ["wallet_id"])
    op.create_index("ix_wallet_transactions_user_id", "wallet_transactions", ["user_id"])
    op.create_index("ix_wallet_transactions_created_at", "wallet_transactions", ["created_at"])
    op.create_index(
        "ix_wallet_transactions_reference",
        "wallet_transactions",
        ["reference_type", "reference_id"],
    )

    # --- mobile_users: add referral & partner columns ---
    op.add_column(
        "mobile_users",
        sa.Column("referral_code", sa.String(12), unique=True, nullable=True),
    )
    op.add_column(
        "mobile_users",
        sa.Column(
            "referred_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mobile_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "mobile_users",
        sa.Column(
            "partner_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mobile_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "mobile_users",
        sa.Column("is_partner", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column(
        "mobile_users",
        sa.Column("partner_promoted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_mobile_users_referral_code", "mobile_users", ["referral_code"])

    # --- payments: add codes & wallet columns ---
    op.add_column(
        "payments",
        sa.Column("plan_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("promo_code_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("partner_code_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("discount_amount", sa.Numeric(20, 8), nullable=False, server_default="0"),
    )
    op.add_column(
        "payments",
        sa.Column("wallet_amount_used", sa.Numeric(20, 8), nullable=False, server_default="0"),
    )
    op.add_column(
        "payments",
        sa.Column("final_amount", sa.Numeric(20, 8), nullable=True),
    )

    # --- Seed default system_config values ---
    op.execute(
        """
        INSERT INTO system_config (key, value, description) VALUES
        ('invite.plan_rules', '{"rules": []}', 'Invite generation rules per plan'),
        ('invite.default_expiry_days', '{"days": 30}', 'Invite code validity period in days'),
        ('referral.enabled', '{"enabled": true}', 'Whether referral system is enabled'),
        ('referral.commission_rate', '{"rate": 0.10}', 'Referral commission rate (0.10 = 10%)'),
        ('referral.duration_mode', '{"mode": "indefinite"}', 'Referral commission duration mode'),
        ('partner.max_markup_pct', '{"max_pct": 300}', 'Maximum partner markup percentage'),
        ('partner.base_commission_pct', '{"pct": 10}', 'Default partner commission on base price'),
        ('partner.tiers', '{"tiers": [{"min_clients": 0, "commission_pct": 20}]}', 'Partner commission tiers'),
        ('wallet.min_withdrawal', '{"amount": 5.0, "currency": "USD"}', 'Minimum withdrawal amount'),
        ('wallet.withdrawal_enabled', '{"enabled": true}', 'Whether withdrawals are enabled'),
        ('wallet.withdrawal_fee_pct', '{"pct": 0}', 'Withdrawal fee percentage')
        """
    )


def downgrade() -> None:
    """Remove codes & wallet foundation tables and columns."""

    # Remove payment columns
    op.drop_column("payments", "final_amount")
    op.drop_column("payments", "wallet_amount_used")
    op.drop_column("payments", "discount_amount")
    op.drop_column("payments", "partner_code_id")
    op.drop_column("payments", "promo_code_id")
    op.drop_column("payments", "plan_id")

    # Remove mobile_users columns
    op.drop_index("ix_mobile_users_referral_code", table_name="mobile_users")
    op.drop_column("mobile_users", "partner_promoted_at")
    op.drop_column("mobile_users", "is_partner")
    op.drop_column("mobile_users", "partner_user_id")
    op.drop_column("mobile_users", "referred_by_user_id")
    op.drop_column("mobile_users", "referral_code")

    # Drop wallet_transactions
    op.drop_index("ix_wallet_transactions_reference", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_created_at", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_user_id", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_wallet_id", table_name="wallet_transactions")
    op.drop_table("wallet_transactions")

    # Drop wallets
    op.drop_index("ix_wallets_user_id", table_name="wallets")
    op.drop_table("wallets")

    # Drop system_config
    op.drop_table("system_config")
