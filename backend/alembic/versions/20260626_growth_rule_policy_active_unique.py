"""Enforce one active Growth rule policy per scope.

Revision ID: 20260626_gr_rule_active
Revises: 20260625_pay_attempt_idem
Create Date: 2026-06-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260626_gr_rule_active"
down_revision: str | Sequence[str] | None = "20260625_pay_attempt_idem"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_policy_versions_growth_rule_active_scope"
NULL_SUBJECT_SENTINEL = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    bind = op.get_bind()
    _assert_no_duplicate_active_growth_rule_policies(bind)
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                f"""
                CREATE UNIQUE INDEX {INDEX_NAME}
                ON policy_versions (
                    policy_key,
                    subject_type,
                    COALESCE(subject_id::text, '{NULL_SUBJECT_SENTINEL}')
                )
                WHERE policy_family = 'growth_rules' AND version_status = 'active'
                """
            )
        )
        return

    op.execute(
        sa.text(
            f"""
            CREATE UNIQUE INDEX {INDEX_NAME}
            ON policy_versions (
                policy_key,
                subject_type,
                COALESCE(subject_id, '{NULL_SUBJECT_SENTINEL}')
            )
            WHERE policy_family = 'growth_rules' AND version_status = 'active'
            """
        )
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="policy_versions")


def _assert_no_duplicate_active_growth_rule_policies(bind: sa.Connection) -> None:
    if bind.dialect.name == "postgresql":
        duplicate_query = sa.text(
            """
            SELECT
                policy_key,
                subject_type,
                COALESCE(subject_id::text, :null_subject_sentinel) AS subject_scope,
                COUNT(*) AS duplicate_count
            FROM policy_versions
            WHERE policy_family = 'growth_rules' AND version_status = 'active'
            GROUP BY policy_key, subject_type, COALESCE(subject_id::text, :null_subject_sentinel)
            HAVING COUNT(*) > 1
            """
        )
    else:
        duplicate_query = sa.text(
            """
            SELECT
                policy_key,
                subject_type,
                COALESCE(subject_id, :null_subject_sentinel) AS subject_scope,
                COUNT(*) AS duplicate_count
            FROM policy_versions
            WHERE policy_family = 'growth_rules' AND version_status = 'active'
            GROUP BY policy_key, subject_type, COALESCE(subject_id, :null_subject_sentinel)
            HAVING COUNT(*) > 1
            """
        )
    rows = bind.execute(duplicate_query, {"null_subject_sentinel": NULL_SUBJECT_SENTINEL}).fetchall()
    if rows:
        details = ", ".join(
            f"{row.policy_key}/{row.subject_type}/{row.subject_scope}:{row.duplicate_count}" for row in rows[:10]
        )
        raise RuntimeError(
            f"Cannot add active growth rule policy uniqueness index; duplicate active scopes exist: {details}"
        )
