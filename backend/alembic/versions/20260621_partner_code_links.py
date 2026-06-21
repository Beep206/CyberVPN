"""Add durable partner code links.

Revision ID: 20260621_partner_code_links
Revises: 20260621_partner_attr_hardening
Create Date: 2026-06-21
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260621_partner_code_links"
down_revision: str | Sequence[str] | None = "20260621_partner_attr_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PUBLIC_SLUG_ALPHABET = "abcdefghijklmnopqrstuvwxyz23456789"
_DESTINATION_PATHS = {
    "register": "/register",
    "pricing": "/pricing",
    "checkout": "/checkout",
    "download": "/download",
}
_APPROVED_CAMPAIGN_PREFIXES = ("/campaigns/", "/campaign/", "/landing/", "/lp/")
_APPROVED_STOREFRONT_PREFIXES = ("/storefronts/", "/storefront/", "/checkout")


def _uuid_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.Uuid()


def _json_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_default(payload: str) -> sa.TextClause:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.text(f"'{payload}'::jsonb")
    return sa.text(f"'{payload}'")


def _generate_public_slug() -> str:
    body = "".join(secrets.choice(_PUBLIC_SLUG_ALPHABET) for _ in range(24))
    return f"px_{body}"


def upgrade() -> None:
    bind = op.get_bind()
    uuid_type = _uuid_type()
    json_type = _json_type()

    op.create_table(
        "partner_code_links",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("public_slug", sa.String(length=80), nullable=False),
        sa.Column("partner_code_id", uuid_type, nullable=False),
        sa.Column("partner_account_id", uuid_type, nullable=False),
        sa.Column("link_kind", sa.String(length=40), nullable=False, server_default="deep_link"),
        sa.Column("destination_key", sa.String(length=80), nullable=False, server_default="register"),
        sa.Column("destination_path", sa.String(length=500), nullable=False, server_default="/register"),
        sa.Column("locale", sa.String(length=16), nullable=True),
        sa.Column("sale_channel", sa.String(length=40), nullable=True),
        sa.Column("campaign_params", json_type, nullable=False, server_default=_json_default("{}")),
        sa.Column("sub_ids", json_type, nullable=False, server_default=_json_default("{}")),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("active_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_admin_user_id", uuid_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["partner_code_id"], ["partner_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_slug", name="uq_partner_code_links_public_slug"),
    )
    op.create_index("ix_partner_code_links_public_slug", "partner_code_links", ["public_slug"], unique=True)
    op.create_index("ix_partner_code_links_partner_code_id", "partner_code_links", ["partner_code_id"])
    op.create_index("ix_partner_code_links_partner_account_id", "partner_code_links", ["partner_account_id"])
    op.create_index("ix_partner_code_links_link_kind", "partner_code_links", ["link_kind"])
    op.create_index("ix_partner_code_links_destination_key", "partner_code_links", ["destination_key"])
    op.create_index("ix_partner_code_links_sale_channel", "partner_code_links", ["sale_channel"])
    op.create_index("ix_partner_code_links_status", "partner_code_links", ["status"])
    op.create_index("ix_partner_code_links_expires_at", "partner_code_links", ["expires_at"])
    op.create_index(
        "ix_partner_code_links_created_by_admin_user_id",
        "partner_code_links",
        ["created_by_admin_user_id"],
    )

    op.add_column("partner_attribution_sessions", sa.Column("partner_code_link_id", uuid_type, nullable=True))
    op.create_foreign_key(
        "fk_partner_attr_sessions_partner_code_link_id",
        "partner_attribution_sessions",
        "partner_code_links",
        ["partner_code_link_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_partner_attr_sessions_partner_code_link_id",
        "partner_attribution_sessions",
        ["partner_code_link_id"],
    )

    _backfill_default_links(bind)


def downgrade() -> None:
    op.drop_index("ix_partner_attr_sessions_partner_code_link_id", table_name="partner_attribution_sessions")
    op.drop_constraint(
        "fk_partner_attr_sessions_partner_code_link_id",
        "partner_attribution_sessions",
        type_="foreignkey",
    )
    op.drop_column("partner_attribution_sessions", "partner_code_link_id")

    op.drop_index("ix_partner_code_links_created_by_admin_user_id", table_name="partner_code_links")
    op.drop_index("ix_partner_code_links_expires_at", table_name="partner_code_links")
    op.drop_index("ix_partner_code_links_status", table_name="partner_code_links")
    op.drop_index("ix_partner_code_links_sale_channel", table_name="partner_code_links")
    op.drop_index("ix_partner_code_links_destination_key", table_name="partner_code_links")
    op.drop_index("ix_partner_code_links_link_kind", table_name="partner_code_links")
    op.drop_index("ix_partner_code_links_partner_account_id", table_name="partner_code_links")
    op.drop_index("ix_partner_code_links_partner_code_id", table_name="partner_code_links")
    op.drop_index("ix_partner_code_links_public_slug", table_name="partner_code_links")
    op.drop_table("partner_code_links")


def _backfill_default_links(bind: sa.Connection) -> None:
    existing_slugs = {
        str(row[0])
        for row in bind.execute(
            sa.text(
                """
                SELECT public_slug
                FROM partner_codes
                WHERE public_slug IS NOT NULL
                """
            )
        )
        if row[0]
    }
    rows = bind.execute(
        sa.text(
            """
            SELECT id, public_slug, public_token_hash, partner_account_id, destination_path, active_from, expires_at
            FROM partner_codes
            WHERE partner_account_id IS NOT NULL
            ORDER BY created_at, id
            """
        )
    ).mappings()
    link_rows: list[dict[str, object]] = []
    for row in rows:
        public_slug = str(row["public_slug"] or "")
        if not public_slug:
            public_slug = _unique_slug(existing_slugs)
            bind.execute(
                sa.text(
                    """
                    UPDATE partner_codes
                    SET public_slug = :public_slug,
                        public_token_hash = COALESCE(public_token_hash, :public_token_hash)
                    WHERE id = :id
                    """
                ),
                {
                    "id": row["id"],
                    "public_slug": public_slug,
                    "public_token_hash": hashlib.sha256(public_slug.encode("utf-8")).hexdigest(),
                },
            )
        destination_key, destination_path = _resolve_destination(row["destination_path"])
        link_rows.append(
            {
                "id": uuid.uuid4(),
                "public_slug": public_slug,
                "partner_code_id": row["id"],
                "partner_account_id": row["partner_account_id"],
                "link_kind": "default",
                "destination_key": destination_key,
                "destination_path": destination_path,
                "locale": None,
                "sale_channel": None,
                "campaign_params": {},
                "sub_ids": {},
                "status": "active",
                "active_from": row["active_from"],
                "expires_at": row["expires_at"],
                "created_by_admin_user_id": None,
            }
        )
    if not link_rows:
        return
    partner_code_links = sa.table(
        "partner_code_links",
        sa.column("id", _uuid_type()),
        sa.column("public_slug", sa.String()),
        sa.column("partner_code_id", _uuid_type()),
        sa.column("partner_account_id", _uuid_type()),
        sa.column("link_kind", sa.String()),
        sa.column("destination_key", sa.String()),
        sa.column("destination_path", sa.String()),
        sa.column("locale", sa.String()),
        sa.column("sale_channel", sa.String()),
        sa.column("campaign_params", _json_type()),
        sa.column("sub_ids", _json_type()),
        sa.column("status", sa.String()),
        sa.column("active_from", sa.DateTime(timezone=True)),
        sa.column("expires_at", sa.DateTime(timezone=True)),
        sa.column("created_by_admin_user_id", _uuid_type()),
    )
    bind.execute(partner_code_links.insert(), link_rows)


def _unique_slug(existing_slugs: set[str]) -> str:
    slug = _generate_public_slug()
    while slug in existing_slugs:
        slug = _generate_public_slug()
    existing_slugs.add(slug)
    return slug


def _resolve_destination(destination_path: object) -> tuple[str, str]:
    raw_path = str(destination_path or "").strip()
    if not raw_path or raw_path.startswith(("http://", "https://", "//")):
        return "register", "/register"
    if not raw_path.startswith("/"):
        raw_path = f"/{raw_path}"
    raw_path = raw_path[:500]
    for key, path in _DESTINATION_PATHS.items():
        if raw_path == path:
            return key, path
    if raw_path.startswith(_APPROVED_CAMPAIGN_PREFIXES):
        return "approved_campaign_landing", raw_path
    if raw_path.startswith(_APPROVED_STOREFRONT_PREFIXES):
        return "approved_storefront", raw_path
    return "register", "/register"
