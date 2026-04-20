"""Phase 5 device credentials and access delivery channels."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260418_phase5_device_credentials_and_delivery_channels"
down_revision = "20260418_phase5_entitlement_grants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("credential_key", sa.String(length=160), nullable=False),
        sa.Column("service_identity_id", sa.Uuid(), nullable=False),
        sa.Column("auth_realm_id", sa.Uuid(), nullable=False),
        sa.Column("origin_storefront_id", sa.Uuid(), nullable=True),
        sa.Column("provisioning_profile_id", sa.Uuid(), nullable=True),
        sa.Column("credential_type", sa.String(length=40), nullable=False),
        sa.Column("credential_status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("subject_key", sa.String(length=160), nullable=False),
        sa.Column("provider_name", sa.String(length=40), nullable=False),
        sa.Column("provider_credential_ref", sa.String(length=160), nullable=True),
        sa.Column("credential_context", sa.JSON(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("revoke_reason_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["service_identity_id"], ["service_identities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["origin_storefront_id"], ["storefronts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["provisioning_profile_id"], ["provisioning_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["revoked_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credential_key"),
        sa.UniqueConstraint(
            "service_identity_id",
            "credential_type",
            "subject_key",
            name="uq_device_credentials_service_identity_type_subject",
        ),
    )
    op.create_index("ix_device_credentials_credential_key", "device_credentials", ["credential_key"], unique=True)
    op.create_index(
        "ix_device_credentials_service_identity_id",
        "device_credentials",
        ["service_identity_id"],
    )
    op.create_index("ix_device_credentials_auth_realm_id", "device_credentials", ["auth_realm_id"])
    op.create_index(
        "ix_device_credentials_origin_storefront_id",
        "device_credentials",
        ["origin_storefront_id"],
    )
    op.create_index(
        "ix_device_credentials_provisioning_profile_id",
        "device_credentials",
        ["provisioning_profile_id"],
    )
    op.create_index("ix_device_credentials_credential_type", "device_credentials", ["credential_type"])
    op.create_index("ix_device_credentials_credential_status", "device_credentials", ["credential_status"])
    op.create_index("ix_device_credentials_subject_key", "device_credentials", ["subject_key"])
    op.create_index("ix_device_credentials_provider_name", "device_credentials", ["provider_name"])
    op.create_index(
        "ix_device_credentials_provider_credential_ref",
        "device_credentials",
        ["provider_credential_ref"],
    )
    op.create_index("ix_device_credentials_issued_at", "device_credentials", ["issued_at"])
    op.create_index("ix_device_credentials_last_used_at", "device_credentials", ["last_used_at"])
    op.create_index("ix_device_credentials_revoked_at", "device_credentials", ["revoked_at"])
    op.create_index(
        "ix_device_credentials_revoked_by_admin_user_id",
        "device_credentials",
        ["revoked_by_admin_user_id"],
    )

    op.create_table(
        "access_delivery_channels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("delivery_key", sa.String(length=160), nullable=False),
        sa.Column("service_identity_id", sa.Uuid(), nullable=False),
        sa.Column("auth_realm_id", sa.Uuid(), nullable=False),
        sa.Column("origin_storefront_id", sa.Uuid(), nullable=True),
        sa.Column("provisioning_profile_id", sa.Uuid(), nullable=True),
        sa.Column("device_credential_id", sa.Uuid(), nullable=True),
        sa.Column("channel_type", sa.String(length=40), nullable=False),
        sa.Column("channel_status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("channel_subject_ref", sa.String(length=160), nullable=False),
        sa.Column("provider_name", sa.String(length=40), nullable=False),
        sa.Column("delivery_context", sa.JSON(), nullable=False),
        sa.Column("delivery_payload", sa.JSON(), nullable=False),
        sa.Column("last_delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("archive_reason_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["service_identity_id"], ["service_identities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["origin_storefront_id"], ["storefronts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["provisioning_profile_id"], ["provisioning_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["device_credential_id"], ["device_credentials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["archived_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("delivery_key"),
        sa.UniqueConstraint(
            "service_identity_id",
            "channel_type",
            "channel_subject_ref",
            name="uq_access_delivery_channels_service_identity_type_subject",
        ),
    )
    op.create_index(
        "ix_access_delivery_channels_delivery_key",
        "access_delivery_channels",
        ["delivery_key"],
        unique=True,
    )
    op.create_index(
        "ix_access_delivery_channels_service_identity_id",
        "access_delivery_channels",
        ["service_identity_id"],
    )
    op.create_index(
        "ix_access_delivery_channels_auth_realm_id",
        "access_delivery_channels",
        ["auth_realm_id"],
    )
    op.create_index(
        "ix_access_delivery_channels_origin_storefront_id",
        "access_delivery_channels",
        ["origin_storefront_id"],
    )
    op.create_index(
        "ix_access_delivery_channels_provisioning_profile_id",
        "access_delivery_channels",
        ["provisioning_profile_id"],
    )
    op.create_index(
        "ix_access_delivery_channels_device_credential_id",
        "access_delivery_channels",
        ["device_credential_id"],
    )
    op.create_index(
        "ix_access_delivery_channels_channel_type",
        "access_delivery_channels",
        ["channel_type"],
    )
    op.create_index(
        "ix_access_delivery_channels_channel_status",
        "access_delivery_channels",
        ["channel_status"],
    )
    op.create_index(
        "ix_access_delivery_channels_channel_subject_ref",
        "access_delivery_channels",
        ["channel_subject_ref"],
    )
    op.create_index(
        "ix_access_delivery_channels_provider_name",
        "access_delivery_channels",
        ["provider_name"],
    )
    op.create_index(
        "ix_access_delivery_channels_last_delivered_at",
        "access_delivery_channels",
        ["last_delivered_at"],
    )
    op.create_index(
        "ix_access_delivery_channels_last_accessed_at",
        "access_delivery_channels",
        ["last_accessed_at"],
    )
    op.create_index(
        "ix_access_delivery_channels_archived_at",
        "access_delivery_channels",
        ["archived_at"],
    )
    op.create_index(
        "ix_access_delivery_channels_archived_by_admin_user_id",
        "access_delivery_channels",
        ["archived_by_admin_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_access_delivery_channels_archived_by_admin_user_id",
        table_name="access_delivery_channels",
    )
    op.drop_index("ix_access_delivery_channels_archived_at", table_name="access_delivery_channels")
    op.drop_index("ix_access_delivery_channels_last_accessed_at", table_name="access_delivery_channels")
    op.drop_index("ix_access_delivery_channels_last_delivered_at", table_name="access_delivery_channels")
    op.drop_index("ix_access_delivery_channels_provider_name", table_name="access_delivery_channels")
    op.drop_index(
        "ix_access_delivery_channels_channel_subject_ref",
        table_name="access_delivery_channels",
    )
    op.drop_index("ix_access_delivery_channels_channel_status", table_name="access_delivery_channels")
    op.drop_index("ix_access_delivery_channels_channel_type", table_name="access_delivery_channels")
    op.drop_index(
        "ix_access_delivery_channels_device_credential_id",
        table_name="access_delivery_channels",
    )
    op.drop_index(
        "ix_access_delivery_channels_provisioning_profile_id",
        table_name="access_delivery_channels",
    )
    op.drop_index(
        "ix_access_delivery_channels_origin_storefront_id",
        table_name="access_delivery_channels",
    )
    op.drop_index("ix_access_delivery_channels_auth_realm_id", table_name="access_delivery_channels")
    op.drop_index(
        "ix_access_delivery_channels_service_identity_id",
        table_name="access_delivery_channels",
    )
    op.drop_index("ix_access_delivery_channels_delivery_key", table_name="access_delivery_channels")
    op.drop_table("access_delivery_channels")

    op.drop_index("ix_device_credentials_revoked_by_admin_user_id", table_name="device_credentials")
    op.drop_index("ix_device_credentials_revoked_at", table_name="device_credentials")
    op.drop_index("ix_device_credentials_last_used_at", table_name="device_credentials")
    op.drop_index("ix_device_credentials_issued_at", table_name="device_credentials")
    op.drop_index("ix_device_credentials_provider_credential_ref", table_name="device_credentials")
    op.drop_index("ix_device_credentials_provider_name", table_name="device_credentials")
    op.drop_index("ix_device_credentials_subject_key", table_name="device_credentials")
    op.drop_index("ix_device_credentials_credential_status", table_name="device_credentials")
    op.drop_index("ix_device_credentials_credential_type", table_name="device_credentials")
    op.drop_index("ix_device_credentials_provisioning_profile_id", table_name="device_credentials")
    op.drop_index("ix_device_credentials_origin_storefront_id", table_name="device_credentials")
    op.drop_index("ix_device_credentials_auth_realm_id", table_name="device_credentials")
    op.drop_index("ix_device_credentials_service_identity_id", table_name="device_credentials")
    op.drop_index("ix_device_credentials_credential_key", table_name="device_credentials")
    op.drop_table("device_credentials")
