"""Partner attribution capture idempotency and invariant hardening.

Revision ID: 20260621_partner_attr_hardening
Revises: 20260620_partner_attr_remaining
Create Date: 2026-06-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260621_partner_attr_hardening"
down_revision: str | Sequence[str] | None = "20260620_partner_attr_remaining"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column(
        "partner_attribution_sessions",
        sa.Column("capture_idempotency_key_hash", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "partner_attribution_sessions",
        sa.Column("consumed_transfer_token_hash", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_partner_attr_sessions_capture_idempotency_key_hash",
        "partner_attribution_sessions",
        ["capture_idempotency_key_hash"],
        unique=True,
    )
    op.create_index(
        "ix_partner_attr_sessions_consumed_transfer_token_hash",
        "partner_attribution_sessions",
        ["consumed_transfer_token_hash"],
        unique=True,
    )

    if bind.dialect.name != "postgresql":
        return

    _assert_no_duplicate_active_owners(bind)
    _assert_no_duplicate_touchpoint_idempotency(bind)

    op.create_index(
        "uq_attribution_touchpoints_realm_idempotency_key",
        "attribution_touchpoints",
        ["auth_realm_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.create_index(
        "uq_attribution_touchpoints_realm_source_event_id",
        "attribution_touchpoints",
        ["auth_realm_id", "source_event_id"],
        unique=True,
        postgresql_where=sa.text("source_event_id IS NOT NULL"),
    )
    op.create_index(
        "uq_customer_commercial_bindings_active_owner_global_scope",
        "customer_commercial_bindings",
        ["user_id", "auth_realm_id"],
        unique=True,
        postgresql_where=sa.text("binding_status = 'active' AND storefront_id IS NULL AND owner_type <> 'none'"),
    )
    op.create_index(
        "uq_customer_commercial_bindings_active_owner_storefront_scope",
        "customer_commercial_bindings",
        ["user_id", "auth_realm_id", "storefront_id"],
        unique=True,
        postgresql_where=sa.text("binding_status = 'active' AND storefront_id IS NOT NULL AND owner_type <> 'none'"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index(
            "uq_customer_commercial_bindings_active_owner_storefront_scope",
            table_name="customer_commercial_bindings",
        )
        op.drop_index(
            "uq_customer_commercial_bindings_active_owner_global_scope",
            table_name="customer_commercial_bindings",
        )
        op.drop_index(
            "uq_attribution_touchpoints_realm_source_event_id",
            table_name="attribution_touchpoints",
        )
        op.drop_index(
            "uq_attribution_touchpoints_realm_idempotency_key",
            table_name="attribution_touchpoints",
        )
    op.drop_index(
        "ix_partner_attr_sessions_capture_idempotency_key_hash",
        table_name="partner_attribution_sessions",
    )
    op.drop_index(
        "ix_partner_attr_sessions_consumed_transfer_token_hash",
        table_name="partner_attribution_sessions",
    )
    op.drop_column("partner_attribution_sessions", "consumed_transfer_token_hash")
    op.drop_column("partner_attribution_sessions", "capture_idempotency_key_hash")


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
            "Cannot add active commercial-owner indexes while duplicate active owners exist. "
            "Run the partner-attribution migration preflight and remediate duplicates first."
        )


def _assert_no_duplicate_touchpoint_idempotency(bind: sa.Connection) -> None:
    duplicate_idempotency = bind.execute(
        sa.text(
            """
            SELECT auth_realm_id, idempotency_key, COUNT(*) AS duplicate_count
            FROM attribution_touchpoints
            WHERE idempotency_key IS NOT NULL
            GROUP BY auth_realm_id, idempotency_key
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate_idempotency is not None:
        raise RuntimeError(
            "Cannot add touchpoint idempotency indexes while duplicate idempotency keys exist. "
            "Run the partner-attribution migration preflight and remediate duplicates first."
        )

    duplicate_source = bind.execute(
        sa.text(
            """
            SELECT auth_realm_id, source_event_id, COUNT(*) AS duplicate_count
            FROM attribution_touchpoints
            WHERE source_event_id IS NOT NULL
            GROUP BY auth_realm_id, source_event_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate_source is not None:
        raise RuntimeError(
            "Cannot add touchpoint source-event indexes while duplicate source events exist. "
            "Run the partner-attribution migration preflight and remediate duplicates first."
        )
