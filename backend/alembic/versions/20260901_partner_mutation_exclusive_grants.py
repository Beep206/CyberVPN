"""Make mutable partner Remnawave resources exclusive across workspaces.

Revision ID: 20260901_partner_grant_exclusive
Revises: 20260901_stream_group_lag
Create Date: 2026-09-01

Profiles and integrations are global Remnawave objects. Partner writes are
tenant-safe only when an active object grant has exactly one workspace owner.
The preflight is deliberately fail-fast and never rewrites or revokes grants.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260901_partner_grant_exclusive"
down_revision: str | Sequence[str] | None = "20260901_stream_group_lag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX_NAME = "uq_partner_remnawave_exclusive_active_resource"
_TABLE_NAME = "partner_remnawave_resource_grants"
_OLD_PREDICATE = "revoked_at IS NULL AND resource_type IN ('node', 'service_identity')"
_NEW_PREDICATE = "revoked_at IS NULL AND resource_type IN ('node', 'service_identity', 'profile', 'integration')"


def upgrade() -> None:
    duplicate = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT resource_type, resource_uuid "
                "FROM partner_remnawave_resource_grants "
                "WHERE revoked_at IS NULL AND resource_type IN ('profile', 'integration') "
                "GROUP BY resource_type, resource_uuid "
                "HAVING count(DISTINCT workspace_id) > 1 "
                "LIMIT 1"
            )
        )
        .first()
    )
    if duplicate is not None:
        raise RuntimeError(
            "Conflicting active partner Remnawave profile/integration grants must be reconciled before upgrade"
        )

    op.drop_index(_INDEX_NAME, table_name=_TABLE_NAME)
    op.create_index(
        _INDEX_NAME,
        _TABLE_NAME,
        ["resource_type", "resource_uuid"],
        unique=True,
        postgresql_where=sa.text(_NEW_PREDICATE),
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name=_TABLE_NAME)
    op.create_index(
        _INDEX_NAME,
        _TABLE_NAME,
        ["resource_type", "resource_uuid"],
        unique=True,
        postgresql_where=sa.text(_OLD_PREDICATE),
    )
