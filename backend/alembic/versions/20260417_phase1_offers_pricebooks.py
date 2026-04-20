"""Add offer, pricebook, and program eligibility foundations.

Revision ID: 20260417_phase1_offers_pricebooks
Revises: 20260417_phase1_partner_workspace
Create Date: 2026-04-17 23:59:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260417_phase1_offers_pricebooks"
down_revision: str | None = "20260417_phase1_partner_workspace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "offer_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offer_key", sa.String(length=60), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("subscription_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("included_addon_codes", sa.JSON(), nullable=False),
        sa.Column("sale_channels", sa.JSON(), nullable=False),
        sa.Column("visibility_rules", sa.JSON(), nullable=False),
        sa.Column("invite_bundle", sa.JSON(), nullable=False),
        sa.Column("trial_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("gift_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("referral_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("renewal_incentives", sa.JSON(), nullable=False),
        sa.Column("version_status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["subscription_plan_id"], ["subscription_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("offer_key", "effective_from", name="uq_offer_versions_key_effective_from"),
    )
    op.create_index(op.f("ix_offer_versions_offer_key"), "offer_versions", ["offer_key"], unique=False)
    op.create_index(
        op.f("ix_offer_versions_subscription_plan_id"),
        "offer_versions",
        ["subscription_plan_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_offer_versions_version_status"),
        "offer_versions",
        ["version_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_offer_versions_effective_from"),
        "offer_versions",
        ["effective_from"],
        unique=False,
    )

    op.create_table(
        "pricebook_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pricebook_key", sa.String(length=60), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("storefront_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("merchant_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("region_code", sa.String(length=16), nullable=True),
        sa.Column("discount_rules", sa.JSON(), nullable=False),
        sa.Column("renewal_pricing_policy", sa.JSON(), nullable=False),
        sa.Column("version_status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["merchant_profile_id"], ["merchant_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pricebook_key", "effective_from", name="uq_pricebook_versions_key_effective_from"),
    )
    op.create_index(op.f("ix_pricebook_versions_pricebook_key"), "pricebook_versions", ["pricebook_key"], unique=False)
    op.create_index(
        op.f("ix_pricebook_versions_storefront_id"),
        "pricebook_versions",
        ["storefront_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pricebook_versions_merchant_profile_id"),
        "pricebook_versions",
        ["merchant_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pricebook_versions_currency_code"),
        "pricebook_versions",
        ["currency_code"],
        unique=False,
    )
    op.create_index(op.f("ix_pricebook_versions_region_code"), "pricebook_versions", ["region_code"], unique=False)
    op.create_index(
        op.f("ix_pricebook_versions_version_status"),
        "pricebook_versions",
        ["version_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pricebook_versions_effective_from"),
        "pricebook_versions",
        ["effective_from"],
        unique=False,
    )

    op.create_table(
        "pricebook_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pricebook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visible_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("compare_at_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("included_addon_codes", sa.JSON(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["offer_id"], ["offer_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pricebook_id"], ["pricebook_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pricebook_id", "offer_id", name="uq_pricebook_entries_pricebook_offer"),
    )
    op.create_index(
        op.f("ix_pricebook_entries_pricebook_id"),
        "pricebook_entries",
        ["pricebook_id"],
        unique=False,
    )
    op.create_index(op.f("ix_pricebook_entries_offer_id"), "pricebook_entries", ["offer_id"], unique=False)

    op.create_table(
        "program_eligibility_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_key", sa.String(length=60), nullable=False),
        sa.Column("subject_type", sa.String(length=20), nullable=False),
        sa.Column("subscription_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("plan_addon_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invite_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("referral_credit_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creator_affiliate_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("performance_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reseller_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("renewal_commissionable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("addon_commissionable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version_status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            """
            ((subscription_plan_id IS NOT NULL)::integer +
             (plan_addon_id IS NOT NULL)::integer +
             (offer_id IS NOT NULL)::integer) = 1
            """,
            name="ck_program_eligibility_exactly_one_subject",
        ),
        sa.ForeignKeyConstraint(["offer_id"], ["offer_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_addon_id"], ["plan_addons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_plan_id"], ["subscription_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_key", "effective_from", name="uq_program_eligibility_key_effective_from"),
    )
    op.create_index(
        op.f("ix_program_eligibility_versions_policy_key"),
        "program_eligibility_versions",
        ["policy_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_program_eligibility_versions_subject_type"),
        "program_eligibility_versions",
        ["subject_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_program_eligibility_versions_subscription_plan_id"),
        "program_eligibility_versions",
        ["subscription_plan_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_program_eligibility_versions_plan_addon_id"),
        "program_eligibility_versions",
        ["plan_addon_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_program_eligibility_versions_offer_id"),
        "program_eligibility_versions",
        ["offer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_program_eligibility_versions_version_status"),
        "program_eligibility_versions",
        ["version_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_program_eligibility_versions_effective_from"),
        "program_eligibility_versions",
        ["effective_from"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_program_eligibility_versions_effective_from"),
        table_name="program_eligibility_versions",
    )
    op.drop_index(
        op.f("ix_program_eligibility_versions_version_status"),
        table_name="program_eligibility_versions",
    )
    op.drop_index(op.f("ix_program_eligibility_versions_offer_id"), table_name="program_eligibility_versions")
    op.drop_index(
        op.f("ix_program_eligibility_versions_plan_addon_id"),
        table_name="program_eligibility_versions",
    )
    op.drop_index(
        op.f("ix_program_eligibility_versions_subscription_plan_id"),
        table_name="program_eligibility_versions",
    )
    op.drop_index(
        op.f("ix_program_eligibility_versions_subject_type"),
        table_name="program_eligibility_versions",
    )
    op.drop_index(
        op.f("ix_program_eligibility_versions_policy_key"),
        table_name="program_eligibility_versions",
    )
    op.drop_table("program_eligibility_versions")

    op.drop_index(op.f("ix_pricebook_entries_offer_id"), table_name="pricebook_entries")
    op.drop_index(op.f("ix_pricebook_entries_pricebook_id"), table_name="pricebook_entries")
    op.drop_table("pricebook_entries")

    op.drop_index(op.f("ix_pricebook_versions_effective_from"), table_name="pricebook_versions")
    op.drop_index(op.f("ix_pricebook_versions_version_status"), table_name="pricebook_versions")
    op.drop_index(op.f("ix_pricebook_versions_region_code"), table_name="pricebook_versions")
    op.drop_index(op.f("ix_pricebook_versions_currency_code"), table_name="pricebook_versions")
    op.drop_index(op.f("ix_pricebook_versions_merchant_profile_id"), table_name="pricebook_versions")
    op.drop_index(op.f("ix_pricebook_versions_storefront_id"), table_name="pricebook_versions")
    op.drop_index(op.f("ix_pricebook_versions_pricebook_key"), table_name="pricebook_versions")
    op.drop_table("pricebook_versions")

    op.drop_index(op.f("ix_offer_versions_effective_from"), table_name="offer_versions")
    op.drop_index(op.f("ix_offer_versions_version_status"), table_name="offer_versions")
    op.drop_index(op.f("ix_offer_versions_subscription_plan_id"), table_name="offer_versions")
    op.drop_index(op.f("ix_offer_versions_offer_key"), table_name="offer_versions")
    op.drop_table("offer_versions")
