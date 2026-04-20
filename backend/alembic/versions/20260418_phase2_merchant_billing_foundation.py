"""Add merchant, invoice, and billing descriptor foundations for Phase 2.

Revision ID: 20260418_phase2_merchant_billing_foundation
Revises: 20260418_phase1_risk_foundation
Create Date: 2026-04-18 01:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260418_phase2_merchant_billing_foundation"
down_revision: str | None = "20260418_phase1_risk_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invoice_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_key", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("issuer_legal_name", sa.String(length=255), nullable=False),
        sa.Column("tax_identifier", sa.String(length=64), nullable=True),
        sa.Column("issuer_email", sa.String(length=255), nullable=True),
        sa.Column("tax_behavior", sa.JSON(), nullable=False),
        sa.Column("invoice_footer", sa.String(length=500), nullable=True),
        sa.Column("receipt_footer", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_profiles_profile_key"), "invoice_profiles", ["profile_key"], unique=True)

    op.add_column(
        "merchant_profiles",
        sa.Column("invoice_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("merchant_profiles", sa.Column("settlement_reference", sa.String(length=120), nullable=True))
    op.add_column(
        "merchant_profiles",
        sa.Column("supported_currencies", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column(
        "merchant_profiles",
        sa.Column("tax_behavior", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.add_column(
        "merchant_profiles",
        sa.Column(
            "refund_responsibility_model",
            sa.String(length=50),
            nullable=False,
            server_default="merchant_of_record",
        ),
    )
    op.add_column(
        "merchant_profiles",
        sa.Column(
            "chargeback_liability_model",
            sa.String(length=50),
            nullable=False,
            server_default="merchant_of_record",
        ),
    )
    op.create_foreign_key(
        "fk_merchant_profiles_invoice_profile_id",
        "merchant_profiles",
        "invoice_profiles",
        ["invoice_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_merchant_profiles_invoice_profile_id"),
        "merchant_profiles",
        ["invoice_profile_id"],
        unique=False,
    )

    op.create_table(
        "billing_descriptors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("descriptor_key", sa.String(length=50), nullable=False),
        sa.Column("merchant_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("statement_descriptor", sa.String(length=64), nullable=False),
        sa.Column("soft_descriptor", sa.String(length=64), nullable=True),
        sa.Column("support_phone", sa.String(length=32), nullable=True),
        sa.Column("support_url", sa.String(length=255), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["invoice_profile_id"], ["invoice_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["merchant_profile_id"], ["merchant_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_billing_descriptors_descriptor_key"),
        "billing_descriptors",
        ["descriptor_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_billing_descriptors_merchant_profile_id"),
        "billing_descriptors",
        ["merchant_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_billing_descriptors_invoice_profile_id"),
        "billing_descriptors",
        ["invoice_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_billing_descriptors_invoice_profile_id"), table_name="billing_descriptors")
    op.drop_index(op.f("ix_billing_descriptors_merchant_profile_id"), table_name="billing_descriptors")
    op.drop_index(op.f("ix_billing_descriptors_descriptor_key"), table_name="billing_descriptors")
    op.drop_table("billing_descriptors")

    op.drop_index(op.f("ix_merchant_profiles_invoice_profile_id"), table_name="merchant_profiles")
    op.drop_constraint("fk_merchant_profiles_invoice_profile_id", "merchant_profiles", type_="foreignkey")
    op.drop_column("merchant_profiles", "chargeback_liability_model")
    op.drop_column("merchant_profiles", "refund_responsibility_model")
    op.drop_column("merchant_profiles", "tax_behavior")
    op.drop_column("merchant_profiles", "supported_currencies")
    op.drop_column("merchant_profiles", "settlement_reference")
    op.drop_column("merchant_profiles", "invoice_profile_id")

    op.drop_index(op.f("ix_invoice_profiles_profile_key"), table_name="invoice_profiles")
    op.drop_table("invoice_profiles")
