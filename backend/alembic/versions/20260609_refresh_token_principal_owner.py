"""Add principal owner metadata to refresh tokens.

Revision ID: 20260609_refresh_token_owner
Revises: 20260609_user_devices_audit
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260609_refresh_token_owner"
down_revision: str | Sequence[str] | None = "20260609_user_devices_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.Uuid()


def upgrade() -> None:
    uuid_type = _uuid_type()

    op.drop_constraint("fk_refresh_tokens_user_id_admin_users", "refresh_tokens", type_="foreignkey")

    op.add_column("refresh_tokens", sa.Column("auth_realm_id", uuid_type, nullable=True))
    op.add_column("refresh_tokens", sa.Column("principal_class", sa.String(length=32), nullable=True))
    op.add_column("refresh_tokens", sa.Column("principal_subject", sa.String(length=255), nullable=True))
    op.add_column("refresh_tokens", sa.Column("audience", sa.String(length=120), nullable=True))
    op.add_column("refresh_tokens", sa.Column("scope_family", sa.String(length=50), nullable=True))

    op.execute(
        """
        insert into auth_realms (
            id,
            realm_key,
            realm_type,
            display_name,
            audience,
            cookie_namespace,
            status,
            is_default,
            created_at,
            updated_at
        )
        values (
            '2acd89fc-8e1d-5e93-9aa9-04e60428001a',
            'admin',
            'admin',
            'Admin Realm',
            'cybervpn:admin',
            'admin',
            'active',
            true,
            now(),
            now()
        )
        on conflict (realm_key) do nothing
        """
    )
    op.execute(
        """
        update refresh_tokens rt
        set
            auth_realm_id = coalesce(ar.id, default_ar.id),
            principal_class = 'admin',
            principal_subject = rt.user_id::text,
            audience = coalesce(ar.audience, default_ar.audience),
            scope_family = coalesce(ar.realm_type, default_ar.realm_type)
        from admin_users au
        join auth_realms default_ar
          on default_ar.realm_key = 'admin'
        left join auth_realms ar
          on ar.id = au.auth_realm_id
        where rt.user_id = au.id
        """
    )
    op.execute(
        """
        update refresh_tokens rt
        set
            auth_realm_id = ar.id,
            principal_class = 'admin',
            principal_subject = rt.user_id::text,
            audience = ar.audience,
            scope_family = ar.realm_type
        from auth_realms ar
        where rt.auth_realm_id is null
          and ar.realm_key = 'admin'
        """
    )

    op.alter_column("refresh_tokens", "auth_realm_id", existing_type=uuid_type, nullable=False)
    op.alter_column("refresh_tokens", "principal_class", existing_type=sa.String(length=32), nullable=False)
    op.alter_column("refresh_tokens", "principal_subject", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("refresh_tokens", "audience", existing_type=sa.String(length=120), nullable=False)
    op.alter_column("refresh_tokens", "scope_family", existing_type=sa.String(length=50), nullable=False)

    op.create_index("ix_refresh_tokens_auth_realm_id", "refresh_tokens", ["auth_realm_id"])
    op.create_index("ix_refresh_tokens_principal_class", "refresh_tokens", ["principal_class"])
    op.create_index("ix_refresh_tokens_principal_subject", "refresh_tokens", ["principal_subject"])
    op.create_index("ix_refresh_tokens_audience", "refresh_tokens", ["audience"])
    op.create_index("ix_refresh_tokens_scope_family", "refresh_tokens", ["scope_family"])
    op.create_index(
        "ix_refresh_tokens_principal_owner",
        "refresh_tokens",
        ["principal_class", "principal_subject", "auth_realm_id"],
    )
    op.create_check_constraint(
        "ck_refresh_tokens_principal_class",
        "refresh_tokens",
        "principal_class in ('admin', 'partner_operator', 'customer')",
    )
    op.create_check_constraint(
        "ck_refresh_tokens_principal_subject_nonempty",
        "refresh_tokens",
        "principal_subject <> ''",
    )
    op.create_check_constraint(
        "ck_refresh_tokens_audience_nonempty",
        "refresh_tokens",
        "audience <> ''",
    )
    op.create_check_constraint(
        "ck_refresh_tokens_scope_family_nonempty",
        "refresh_tokens",
        "scope_family <> ''",
    )
    op.create_foreign_key(
        "fk_refresh_tokens_auth_realm_id",
        "refresh_tokens",
        "auth_realms",
        ["auth_realm_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_refresh_tokens_auth_realm_id", "refresh_tokens", type_="foreignkey")
    op.drop_constraint("ck_refresh_tokens_scope_family_nonempty", "refresh_tokens", type_="check")
    op.drop_constraint("ck_refresh_tokens_audience_nonempty", "refresh_tokens", type_="check")
    op.drop_constraint("ck_refresh_tokens_principal_subject_nonempty", "refresh_tokens", type_="check")
    op.drop_constraint("ck_refresh_tokens_principal_class", "refresh_tokens", type_="check")
    op.drop_index("ix_refresh_tokens_principal_owner", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_scope_family", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_audience", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_principal_subject", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_principal_class", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_auth_realm_id", table_name="refresh_tokens")

    op.execute("delete from refresh_tokens where principal_class <> 'admin'")
    op.execute(
        """
        delete from refresh_tokens rt
        where not exists (
            select 1
            from admin_users au
            where au.id = rt.user_id
        )
        """
    )

    op.drop_column("refresh_tokens", "scope_family")
    op.drop_column("refresh_tokens", "audience")
    op.drop_column("refresh_tokens", "principal_subject")
    op.drop_column("refresh_tokens", "principal_class")
    op.drop_column("refresh_tokens", "auth_realm_id")

    op.create_foreign_key(
        "fk_refresh_tokens_user_id_admin_users",
        "refresh_tokens",
        "admin_users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
