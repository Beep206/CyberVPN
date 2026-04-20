"""Add partner workspace accounts, roles, memberships, and legacy links.

Revision ID: 20260417_phase1_partner_workspace
Revises: 20260417_phase1_auth_realms
Create Date: 2026-04-17 23:55:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260417_phase1_partner_workspace"
down_revision: str | None = "20260417_phase1_auth_realms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "partner_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_key", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("legacy_owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_admin_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["legacy_owner_user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_partner_accounts_account_key"), "partner_accounts", ["account_key"], unique=True)
    op.create_index(
        op.f("ix_partner_accounts_legacy_owner_user_id"),
        "partner_accounts",
        ["legacy_owner_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_partner_accounts_created_by_admin_user_id"),
        "partner_accounts",
        ["created_by_admin_user_id"],
        unique=False,
    )

    op.create_table(
        "partner_account_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_key", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("permission_keys", sa.JSON(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_partner_account_roles_role_key"), "partner_account_roles", ["role_key"], unique=True)

    op.create_table(
        "partner_account_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("membership_status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("invited_by_admin_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["partner_account_roles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["invited_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("partner_account_id", "admin_user_id", name="uq_partner_account_users_account_admin_user"),
    )
    op.create_index(
        op.f("ix_partner_account_users_partner_account_id"),
        "partner_account_users",
        ["partner_account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_partner_account_users_admin_user_id"),
        "partner_account_users",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(op.f("ix_partner_account_users_role_id"), "partner_account_users", ["role_id"], unique=False)
    op.create_index(
        op.f("ix_partner_account_users_invited_by_admin_user_id"),
        "partner_account_users",
        ["invited_by_admin_user_id"],
        unique=False,
    )

    op.add_column("mobile_users", sa.Column("partner_account_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_mobile_users_partner_account_id"), "mobile_users", ["partner_account_id"], unique=False)
    op.create_foreign_key(
        "fk_mobile_users_partner_account_id",
        "mobile_users",
        "partner_accounts",
        ["partner_account_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("partner_codes", sa.Column("partner_account_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_partner_codes_partner_account_id"), "partner_codes", ["partner_account_id"], unique=False)
    op.create_foreign_key(
        "fk_partner_codes_partner_account_id",
        "partner_codes",
        "partner_accounts",
        ["partner_account_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("partner_earnings", sa.Column("partner_account_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(
        op.f("ix_partner_earnings_partner_account_id"),
        "partner_earnings",
        ["partner_account_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_partner_earnings_partner_account_id",
        "partner_earnings",
        "partner_accounts",
        ["partner_account_id"],
        ["id"],
        ondelete="SET NULL",
    )

    connection = op.get_bind()

    partner_roles = sa.table(
        "partner_account_roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("role_key", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("permission_keys", sa.JSON()),
        sa.column("is_system", sa.Boolean()),
    )
    op.bulk_insert(
        partner_roles,
        [
            {
                "id": uuid.uuid4(),
                "role_key": "owner",
                "display_name": "Owner",
                "description": "Full workspace access including member and revenue controls.",
                "permission_keys": [
                    "workspace_read",
                    "membership_read",
                    "membership_write",
                    "codes_read",
                    "codes_write",
                    "earnings_read",
                    "payouts_read",
                    "traffic_read",
                ],
                "is_system": True,
            },
            {
                "id": uuid.uuid4(),
                "role_key": "manager",
                "display_name": "Manager",
                "description": "Operational workspace manager with member and code controls.",
                "permission_keys": [
                    "workspace_read",
                    "membership_read",
                    "membership_write",
                    "codes_read",
                    "codes_write",
                    "earnings_read",
                ],
                "is_system": True,
            },
            {
                "id": uuid.uuid4(),
                "role_key": "finance",
                "display_name": "Finance",
                "description": "Finance operator with earnings and payout visibility.",
                "permission_keys": [
                    "workspace_read",
                    "membership_read",
                    "earnings_read",
                    "payouts_read",
                ],
                "is_system": True,
            },
            {
                "id": uuid.uuid4(),
                "role_key": "analyst",
                "display_name": "Analyst",
                "description": "Read-only operator for performance and code analytics.",
                "permission_keys": [
                    "workspace_read",
                    "codes_read",
                    "earnings_read",
                    "traffic_read",
                ],
                "is_system": True,
            },
            {
                "id": uuid.uuid4(),
                "role_key": "traffic_manager",
                "display_name": "Traffic Manager",
                "description": "Operator responsible for code and traffic surfaces.",
                "permission_keys": [
                    "workspace_read",
                    "codes_read",
                    "codes_write",
                    "traffic_read",
                ],
                "is_system": True,
            },
            {
                "id": uuid.uuid4(),
                "role_key": "support_manager",
                "display_name": "Support Manager",
                "description": "Operator with workspace and membership visibility.",
                "permission_keys": [
                    "workspace_read",
                    "membership_read",
                ],
                "is_system": True,
            },
        ],
    )

    mobile_users = sa.table(
        "mobile_users",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("email", sa.String()),
        sa.column("username", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("is_partner", sa.Boolean()),
    )
    partner_accounts = sa.table(
        "partner_accounts",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("account_key", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("legacy_owner_user_id", postgresql.UUID(as_uuid=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    rows = connection.execute(
        sa.select(
            mobile_users.c.id,
            mobile_users.c.email,
            mobile_users.c.username,
            mobile_users.c.created_at,
        ).where(mobile_users.c.is_partner.is_(True))
    ).fetchall()

    account_rows: list[dict[str, object]] = []
    for row in rows:
        account_id = uuid.uuid4()
        key_suffix = str(row.id).replace("-", "")[:8]
        account_rows.append(
            {
                "id": account_id,
                "account_key": f"legacy-partner-{key_suffix}",
                "display_name": row.username or row.email or f"Partner {key_suffix}",
                "legacy_owner_user_id": row.id,
                "created_at": row.created_at or datetime.now(UTC),
                "updated_at": row.created_at or datetime.now(UTC),
            }
        )

    if account_rows:
        op.bulk_insert(partner_accounts, account_rows)

        for row in account_rows:
            connection.execute(
                sa.text(
                    """
                    UPDATE mobile_users
                    SET partner_account_id = :partner_account_id
                    WHERE id = :mobile_user_id
                    """
                ),
                {"partner_account_id": row["id"], "mobile_user_id": row["legacy_owner_user_id"]},
            )
            connection.execute(
                sa.text(
                    """
                    UPDATE partner_codes
                    SET partner_account_id = :partner_account_id
                    WHERE partner_user_id = :mobile_user_id
                    """
                ),
                {"partner_account_id": row["id"], "mobile_user_id": row["legacy_owner_user_id"]},
            )
            connection.execute(
                sa.text(
                    """
                    UPDATE partner_earnings
                    SET partner_account_id = :partner_account_id
                    WHERE partner_user_id = :mobile_user_id
                    """
                ),
                {"partner_account_id": row["id"], "mobile_user_id": row["legacy_owner_user_id"]},
            )


def downgrade() -> None:
    op.drop_constraint("fk_partner_earnings_partner_account_id", "partner_earnings", type_="foreignkey")
    op.drop_index(op.f("ix_partner_earnings_partner_account_id"), table_name="partner_earnings")
    op.drop_column("partner_earnings", "partner_account_id")

    op.drop_constraint("fk_partner_codes_partner_account_id", "partner_codes", type_="foreignkey")
    op.drop_index(op.f("ix_partner_codes_partner_account_id"), table_name="partner_codes")
    op.drop_column("partner_codes", "partner_account_id")

    op.drop_constraint("fk_mobile_users_partner_account_id", "mobile_users", type_="foreignkey")
    op.drop_index(op.f("ix_mobile_users_partner_account_id"), table_name="mobile_users")
    op.drop_column("mobile_users", "partner_account_id")

    op.drop_index(op.f("ix_partner_account_users_invited_by_admin_user_id"), table_name="partner_account_users")
    op.drop_index(op.f("ix_partner_account_users_role_id"), table_name="partner_account_users")
    op.drop_index(op.f("ix_partner_account_users_admin_user_id"), table_name="partner_account_users")
    op.drop_index(op.f("ix_partner_account_users_partner_account_id"), table_name="partner_account_users")
    op.drop_table("partner_account_users")

    op.drop_index(op.f("ix_partner_account_roles_role_key"), table_name="partner_account_roles")
    op.drop_table("partner_account_roles")

    op.drop_index(op.f("ix_partner_accounts_created_by_admin_user_id"), table_name="partner_accounts")
    op.drop_index(op.f("ix_partner_accounts_legacy_owner_user_id"), table_name="partner_accounts")
    op.drop_index(op.f("ix_partner_accounts_account_key"), table_name="partner_accounts")
    op.drop_table("partner_accounts")
