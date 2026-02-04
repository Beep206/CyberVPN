"""Add mobile auth tables.

Revision ID: 20260205_mobile_auth
Revises:
Create Date: 2026-02-05

Creates mobile_users and mobile_devices tables for mobile app authentication.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260205_mobile_auth"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create mobile_users table
    op.create_table(
        "mobile_users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("username", sa.String(50), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_username", sa.String(100), nullable=True),
        sa.Column("remnawave_uuid", sa.String(36), nullable=True),
        sa.Column("subscription_url", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("status", sa.String(20), nullable=False, default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mobile_users")),
        sa.UniqueConstraint("email", name=op.f("uq_mobile_users_email")),
        sa.UniqueConstraint("username", name=op.f("uq_mobile_users_username")),
        sa.UniqueConstraint("telegram_id", name=op.f("uq_mobile_users_telegram_id")),
        sa.UniqueConstraint("remnawave_uuid", name=op.f("uq_mobile_users_remnawave_uuid")),
    )
    op.create_index(op.f("ix_mobile_users_email"), "mobile_users", ["email"])
    op.create_index(op.f("ix_mobile_users_telegram_id"), "mobile_users", ["telegram_id"])
    op.create_index(op.f("ix_mobile_users_remnawave_uuid"), "mobile_users", ["remnawave_uuid"])

    # Create mobile_devices table
    op.create_table(
        "mobile_devices",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("device_id", sa.String(36), nullable=False),
        sa.Column("platform", sa.String(10), nullable=False),
        sa.Column("platform_id", sa.String(255), nullable=False),
        sa.Column("os_version", sa.String(20), nullable=False),
        sa.Column("app_version", sa.String(20), nullable=False),
        sa.Column("device_model", sa.String(100), nullable=False),
        sa.Column("push_token", sa.String(512), nullable=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mobile_devices")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["mobile_users.id"],
            name=op.f("fk_mobile_devices_user_id_mobile_users"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(op.f("ix_mobile_devices_device_id"), "mobile_devices", ["device_id"])
    op.create_index(op.f("ix_mobile_devices_user_id"), "mobile_devices", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_mobile_devices_user_id"), table_name="mobile_devices")
    op.drop_index(op.f("ix_mobile_devices_device_id"), table_name="mobile_devices")
    op.drop_table("mobile_devices")

    op.drop_index(op.f("ix_mobile_users_remnawave_uuid"), table_name="mobile_users")
    op.drop_index(op.f("ix_mobile_users_telegram_id"), table_name="mobile_users")
    op.drop_index(op.f("ix_mobile_users_email"), table_name="mobile_users")
    op.drop_table("mobile_users")
