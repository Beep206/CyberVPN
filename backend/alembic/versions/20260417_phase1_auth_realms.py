"""Add auth realms, principal sessions, and realm-aware admin identity fields.

Revision ID: 20260417_phase1_auth_realms
Revises: 20260417_phase1_storefront_core
Create Date: 2026-04-17 23:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260417_phase1_auth_realms"
down_revision: str | None = "20260417_phase1_storefront_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADMIN_REALM_ID = "2acd89fc-8e1d-5e93-9aa9-04e60428001a"
CUSTOMER_REALM_ID = "da9be308-c1c5-57d2-90d1-533503f2b68b"
PARTNER_REALM_ID = "a4de943e-6124-5f53-88c2-c41b1469e051"
SERVICE_REALM_ID = "e9c8debe-a352-5bef-abfc-b49b00c4e675"


def upgrade() -> None:
    op.create_table(
        "auth_realms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("realm_key", sa.String(length=50), nullable=False),
        sa.Column("realm_type", sa.String(length=20), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("audience", sa.String(length=120), nullable=False),
        sa.Column("cookie_namespace", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_realms_realm_key"), "auth_realms", ["realm_key"], unique=True)
    op.create_index(op.f("ix_auth_realms_realm_type"), "auth_realms", ["realm_type"], unique=False)
    op.create_index(op.f("ix_auth_realms_audience"), "auth_realms", ["audience"], unique=True)

    auth_realms = sa.table(
        "auth_realms",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("realm_key", sa.String()),
        sa.column("realm_type", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("audience", sa.String()),
        sa.column("cookie_namespace", sa.String()),
        sa.column("status", sa.String()),
        sa.column("is_default", sa.Boolean()),
    )
    op.bulk_insert(
        auth_realms,
        [
            {
                "id": ADMIN_REALM_ID,
                "realm_key": "admin",
                "realm_type": "admin",
                "display_name": "Admin Realm",
                "audience": "cybervpn:admin",
                "cookie_namespace": "admin",
                "status": "active",
                "is_default": True,
            },
            {
                "id": CUSTOMER_REALM_ID,
                "realm_key": "customer",
                "realm_type": "customer",
                "display_name": "Customer Realm",
                "audience": "cybervpn:customer",
                "cookie_namespace": "customer",
                "status": "active",
                "is_default": True,
            },
            {
                "id": PARTNER_REALM_ID,
                "realm_key": "partner",
                "realm_type": "partner",
                "display_name": "Partner Realm",
                "audience": "cybervpn:partner",
                "cookie_namespace": "partner",
                "status": "active",
                "is_default": True,
            },
            {
                "id": SERVICE_REALM_ID,
                "realm_key": "service",
                "realm_type": "service",
                "display_name": "Service Realm",
                "audience": "cybervpn:service",
                "cookie_namespace": "service",
                "status": "active",
                "is_default": True,
            },
        ],
    )

    op.add_column("storefronts", sa.Column("auth_realm_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_storefronts_auth_realm_id"), "storefronts", ["auth_realm_id"], unique=False)
    op.create_foreign_key(
        "fk_storefronts_auth_realm_id",
        "storefronts",
        "auth_realms",
        ["auth_realm_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("admin_users", sa.Column("auth_realm_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_admin_users_auth_realm_id"), "admin_users", ["auth_realm_id"], unique=False)
    op.create_foreign_key(
        "fk_admin_users_auth_realm_id",
        "admin_users",
        "auth_realms",
        ["auth_realm_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute("DROP INDEX IF EXISTS ix_admin_users_login")
    op.execute("DROP INDEX IF EXISTS ix_admin_users_email")
    op.execute("ALTER TABLE admin_users DROP CONSTRAINT IF EXISTS admin_users_login_key")
    op.execute("ALTER TABLE admin_users DROP CONSTRAINT IF EXISTS admin_users_email_key")
    op.create_index(op.f("ix_admin_users_login"), "admin_users", ["login"], unique=False)
    op.create_index(op.f("ix_admin_users_email"), "admin_users", ["email"], unique=False)
    op.create_unique_constraint("uq_admin_users_realm_login", "admin_users", ["auth_realm_id", "login"])
    op.create_unique_constraint("uq_admin_users_realm_email", "admin_users", ["auth_realm_id", "email"])
    op.execute(f"UPDATE admin_users SET auth_realm_id = '{ADMIN_REALM_ID}' WHERE auth_realm_id IS NULL")

    op.add_column("mobile_users", sa.Column("auth_realm_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_mobile_users_auth_realm_id"), "mobile_users", ["auth_realm_id"], unique=False)
    op.create_foreign_key(
        "fk_mobile_users_auth_realm_id",
        "mobile_users",
        "auth_realms",
        ["auth_realm_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(f"UPDATE mobile_users SET auth_realm_id = '{CUSTOMER_REALM_ID}' WHERE auth_realm_id IS NULL")

    op.create_table(
        "principal_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("auth_realm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal_subject", sa.String(length=255), nullable=False),
        sa.Column("principal_class", sa.String(length=32), nullable=False),
        sa.Column("audience", sa.String(length=120), nullable=False),
        sa.Column("scope_family", sa.String(length=50), nullable=False),
        sa.Column("access_token_jti", sa.String(length=64), nullable=True),
        sa.Column("refresh_token_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["refresh_token_id"], ["refresh_tokens.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_principal_sessions_auth_realm_id"), "principal_sessions", ["auth_realm_id"], unique=False)
    op.create_index(
        op.f("ix_principal_sessions_principal_subject"),
        "principal_sessions",
        ["principal_subject"],
        unique=False,
    )
    op.create_index(
        op.f("ix_principal_sessions_principal_class"),
        "principal_sessions",
        ["principal_class"],
        unique=False,
    )
    op.create_index(op.f("ix_principal_sessions_audience"), "principal_sessions", ["audience"], unique=False)
    op.create_index(
        op.f("ix_principal_sessions_access_token_jti"),
        "principal_sessions",
        ["access_token_jti"],
        unique=False,
    )
    op.create_index(
        op.f("ix_principal_sessions_refresh_token_id"),
        "principal_sessions",
        ["refresh_token_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_principal_sessions_refresh_token_id"), table_name="principal_sessions")
    op.drop_index(op.f("ix_principal_sessions_access_token_jti"), table_name="principal_sessions")
    op.drop_index(op.f("ix_principal_sessions_audience"), table_name="principal_sessions")
    op.drop_index(op.f("ix_principal_sessions_principal_class"), table_name="principal_sessions")
    op.drop_index(op.f("ix_principal_sessions_principal_subject"), table_name="principal_sessions")
    op.drop_index(op.f("ix_principal_sessions_auth_realm_id"), table_name="principal_sessions")
    op.drop_table("principal_sessions")

    op.drop_constraint("fk_mobile_users_auth_realm_id", "mobile_users", type_="foreignkey")
    op.drop_index(op.f("ix_mobile_users_auth_realm_id"), table_name="mobile_users")
    op.drop_column("mobile_users", "auth_realm_id")

    op.drop_constraint("uq_admin_users_realm_email", "admin_users", type_="unique")
    op.drop_constraint("uq_admin_users_realm_login", "admin_users", type_="unique")
    op.drop_constraint("fk_admin_users_auth_realm_id", "admin_users", type_="foreignkey")
    op.drop_index(op.f("ix_admin_users_auth_realm_id"), table_name="admin_users")
    op.execute("DROP INDEX IF EXISTS ix_admin_users_email")
    op.execute("DROP INDEX IF EXISTS ix_admin_users_login")
    op.create_index("ix_admin_users_login", "admin_users", ["login"], unique=True)
    op.create_index("ix_admin_users_email", "admin_users", ["email"], unique=True)
    op.drop_column("admin_users", "auth_realm_id")

    op.drop_constraint("fk_storefronts_auth_realm_id", "storefronts", type_="foreignkey")
    op.drop_index(op.f("ix_storefronts_auth_realm_id"), table_name="storefronts")
    op.drop_column("storefronts", "auth_realm_id")

    op.drop_index(op.f("ix_auth_realms_audience"), table_name="auth_realms")
    op.drop_index(op.f("ix_auth_realms_realm_type"), table_name="auth_realms")
    op.drop_index(op.f("ix_auth_realms_realm_key"), table_name="auth_realms")
    op.drop_table("auth_realms")
