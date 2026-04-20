"""Phase 5 service identities and provisioning profiles."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260418_phase5_service_identity_foundation"
down_revision = "20260418_phase4_payout_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_identities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("service_key", sa.String(length=160), nullable=False),
        sa.Column("customer_account_id", sa.Uuid(), nullable=False),
        sa.Column("auth_realm_id", sa.Uuid(), nullable=False),
        sa.Column("source_order_id", sa.Uuid(), nullable=True),
        sa.Column("origin_storefront_id", sa.Uuid(), nullable=True),
        sa.Column("provider_name", sa.String(length=40), nullable=False),
        sa.Column("provider_subject_ref", sa.String(length=160), nullable=True),
        sa.Column("identity_status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("service_context", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_account_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_storefront_id"], ["storefronts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "customer_account_id",
            "auth_realm_id",
            "provider_name",
            name="uq_service_identities_customer_realm_provider",
        ),
        sa.UniqueConstraint("service_key"),
    )
    op.create_index("ix_service_identities_service_key", "service_identities", ["service_key"], unique=True)
    op.create_index(
        "ix_service_identities_customer_account_id",
        "service_identities",
        ["customer_account_id"],
    )
    op.create_index("ix_service_identities_auth_realm_id", "service_identities", ["auth_realm_id"])
    op.create_index("ix_service_identities_source_order_id", "service_identities", ["source_order_id"])
    op.create_index(
        "ix_service_identities_origin_storefront_id",
        "service_identities",
        ["origin_storefront_id"],
    )
    op.create_index("ix_service_identities_provider_name", "service_identities", ["provider_name"])
    op.create_index(
        "ix_service_identities_provider_subject_ref",
        "service_identities",
        ["provider_subject_ref"],
    )
    op.create_index("ix_service_identities_identity_status", "service_identities", ["identity_status"])

    op.create_table(
        "provisioning_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("service_identity_id", sa.Uuid(), nullable=False),
        sa.Column("profile_key", sa.String(length=120), nullable=False),
        sa.Column("target_channel", sa.String(length=40), nullable=False),
        sa.Column("delivery_method", sa.String(length=40), nullable=False),
        sa.Column("profile_status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("provider_name", sa.String(length=40), nullable=False),
        sa.Column("provider_profile_ref", sa.String(length=160), nullable=True),
        sa.Column("provisioning_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["service_identity_id"], ["service_identities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "service_identity_id",
            "profile_key",
            name="uq_provisioning_profiles_service_identity_profile_key",
        ),
    )
    op.create_index(
        "ix_provisioning_profiles_service_identity_id",
        "provisioning_profiles",
        ["service_identity_id"],
    )
    op.create_index("ix_provisioning_profiles_profile_key", "provisioning_profiles", ["profile_key"])
    op.create_index("ix_provisioning_profiles_target_channel", "provisioning_profiles", ["target_channel"])
    op.create_index("ix_provisioning_profiles_delivery_method", "provisioning_profiles", ["delivery_method"])
    op.create_index("ix_provisioning_profiles_profile_status", "provisioning_profiles", ["profile_status"])
    op.create_index("ix_provisioning_profiles_provider_name", "provisioning_profiles", ["provider_name"])
    op.create_index(
        "ix_provisioning_profiles_provider_profile_ref",
        "provisioning_profiles",
        ["provider_profile_ref"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provisioning_profiles_provider_profile_ref",
        table_name="provisioning_profiles",
    )
    op.drop_index("ix_provisioning_profiles_provider_name", table_name="provisioning_profiles")
    op.drop_index("ix_provisioning_profiles_profile_status", table_name="provisioning_profiles")
    op.drop_index("ix_provisioning_profiles_delivery_method", table_name="provisioning_profiles")
    op.drop_index("ix_provisioning_profiles_target_channel", table_name="provisioning_profiles")
    op.drop_index("ix_provisioning_profiles_profile_key", table_name="provisioning_profiles")
    op.drop_index("ix_provisioning_profiles_service_identity_id", table_name="provisioning_profiles")
    op.drop_table("provisioning_profiles")

    op.drop_index("ix_service_identities_identity_status", table_name="service_identities")
    op.drop_index("ix_service_identities_provider_subject_ref", table_name="service_identities")
    op.drop_index("ix_service_identities_provider_name", table_name="service_identities")
    op.drop_index("ix_service_identities_origin_storefront_id", table_name="service_identities")
    op.drop_index("ix_service_identities_source_order_id", table_name="service_identities")
    op.drop_index("ix_service_identities_auth_realm_id", table_name="service_identities")
    op.drop_index("ix_service_identities_customer_account_id", table_name="service_identities")
    op.drop_index("ix_service_identities_service_key", table_name="service_identities")
    op.drop_table("service_identities")
