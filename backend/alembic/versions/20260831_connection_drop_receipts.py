"""Add durable Remnawave connection-drop receipts and exclusive grants.

Revision ID: 20260831_drop_receipts
Revises: 20260830_webhook_hmac_cleanup
Create Date: 2026-08-31

The receipt table is expand-only application state. It stores only
domain-separated HMACs, never raw idempotency keys, raw scopes, provider
payloads, or IP addresses. Active node and service-identity grants are made
exclusive across partner workspaces before partner connection reads/drops can
be enabled safely. Ambiguous receipts deliberately have no expiry; only known
terminal outcomes receive a retention deadline.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "20260831_drop_receipts"
down_revision: str | Sequence[str] | None = "20260830_webhook_hmac_cleanup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_RESOURCE_TYPES = "'node', 'host', 'profile', 'squad', 'tag', 'integration', 'shared_list'"
_NEW_RESOURCE_TYPES = _OLD_RESOURCE_TYPES + ", 'service_identity'"
_RECEIPT_TABLE = "remnawave_connection_drop_receipts"

_EXPECTED_RECEIPT_COLUMNS = (
    ("id", "uuid", "uuid", None, "NO", None),
    ("key_hmac", "character varying", "varchar", 64, "NO", None),
    ("hmac_key_id", "character varying", "varchar", 64, "NO", None),
    ("receipt_id", "character varying", "varchar", 43, "NO", None),
    ("audience", "character varying", "varchar", 16, "NO", None),
    ("actor_id", "uuid", "uuid", None, "NO", None),
    ("workspace_id", "uuid", "uuid", None, "YES", None),
    ("scope_hmac", "character varying", "varchar", 64, "NO", None),
    ("payload_hmac", "character varying", "varchar", 64, "NO", None),
    ("state", "character varying", "varchar", 24, "NO", None),
    ("created_at", "timestamp with time zone", "timestamptz", None, "NO", None),
    ("updated_at", "timestamp with time zone", "timestamptz", None, "NO", None),
    ("expires_at", "timestamp with time zone", "timestamptz", None, "YES", None),
    ("reconciled_at", "timestamp with time zone", "timestamptz", None, "YES", None),
    ("reconciled_by_admin_id", "uuid", "uuid", None, "YES", None),
    ("reconciliation_reason", "character varying", "varchar", 48, "YES", None),
    ("reconciliation_reference", "character varying", "varchar", 64, "YES", None),
)

# PostgreSQL 17 canonical definitions are intentionally exact. A retained
# table is security state, not an arbitrary compatible-looking extension:
# missing or additional constraints must stop re-upgrade before grant DDL.
_EXPECTED_RECEIPT_CONSTRAINTS = {
    "ck_remnawave_connection_drop_receipt_audience": (
        "CHECK (audience::text = ANY (ARRAY['admin'::character varying, "
        "'partner'::character varying, 'customer'::character varying]::text[]))"
    ),
    "ck_remnawave_connection_drop_receipt_digest_lengths": (
        "CHECK (char_length(key_hmac::text) = 64 AND char_length(hmac_key_id::text) = 64 "
        "AND char_length(scope_hmac::text) = 64 AND char_length(payload_hmac::text) = 64 "
        "AND char_length(receipt_id::text) = 43)"
    ),
    "ck_remnawave_connection_drop_receipt_lifecycle": (
        "CHECK (state::text = 'outcome_unknown'::text AND expires_at IS NULL "
        "AND reconciled_at IS NULL AND reconciled_by_admin_id IS NULL "
        "AND reconciliation_reason IS NULL AND reconciliation_reference IS NULL OR "
        "(state::text = ANY (ARRAY['accepted'::character varying, "
        "'rejected'::character varying]::text[])) AND expires_at IS NOT NULL AND "
        "(reconciled_at IS NULL AND reconciled_by_admin_id IS NULL "
        "AND reconciliation_reason IS NULL AND reconciliation_reference IS NULL OR "
        "reconciled_at IS NOT NULL AND reconciled_by_admin_id IS NOT NULL "
        "AND reconciliation_reason IS NOT NULL AND reconciliation_reference IS NOT NULL "
        "AND updated_at = reconciled_at AND expires_at > reconciled_at))"
    ),
    "ck_remnawave_connection_drop_receipt_reconciliation_reason": (
        "CHECK (reconciliation_reason IS NULL OR state::text = 'accepted'::text AND "
        "(reconciliation_reason::text = ANY (ARRAY['provider_confirmed_applied'::character varying, "
        "'postcondition_confirmed_applied'::character varying]::text[])) OR "
        "state::text = 'rejected'::text AND (reconciliation_reason::text = ANY "
        "(ARRAY['provider_confirmed_not_applied'::character varying, "
        "'postcondition_confirmed_not_applied'::character varying]::text[])))"
    ),
    "ck_remnawave_connection_drop_receipt_state": (
        "CHECK (state::text = ANY (ARRAY['outcome_unknown'::character varying, "
        "'accepted'::character varying, 'rejected'::character varying]::text[]))"
    ),
    "ck_remnawave_connection_drop_receipt_workspace_scope": (
        "CHECK (audience::text = 'partner'::text AND workspace_id IS NOT NULL OR "
        "(audience::text = ANY (ARRAY['admin'::character varying, "
        "'customer'::character varying]::text[])) AND workspace_id IS NULL)"
    ),
    "remnawave_connection_drop_receipts_pkey": "PRIMARY KEY (id)",
    "remnawave_connection_drop_receipts_reconciled_by_admin_id_fkey": (
        "FOREIGN KEY (reconciled_by_admin_id) REFERENCES admin_users(id) ON DELETE RESTRICT"
    ),
    "remnawave_connection_drop_receipts_workspace_id_fkey": (
        "FOREIGN KEY (workspace_id) REFERENCES partner_accounts(id) ON DELETE RESTRICT"
    ),
    "uq_remnawave_connection_drop_receipt_key_hmac": "UNIQUE (key_hmac)",
    "uq_remnawave_connection_drop_receipt_public_id": "UNIQUE (receipt_id)",
}

_EXPECTED_RECEIPT_INDEXES = {
    "ix_remnawave_connection_drop_receipts_actor_id": (
        "CREATE INDEX ix_remnawave_connection_drop_receipts_actor_id ON "
        "public.remnawave_connection_drop_receipts USING btree (actor_id)"
    ),
    "ix_remnawave_connection_drop_receipts_audience": (
        "CREATE INDEX ix_remnawave_connection_drop_receipts_audience ON "
        "public.remnawave_connection_drop_receipts USING btree (audience)"
    ),
    "ix_remnawave_connection_drop_receipts_expires_at": (
        "CREATE INDEX ix_remnawave_connection_drop_receipts_expires_at ON "
        "public.remnawave_connection_drop_receipts USING btree (expires_at)"
    ),
    "ix_remnawave_connection_drop_receipts_key_lifecycle": (
        "CREATE INDEX ix_remnawave_connection_drop_receipts_key_lifecycle ON "
        "public.remnawave_connection_drop_receipts USING btree (hmac_key_id, state, expires_at)"
    ),
    "ix_remnawave_connection_drop_receipts_pending_actor": (
        "CREATE INDEX ix_remnawave_connection_drop_receipts_pending_actor ON "
        "public.remnawave_connection_drop_receipts USING btree (audience, actor_id) "
        "WHERE ((state)::text = 'outcome_unknown'::text)"
    ),
    "ix_remnawave_connection_drop_receipts_state": (
        "CREATE INDEX ix_remnawave_connection_drop_receipts_state ON "
        "public.remnawave_connection_drop_receipts USING btree (state)"
    ),
    "ix_remnawave_connection_drop_receipts_unresolved_public_id": (
        "CREATE INDEX ix_remnawave_connection_drop_receipts_unresolved_public_id ON "
        "public.remnawave_connection_drop_receipts USING btree (receipt_id) "
        "WHERE ((state)::text = 'outcome_unknown'::text)"
    ),
    "ix_remnawave_connection_drop_receipts_workspace_id": (
        "CREATE INDEX ix_remnawave_connection_drop_receipts_workspace_id ON "
        "public.remnawave_connection_drop_receipts USING btree (workspace_id)"
    ),
    "remnawave_connection_drop_receipts_pkey": (
        "CREATE UNIQUE INDEX remnawave_connection_drop_receipts_pkey ON "
        "public.remnawave_connection_drop_receipts USING btree (id)"
    ),
    "uq_remnawave_connection_drop_receipt_key_hmac": (
        "CREATE UNIQUE INDEX uq_remnawave_connection_drop_receipt_key_hmac ON "
        "public.remnawave_connection_drop_receipts USING btree (key_hmac)"
    ),
    "uq_remnawave_connection_drop_receipt_public_id": (
        "CREATE UNIQUE INDEX uq_remnawave_connection_drop_receipt_public_id ON "
        "public.remnawave_connection_drop_receipts USING btree (receipt_id)"
    ),
}


def _receipt_table_exists(bind: Any) -> bool:
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Connection drop receipt migration requires PostgreSQL")
    return bool(sa.inspect(bind).has_table(_RECEIPT_TABLE, schema="public"))


def _validate_retained_receipt_table(bind: Any) -> None:
    columns = tuple(
        bind.execute(
            sa.text(
                "SELECT column_name, data_type, udt_name, character_maximum_length, "
                "is_nullable, column_default FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :table_name "
                "ORDER BY ordinal_position"
            ),
            {"table_name": _RECEIPT_TABLE},
        )
        .tuples()
        .all()
    )
    constraints = dict(
        bind.execute(
            sa.text(
                "SELECT conname, pg_get_constraintdef(oid, true) FROM pg_constraint "
                "WHERE conrelid = to_regclass('public.' || :table_name) ORDER BY conname"
            ),
            {"table_name": _RECEIPT_TABLE},
        )
        .tuples()
        .all()
    )
    indexes = dict(
        bind.execute(
            sa.text(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE schemaname = 'public' AND tablename = :table_name ORDER BY indexname"
            ),
            {"table_name": _RECEIPT_TABLE},
        )
        .tuples()
        .all()
    )
    mismatches: list[str] = []
    if columns != _EXPECTED_RECEIPT_COLUMNS:
        mismatches.append("columns")
    if constraints != _EXPECTED_RECEIPT_CONSTRAINTS:
        mismatches.append("constraints")
    if indexes != _EXPECTED_RECEIPT_INDEXES:
        mismatches.append("indexes")
    if mismatches:
        raise RuntimeError(
            "Retained Remnawave connection-drop receipt table has an incompatible exact schema: "
            + ", ".join(mismatches)
        )


def _create_receipt_table() -> None:
    op.create_table(
        _RECEIPT_TABLE,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key_hmac", sa.String(length=64), nullable=False),
        sa.Column("hmac_key_id", sa.String(length=64), nullable=False),
        sa.Column("receipt_id", sa.String(length=43), nullable=False),
        sa.Column("audience", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=True),
        sa.Column("scope_hmac", sa.String(length=64), nullable=False),
        sa.Column("payload_hmac", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconciled_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("reconciliation_reason", sa.String(length=48), nullable=True),
        sa.Column("reconciliation_reference", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "audience IN ('admin', 'partner', 'customer')",
            name="ck_remnawave_connection_drop_receipt_audience",
        ),
        sa.CheckConstraint(
            "state IN ('outcome_unknown', 'accepted', 'rejected')",
            name="ck_remnawave_connection_drop_receipt_state",
        ),
        sa.CheckConstraint(
            "(state = 'outcome_unknown' AND expires_at IS NULL "
            "AND reconciled_at IS NULL AND reconciled_by_admin_id IS NULL "
            "AND reconciliation_reason IS NULL AND reconciliation_reference IS NULL) OR "
            "(state IN ('accepted', 'rejected') AND expires_at IS NOT NULL AND ("
            "(reconciled_at IS NULL AND reconciled_by_admin_id IS NULL "
            "AND reconciliation_reason IS NULL AND reconciliation_reference IS NULL) OR "
            "(reconciled_at IS NOT NULL AND reconciled_by_admin_id IS NOT NULL "
            "AND reconciliation_reason IS NOT NULL AND reconciliation_reference IS NOT NULL "
            "AND updated_at = reconciled_at AND expires_at > reconciled_at)))",
            name="ck_remnawave_connection_drop_receipt_lifecycle",
        ),
        sa.CheckConstraint(
            "reconciliation_reason IS NULL OR "
            "(state = 'accepted' AND reconciliation_reason IN "
            "('provider_confirmed_applied', 'postcondition_confirmed_applied')) OR "
            "(state = 'rejected' AND reconciliation_reason IN "
            "('provider_confirmed_not_applied', 'postcondition_confirmed_not_applied'))",
            name="ck_remnawave_connection_drop_receipt_reconciliation_reason",
        ),
        sa.CheckConstraint(
            "(audience = 'partner' AND workspace_id IS NOT NULL) OR "
            "(audience IN ('admin', 'customer') AND workspace_id IS NULL)",
            name="ck_remnawave_connection_drop_receipt_workspace_scope",
        ),
        sa.CheckConstraint(
            "char_length(key_hmac) = 64 AND char_length(hmac_key_id) = 64 "
            "AND char_length(scope_hmac) = 64 AND char_length(payload_hmac) = 64 "
            "AND char_length(receipt_id) = 43",
            name="ck_remnawave_connection_drop_receipt_digest_lengths",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["partner_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reconciled_by_admin_id"], ["admin_users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hmac", name="uq_remnawave_connection_drop_receipt_key_hmac"),
        sa.UniqueConstraint("receipt_id", name="uq_remnawave_connection_drop_receipt_public_id"),
    )
    for column in ("audience", "actor_id", "workspace_id", "state", "expires_at"):
        op.create_index(f"ix_remnawave_connection_drop_receipts_{column}", _RECEIPT_TABLE, [column])
    op.create_index(
        "ix_remnawave_connection_drop_receipts_pending_actor",
        _RECEIPT_TABLE,
        ["audience", "actor_id"],
        postgresql_where=sa.text("state = 'outcome_unknown'"),
    )
    op.create_index(
        "ix_remnawave_connection_drop_receipts_key_lifecycle",
        _RECEIPT_TABLE,
        ["hmac_key_id", "state", "expires_at"],
    )
    op.create_index(
        "ix_remnawave_connection_drop_receipts_unresolved_public_id",
        _RECEIPT_TABLE,
        ["receipt_id"],
        postgresql_where=sa.text("state = 'outcome_unknown'"),
    )


def upgrade() -> None:
    bind = op.get_bind()
    retained_receipt_table = _receipt_table_exists(bind)
    if retained_receipt_table:
        _validate_retained_receipt_table(bind)

    duplicate = bind.execute(
        sa.text(
            "SELECT resource_type, resource_uuid "
            "FROM partner_remnawave_resource_grants "
            "WHERE revoked_at IS NULL AND resource_type IN ('node', 'service_identity') "
            "GROUP BY resource_type, resource_uuid "
            "HAVING count(DISTINCT workspace_id) > 1 "
            "LIMIT 1"
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Conflicting active partner Remnawave node/service-identity grants must be revoked before upgrade"
        )

    op.drop_constraint(
        "ck_partner_remnawave_resource_type",
        "partner_remnawave_resource_grants",
        type_="check",
    )
    op.create_check_constraint(
        "ck_partner_remnawave_resource_type",
        "partner_remnawave_resource_grants",
        f"resource_type IN ({_NEW_RESOURCE_TYPES})",
    )
    op.create_index(
        "uq_partner_remnawave_exclusive_active_resource",
        "partner_remnawave_resource_grants",
        ["resource_type", "resource_uuid"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL AND resource_type IN ('node', 'service_identity')"),
    )

    if not retained_receipt_table:
        _create_receipt_table()


def downgrade() -> None:
    bind = op.get_bind()
    service_identity_grant = bind.execute(
        sa.text("SELECT 1 FROM partner_remnawave_resource_grants WHERE resource_type = 'service_identity' LIMIT 1")
    ).first()
    if service_identity_grant is not None:
        raise RuntimeError("Remove service_identity grants before downgrading to the prior resource-type contract")

    # Expand-only safety boundary: outcome_unknown tombstones and active
    # terminal replay receipts survive code rollback. Deeper rollback must use
    # the pre-upgrade database restore documented in the release runbook.
    op.drop_index(
        "uq_partner_remnawave_exclusive_active_resource",
        table_name="partner_remnawave_resource_grants",
    )
    op.drop_constraint(
        "ck_partner_remnawave_resource_type",
        "partner_remnawave_resource_grants",
        type_="check",
    )
    op.create_check_constraint(
        "ck_partner_remnawave_resource_type",
        "partner_remnawave_resource_grants",
        f"resource_type IN ({_OLD_RESOURCE_TYPES})",
    )
