"""Partner attribution remaining hardening fixes.

Revision ID: 20260620_partner_attr_remaining
Revises: 20260620_partner_attribution_v2
Create Date: 2026-06-20
"""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260620_partner_attr_remaining"
down_revision: str | Sequence[str] | None = "20260620_partner_attribution_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PUBLIC_SLUG_ALPHABET = "abcdefghijklmnopqrstuvwxyz23456789"


def _uuid_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.Uuid()


def _json_default(payload: str) -> sa.TextClause:
    return sa.text(f"'{payload}'")


def _generate_public_slug() -> str:
    body = "".join(secrets.choice(_PUBLIC_SLUG_ALPHABET) for _ in range(24))
    return f"px_{body}"


def upgrade() -> None:
    bind = op.get_bind()
    uuid_type = _uuid_type()

    op.add_column("partner_codes", sa.Column("public_slug", sa.String(length=80), nullable=True))
    existing_slugs: set[str] = set()
    for row in bind.execute(sa.text("SELECT id FROM partner_codes ORDER BY created_at, id")).mappings():
        slug = _generate_public_slug()
        while slug in existing_slugs:
            slug = _generate_public_slug()
        existing_slugs.add(slug)
        bind.execute(
            sa.text(
                """
                UPDATE partner_codes
                SET public_slug = :slug,
                    public_token_hash = :token_hash
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "slug": slug,
                "token_hash": hashlib.sha256(slug.encode("utf-8")).hexdigest(),
            },
        )
    op.create_index("ix_partner_codes_public_slug", "partner_codes", ["public_slug"], unique=True)

    op.drop_index("ix_partner_attr_sessions_token_hash", table_name="partner_attribution_sessions")
    if bind.dialect.name != "sqlite":
        op.drop_constraint(
            "uq_partner_attr_sessions_token_hash",
            "partner_attribution_sessions",
            type_="unique",
        )
    op.alter_column(
        "partner_attribution_sessions",
        "token_hash",
        new_column_name="session_token_hash",
        existing_type=sa.String(length=128),
        existing_nullable=False,
        nullable=True,
    )
    op.add_column(
        "partner_attribution_sessions",
        sa.Column("transfer_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "partner_attribution_sessions",
        sa.Column("transfer_consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("partner_attribution_sessions", sa.Column("destination_path", sa.String(length=500), nullable=True))
    op.add_column(
        "partner_attribution_sessions",
        sa.Column("locale", sa.String(length=16), server_default="ru-RU", nullable=False),
    )
    op.add_column("partner_attribution_sessions", sa.Column("sale_channel", sa.String(length=40), nullable=True))
    op.add_column(
        "partner_attribution_sessions",
        sa.Column("sub_ids", sa.JSON(), server_default=_json_default("{}"), nullable=False),
    )
    op.add_column("partner_attribution_sessions", sa.Column("click_id", sa.String(length=160), nullable=True))
    op.add_column("partner_attribution_sessions", sa.Column("browser_key_hash", sa.String(length=128), nullable=True))
    op.add_column(
        "partner_attribution_sessions",
        sa.Column("rejection_reason_code", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "partner_attribution_sessions",
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "partner_attribution_sessions",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    bind.execute(
        sa.text(
            """
            UPDATE partner_attribution_sessions
            SET transfer_expires_at = COALESCE(transfer_expires_at, created_at + INTERVAL '15 minutes'),
                first_seen_at = COALESCE(first_seen_at, created_at),
                last_seen_at = COALESCE(last_seen_at, transferred_at, claimed_at, created_at)
            """
        )
        if bind.dialect.name == "postgresql"
        else sa.text(
            """
            UPDATE partner_attribution_sessions
            SET transfer_expires_at = COALESCE(transfer_expires_at, datetime(created_at, '+15 minutes')),
                first_seen_at = COALESCE(first_seen_at, created_at),
                last_seen_at = COALESCE(last_seen_at, transferred_at, claimed_at, created_at)
            """
        )
    )
    op.create_index(
        "ix_partner_attr_sessions_session_token_hash",
        "partner_attribution_sessions",
        ["session_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_partner_attr_sessions_transfer_expires_at",
        "partner_attribution_sessions",
        ["transfer_expires_at"],
    )
    op.create_index("ix_partner_attr_sessions_sale_channel", "partner_attribution_sessions", ["sale_channel"])
    op.create_index("ix_partner_attr_sessions_click_id", "partner_attribution_sessions", ["click_id"])
    op.create_index(
        "ix_partner_attr_sessions_browser_key_hash",
        "partner_attribution_sessions",
        ["browser_key_hash"],
    )
    op.create_index("ix_partner_attr_sessions_last_seen_at", "partner_attribution_sessions", ["last_seen_at"])

    op.create_table(
        "partner_code_events",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("partner_code_id", uuid_type, nullable=False),
        sa.Column("partner_account_id", uuid_type, nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("previous_status", sa.String(length=24), nullable=True),
        sa.Column("next_status", sa.String(length=24), nullable=True),
        sa.Column("reason_code", sa.String(length=120), nullable=True),
        sa.Column("actor_principal_id", uuid_type, nullable=True),
        sa.Column("event_payload", sa.JSON(), server_default=_json_default("{}"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["partner_code_id"], ["partner_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_partner_code_events_partner_code_id", "partner_code_events", ["partner_code_id"])
    op.create_index("ix_partner_code_events_partner_account_id", "partner_code_events", ["partner_account_id"])
    op.create_index("ix_partner_code_events_event_type", "partner_code_events", ["event_type"])
    op.create_index("ix_partner_code_events_actor_principal_id", "partner_code_events", ["actor_principal_id"])

    op.create_table(
        "api_idempotency_records",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("scope", sa.String(length=120), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", uuid_type, nullable=True),
        sa.Column("request_hash", sa.String(length=128), nullable=True),
        sa.Column("response_payload", sa.JSON(), server_default=_json_default("{}"), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="completed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "idempotency_key", name="uq_api_idempotency_records_scope_key"),
    )
    op.create_index("ix_api_idempotency_records_scope", "api_idempotency_records", ["scope"])
    op.create_index("ix_api_idempotency_records_resource_id", "api_idempotency_records", ["resource_id"])
    op.create_index("ix_api_idempotency_records_created_at", "api_idempotency_records", ["created_at"])
    op.create_index("ix_api_idempotency_records_expires_at", "api_idempotency_records", ["expires_at"])

    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_customer_commercial_bindings_active_global_scope",
            "customer_commercial_bindings",
            ["user_id", "binding_type"],
            unique=True,
            postgresql_where=sa.text("binding_status = 'active' AND storefront_id IS NULL"),
        )
        op.create_index(
            "uq_customer_commercial_bindings_active_storefront_scope",
            "customer_commercial_bindings",
            ["user_id", "binding_type", "storefront_id"],
            unique=True,
            postgresql_where=sa.text("binding_status = 'active' AND storefront_id IS NOT NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index(
            "uq_customer_commercial_bindings_active_storefront_scope",
            table_name="customer_commercial_bindings",
        )
        op.drop_index("uq_customer_commercial_bindings_active_global_scope", table_name="customer_commercial_bindings")

    op.drop_index("ix_api_idempotency_records_expires_at", table_name="api_idempotency_records")
    op.drop_index("ix_api_idempotency_records_created_at", table_name="api_idempotency_records")
    op.drop_index("ix_api_idempotency_records_resource_id", table_name="api_idempotency_records")
    op.drop_index("ix_api_idempotency_records_scope", table_name="api_idempotency_records")
    op.drop_table("api_idempotency_records")

    op.drop_index("ix_partner_code_events_actor_principal_id", table_name="partner_code_events")
    op.drop_index("ix_partner_code_events_event_type", table_name="partner_code_events")
    op.drop_index("ix_partner_code_events_partner_account_id", table_name="partner_code_events")
    op.drop_index("ix_partner_code_events_partner_code_id", table_name="partner_code_events")
    op.drop_table("partner_code_events")

    op.drop_index("ix_partner_attr_sessions_last_seen_at", table_name="partner_attribution_sessions")
    op.drop_index("ix_partner_attr_sessions_browser_key_hash", table_name="partner_attribution_sessions")
    op.drop_index("ix_partner_attr_sessions_click_id", table_name="partner_attribution_sessions")
    op.drop_index("ix_partner_attr_sessions_sale_channel", table_name="partner_attribution_sessions")
    op.drop_index("ix_partner_attr_sessions_transfer_expires_at", table_name="partner_attribution_sessions")
    op.drop_index("ix_partner_attr_sessions_session_token_hash", table_name="partner_attribution_sessions")
    if bind.dialect.name != "sqlite":
        op.create_unique_constraint(
            "uq_partner_attr_sessions_token_hash",
            "partner_attribution_sessions",
            ["session_token_hash"],
        )
    op.drop_column("partner_attribution_sessions", "last_seen_at")
    op.drop_column("partner_attribution_sessions", "first_seen_at")
    op.drop_column("partner_attribution_sessions", "rejection_reason_code")
    op.drop_column("partner_attribution_sessions", "browser_key_hash")
    op.drop_column("partner_attribution_sessions", "click_id")
    op.drop_column("partner_attribution_sessions", "sub_ids")
    op.drop_column("partner_attribution_sessions", "sale_channel")
    op.drop_column("partner_attribution_sessions", "locale")
    op.drop_column("partner_attribution_sessions", "destination_path")
    op.drop_column("partner_attribution_sessions", "transfer_consumed_at")
    op.drop_column("partner_attribution_sessions", "transfer_expires_at")
    op.alter_column(
        "partner_attribution_sessions",
        "session_token_hash",
        new_column_name="token_hash",
        existing_type=sa.String(length=128),
        existing_nullable=True,
        nullable=False,
    )
    op.create_index("ix_partner_attr_sessions_token_hash", "partner_attribution_sessions", ["token_hash"])

    op.drop_index("ix_partner_codes_public_slug", table_name="partner_codes")
    op.drop_column("partner_codes", "public_slug")
