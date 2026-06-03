"""Passkey WebAuthn credential storage.

Revision ID: 20260603_passkey_credentials
Revises: 20260531_messaging_core
Create Date: 2026-06-03
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260603_passkey_credentials"
down_revision = "20260531_messaging_core"
branch_labels = None
depends_on = None


def _uuid_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.Uuid()


def _json_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB()
    return sa.JSON()


def upgrade() -> None:
    op.create_table(
        "passkey_credentials",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("credential_id", sa.Text(), nullable=False),
        sa.Column("credential_id_hash", sa.String(length=64), nullable=False),
        sa.Column("credential_public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("auth_realm_id", _uuid_type(), nullable=False),
        sa.Column("realm_key", sa.String(length=50), nullable=False),
        sa.Column("audience", sa.String(length=120), nullable=False),
        sa.Column("principal_class", sa.String(length=40), nullable=False),
        sa.Column("principal_subject", sa.String(length=80), nullable=False),
        sa.Column("user_handle", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("surface", sa.String(length=40), nullable=False),
        sa.Column("rp_id", sa.String(length=253), nullable=False),
        sa.Column("origin", sa.String(length=255), nullable=True),
        sa.Column("aaguid", sa.String(length=36), nullable=True),
        sa.Column("attestation_format", sa.String(length=40), nullable=True),
        sa.Column("credential_type", sa.String(length=40), nullable=False, server_default="public-key"),
        sa.Column("device_type", sa.String(length=40), nullable=True),
        sa.Column("transports", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("backed_up", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("user_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("authenticator_attachment", sa.String(length=40), nullable=True),
        sa.Column("policy_snapshot", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("clone_suspected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credential_id_hash", name="uq_passkey_credentials_credential_id_hash"),
    )
    op.create_index("ix_passkey_credentials_auth_realm_id", "passkey_credentials", ["auth_realm_id"])
    op.create_index("ix_passkey_credentials_credential_id_hash", "passkey_credentials", ["credential_id_hash"])
    op.create_index("ix_passkey_credentials_principal_class", "passkey_credentials", ["principal_class"])
    op.create_index("ix_passkey_credentials_principal_subject", "passkey_credentials", ["principal_subject"])
    op.create_index("ix_passkey_credentials_realm_key", "passkey_credentials", ["realm_key"])
    op.create_index("ix_passkey_credentials_status", "passkey_credentials", ["status"])
    op.create_index("ix_passkey_credentials_user_handle", "passkey_credentials", ["user_handle"])
    op.create_index(
        "ix_passkey_credentials_principal_active",
        "passkey_credentials",
        ["auth_realm_id", "principal_class", "principal_subject", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_passkey_credentials_principal_active", table_name="passkey_credentials")
    op.drop_index("ix_passkey_credentials_user_handle", table_name="passkey_credentials")
    op.drop_index("ix_passkey_credentials_status", table_name="passkey_credentials")
    op.drop_index("ix_passkey_credentials_realm_key", table_name="passkey_credentials")
    op.drop_index("ix_passkey_credentials_principal_subject", table_name="passkey_credentials")
    op.drop_index("ix_passkey_credentials_principal_class", table_name="passkey_credentials")
    op.drop_index("ix_passkey_credentials_credential_id_hash", table_name="passkey_credentials")
    op.drop_index("ix_passkey_credentials_auth_realm_id", table_name="passkey_credentials")
    op.drop_table("passkey_credentials")
