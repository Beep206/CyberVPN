"""Enforce active commercial-owner effective ranges.

Revision ID: 20260622_partner_owner_ranges
Revises: 20260621_partner_slug_required
Create Date: 2026-06-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260622_partner_owner_ranges"
down_revision: str | Sequence[str] | None = "20260621_partner_slug_required"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GLOBAL_CONSTRAINT = "uq_customer_commercial_bindings_active_owner_global_scope"
STOREFRONT_CONSTRAINT = "uq_customer_commercial_bindings_active_owner_storefront_scope"
LEGACY_GLOBAL_INDEX = "uq_customer_commercial_bindings_active_global_scope"
LEGACY_STOREFRONT_INDEX = "uq_customer_commercial_bindings_active_storefront_scope"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    _assert_no_overlapping_active_owner_ranges(bind)
    op.execute(sa.text(f"DROP INDEX IF EXISTS {LEGACY_STOREFRONT_INDEX}"))
    op.execute(sa.text(f"DROP INDEX IF EXISTS {LEGACY_GLOBAL_INDEX}"))
    op.drop_index(GLOBAL_CONSTRAINT, table_name="customer_commercial_bindings")
    op.drop_index(STOREFRONT_CONSTRAINT, table_name="customer_commercial_bindings")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        sa.text(
            f"""
            ALTER TABLE customer_commercial_bindings
            ADD CONSTRAINT {GLOBAL_CONSTRAINT}
            EXCLUDE USING gist (
                user_id WITH =,
                auth_realm_id WITH =,
                tstzrange(effective_from, COALESCE(effective_to, 'infinity'::timestamptz), '[)') WITH &&
            )
            WHERE (
                binding_status = 'active'
                AND storefront_id IS NULL
                AND owner_type <> 'none'
            )
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            ALTER TABLE customer_commercial_bindings
            ADD CONSTRAINT {STOREFRONT_CONSTRAINT}
            EXCLUDE USING gist (
                user_id WITH =,
                auth_realm_id WITH =,
                storefront_id WITH =,
                tstzrange(effective_from, COALESCE(effective_to, 'infinity'::timestamptz), '[)') WITH &&
            )
            WHERE (
                binding_status = 'active'
                AND storefront_id IS NOT NULL
                AND owner_type <> 'none'
            )
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    _assert_no_duplicate_active_owners(bind)
    _assert_no_duplicate_legacy_active_binding_types(bind)
    op.execute(sa.text(f"ALTER TABLE customer_commercial_bindings DROP CONSTRAINT IF EXISTS {STOREFRONT_CONSTRAINT}"))
    op.execute(sa.text(f"ALTER TABLE customer_commercial_bindings DROP CONSTRAINT IF EXISTS {GLOBAL_CONSTRAINT}"))
    op.create_index(
        GLOBAL_CONSTRAINT,
        "customer_commercial_bindings",
        ["user_id", "auth_realm_id"],
        unique=True,
        postgresql_where=sa.text("binding_status = 'active' AND storefront_id IS NULL AND owner_type <> 'none'"),
    )
    op.create_index(
        STOREFRONT_CONSTRAINT,
        "customer_commercial_bindings",
        ["user_id", "auth_realm_id", "storefront_id"],
        unique=True,
        postgresql_where=sa.text("binding_status = 'active' AND storefront_id IS NOT NULL AND owner_type <> 'none'"),
    )
    op.execute(
        sa.text(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {LEGACY_GLOBAL_INDEX}
            ON customer_commercial_bindings (user_id, binding_type)
            WHERE binding_status = 'active' AND storefront_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {LEGACY_STOREFRONT_INDEX}
            ON customer_commercial_bindings (user_id, binding_type, storefront_id)
            WHERE binding_status = 'active' AND storefront_id IS NOT NULL
            """
        )
    )


def _assert_no_overlapping_active_owner_ranges(bind: sa.Connection) -> None:
    overlap = bind.execute(
        sa.text(
            """
            SELECT current_owner.user_id, current_owner.auth_realm_id, current_owner.storefront_id
            FROM customer_commercial_bindings AS current_owner
            JOIN customer_commercial_bindings AS other_owner
              ON current_owner.id < other_owner.id
             AND current_owner.user_id = other_owner.user_id
             AND current_owner.auth_realm_id = other_owner.auth_realm_id
             AND current_owner.storefront_id IS NOT DISTINCT FROM other_owner.storefront_id
             AND tstzrange(
                   current_owner.effective_from,
                   COALESCE(current_owner.effective_to, 'infinity'::timestamptz),
                   '[)'
                 ) && tstzrange(
                   other_owner.effective_from,
                   COALESCE(other_owner.effective_to, 'infinity'::timestamptz),
                   '[)'
                 )
            WHERE current_owner.binding_status = 'active'
              AND other_owner.binding_status = 'active'
              AND current_owner.owner_type <> 'none'
              AND other_owner.owner_type <> 'none'
            LIMIT 1
            """
        )
    ).first()
    if overlap is not None:
        raise RuntimeError(
            "Cannot add active owner effective-range constraints while overlapping active owners exist. "
            "Normalize effective_from/effective_to or supersede stale rows before migration."
        )


def _assert_no_duplicate_active_owners(bind: sa.Connection) -> None:
    duplicates = bind.execute(
        sa.text(
            """
            SELECT user_id, auth_realm_id, storefront_id, COUNT(*) AS active_count
            FROM customer_commercial_bindings
            WHERE binding_status = 'active'
              AND owner_type <> 'none'
            GROUP BY user_id, auth_realm_id, storefront_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicates is not None:
        raise RuntimeError(
            "Cannot downgrade active owner effective-range constraints while multiple active owners exist in a scope. "
            "Supersede scheduled/current rows before downgrading."
        )


def _assert_no_duplicate_legacy_active_binding_types(bind: sa.Connection) -> None:
    duplicates = bind.execute(
        sa.text(
            """
            SELECT user_id, storefront_id, binding_type, COUNT(*) AS active_count
            FROM customer_commercial_bindings
            WHERE binding_status = 'active'
            GROUP BY user_id, storefront_id, binding_type
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicates is not None:
        raise RuntimeError(
            "Cannot downgrade active owner effective-range constraints while multiple active bindings of the same "
            "type exist in a legacy scope. Supersede cross-realm or scheduled rows before downgrading."
        )
