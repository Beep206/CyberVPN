"""Session device and refresh rotation schema foundation.

Revision ID: 20260609_session_device_refresh
Revises: 20260531_offer_channels_jsonb, 20260603_passkey_credentials
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260609_session_device_refresh"
down_revision: str | Sequence[str] | None = (
    "20260531_offer_channels_jsonb",
    "20260603_passkey_credentials",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.Uuid()


def upgrade() -> None:
    uuid_type = _uuid_type()

    op.create_table(
        "user_devices",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("auth_realm_id", uuid_type, nullable=False),
        sa.Column("principal_subject", sa.String(length=255), nullable=False),
        sa.Column("principal_class", sa.String(length=32), nullable=False),
        sa.Column("audience", sa.String(length=120), nullable=False),
        sa.Column("device_key_hash", sa.String(length=64), nullable=False),
        sa.Column("device_label", sa.String(length=120), nullable=True),
        sa.Column("platform", sa.String(length=40), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_devices_auth_realm_id", "user_devices", ["auth_realm_id"])
    op.create_index("ix_user_devices_principal_subject", "user_devices", ["principal_subject"])
    op.create_index("ix_user_devices_principal_class", "user_devices", ["principal_class"])
    op.create_index("ix_user_devices_audience", "user_devices", ["audience"])
    op.create_index(
        "ix_user_devices_principal",
        "user_devices",
        ["auth_realm_id", "principal_class", "principal_subject"],
    )
    op.create_index("ix_user_devices_last_seen_at", "user_devices", ["last_seen_at"])
    op.create_index("ix_user_devices_revoked_at", "user_devices", ["revoked_at"])
    op.create_index(
        "uq_user_devices_active_principal_device_key",
        "user_devices",
        ["auth_realm_id", "principal_class", "principal_subject", "device_key_hash"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )

    op.add_column("principal_sessions", sa.Column("user_device_id", uuid_type, nullable=True))
    op.add_column("principal_sessions", sa.Column("current_refresh_token_id", uuid_type, nullable=True))
    op.create_index("ix_principal_sessions_user_device_id", "principal_sessions", ["user_device_id"])
    op.create_index(
        "ix_principal_sessions_user_device_status",
        "principal_sessions",
        ["user_device_id", "status"],
    )
    op.create_index(
        "ix_principal_sessions_current_refresh_token_id",
        "principal_sessions",
        ["current_refresh_token_id"],
    )
    op.create_foreign_key(
        "fk_principal_sessions_user_device_id",
        "principal_sessions",
        "user_devices",
        ["user_device_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_principal_sessions_current_refresh_token_id",
        "principal_sessions",
        "refresh_tokens",
        ["current_refresh_token_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("refresh_tokens", sa.Column("revoked_reason", sa.String(length=64), nullable=True))
    op.add_column("refresh_tokens", sa.Column("jti", sa.String(length=64), nullable=True))
    op.add_column("refresh_tokens", sa.Column("family_id", uuid_type, nullable=True))
    op.add_column("refresh_tokens", sa.Column("parent_token_id", uuid_type, nullable=True))
    op.add_column("refresh_tokens", sa.Column("principal_session_id", uuid_type, nullable=True))
    op.add_column("refresh_tokens", sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("refresh_tokens", sa.Column("replaced_by_token_id", uuid_type, nullable=True))
    op.create_index(
        "uq_refresh_tokens_jti",
        "refresh_tokens",
        ["jti"],
        unique=True,
        postgresql_where=sa.text("jti IS NOT NULL"),
    )
    op.create_index("ix_refresh_tokens_principal_session_id", "refresh_tokens", ["principal_session_id"])
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])
    op.create_index("ix_refresh_tokens_parent_token_id", "refresh_tokens", ["parent_token_id"])
    op.create_index("ix_refresh_tokens_replaced_by_token_id", "refresh_tokens", ["replaced_by_token_id"])
    op.create_index("ix_refresh_tokens_consumed_at", "refresh_tokens", ["consumed_at"])
    op.create_index("ix_refresh_tokens_session_family", "refresh_tokens", ["principal_session_id", "family_id"])
    op.create_foreign_key(
        "fk_refresh_tokens_parent_token_id",
        "refresh_tokens",
        "refresh_tokens",
        ["parent_token_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_refresh_tokens_principal_session_id",
        "refresh_tokens",
        "principal_sessions",
        ["principal_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_refresh_tokens_replaced_by_token_id",
        "refresh_tokens",
        "refresh_tokens",
        ["replaced_by_token_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_refresh_tokens_replaced_by_token_id", "refresh_tokens", type_="foreignkey")
    op.drop_constraint("fk_refresh_tokens_principal_session_id", "refresh_tokens", type_="foreignkey")
    op.drop_constraint("fk_refresh_tokens_parent_token_id", "refresh_tokens", type_="foreignkey")
    op.drop_index("ix_refresh_tokens_session_family", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_consumed_at", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_replaced_by_token_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_parent_token_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_principal_session_id", table_name="refresh_tokens")
    op.drop_index("uq_refresh_tokens_jti", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "replaced_by_token_id")
    op.drop_column("refresh_tokens", "consumed_at")
    op.drop_column("refresh_tokens", "principal_session_id")
    op.drop_column("refresh_tokens", "parent_token_id")
    op.drop_column("refresh_tokens", "family_id")
    op.drop_column("refresh_tokens", "jti")
    op.drop_column("refresh_tokens", "revoked_reason")

    op.drop_constraint("fk_principal_sessions_current_refresh_token_id", "principal_sessions", type_="foreignkey")
    op.drop_constraint("fk_principal_sessions_user_device_id", "principal_sessions", type_="foreignkey")
    op.drop_index("ix_principal_sessions_current_refresh_token_id", table_name="principal_sessions")
    op.drop_index("ix_principal_sessions_user_device_status", table_name="principal_sessions")
    op.drop_index("ix_principal_sessions_user_device_id", table_name="principal_sessions")
    op.drop_column("principal_sessions", "current_refresh_token_id")
    op.drop_column("principal_sessions", "user_device_id")

    op.drop_index("uq_user_devices_active_principal_device_key", table_name="user_devices")
    op.drop_index("ix_user_devices_revoked_at", table_name="user_devices")
    op.drop_index("ix_user_devices_last_seen_at", table_name="user_devices")
    op.drop_index("ix_user_devices_principal", table_name="user_devices")
    op.drop_index("ix_user_devices_audience", table_name="user_devices")
    op.drop_index("ix_user_devices_principal_class", table_name="user_devices")
    op.drop_index("ix_user_devices_principal_subject", table_name="user_devices")
    op.drop_index("ix_user_devices_auth_realm_id", table_name="user_devices")
    op.drop_table("user_devices")
