"""Add brand, storefront, and profile core tables.

Revision ID: 20260417_phase1_storefront_core
Revises: 20260416_pricing_catalog
Create Date: 2026-04-17 21:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260417_phase1_storefront_core"
down_revision: str | None = "20260416_pricing_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_key", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_brands_brand_key"), "brands", ["brand_key"], unique=True)

    op.create_table(
        "merchant_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_key", sa.String(length=50), nullable=False),
        sa.Column("legal_entity_name", sa.String(length=255), nullable=False),
        sa.Column("billing_descriptor", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_merchant_profiles_profile_key"), "merchant_profiles", ["profile_key"], unique=True)

    op.create_table(
        "support_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_key", sa.String(length=50), nullable=False),
        sa.Column("support_email", sa.String(length=255), nullable=False),
        sa.Column("help_center_url", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_support_profiles_profile_key"), "support_profiles", ["profile_key"], unique=True)

    op.create_table(
        "communication_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_key", sa.String(length=50), nullable=False),
        sa.Column("sender_domain", sa.String(length=255), nullable=False),
        sa.Column("from_email", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_communication_profiles_profile_key"),
        "communication_profiles",
        ["profile_key"],
        unique=True,
    )

    op.create_table(
        "storefronts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storefront_key", sa.String(length=50), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("merchant_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("support_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("communication_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["merchant_profile_id"], ["merchant_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["support_profile_id"], ["support_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["communication_profile_id"], ["communication_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_storefronts_storefront_key"), "storefronts", ["storefront_key"], unique=True)
    op.create_index(op.f("ix_storefronts_host"), "storefronts", ["host"], unique=True)
    op.create_index(op.f("ix_storefronts_brand_id"), "storefronts", ["brand_id"], unique=False)
    op.create_index(op.f("ix_storefronts_merchant_profile_id"), "storefronts", ["merchant_profile_id"], unique=False)
    op.create_index(op.f("ix_storefronts_support_profile_id"), "storefronts", ["support_profile_id"], unique=False)
    op.create_index(
        op.f("ix_storefronts_communication_profile_id"),
        "storefronts",
        ["communication_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_storefronts_communication_profile_id"), table_name="storefronts")
    op.drop_index(op.f("ix_storefronts_support_profile_id"), table_name="storefronts")
    op.drop_index(op.f("ix_storefronts_merchant_profile_id"), table_name="storefronts")
    op.drop_index(op.f("ix_storefronts_brand_id"), table_name="storefronts")
    op.drop_index(op.f("ix_storefronts_host"), table_name="storefronts")
    op.drop_index(op.f("ix_storefronts_storefront_key"), table_name="storefronts")
    op.drop_table("storefronts")

    op.drop_index(op.f("ix_communication_profiles_profile_key"), table_name="communication_profiles")
    op.drop_table("communication_profiles")

    op.drop_index(op.f("ix_support_profiles_profile_key"), table_name="support_profiles")
    op.drop_table("support_profiles")

    op.drop_index(op.f("ix_merchant_profiles_profile_key"), table_name="merchant_profiles")
    op.drop_table("merchant_profiles")

    op.drop_index(op.f("ix_brands_brand_key"), table_name="brands")
    op.drop_table("brands")
