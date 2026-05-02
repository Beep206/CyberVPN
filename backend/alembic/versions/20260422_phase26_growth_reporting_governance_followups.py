"""phase26_growth_reporting_governance_followups

Revision ID: 20260422_phase26_growth_reporting_governance_followups
Revises: 20260422_phase22_growth_reporting_governance
Create Date: 2026-04-22 23:59:30.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260422_phase26_growth_reporting_governance_followups"
down_revision = "20260422_phase22_growth_reporting_governance"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("growth_reporting_subscriptions"):
        return

    column_names = _column_names("growth_reporting_subscriptions")
    if "governance_followup_status" not in column_names:
        op.add_column(
            "growth_reporting_subscriptions",
            sa.Column("governance_followup_status", sa.String(length=20), nullable=False, server_default="none"),
        )
    if "governance_followup_reason_code" not in column_names:
        op.add_column(
            "growth_reporting_subscriptions",
            sa.Column("governance_followup_reason_code", sa.String(length=80), nullable=True),
        )
    if "governance_followup_opened_at" not in column_names:
        op.add_column(
            "growth_reporting_subscriptions",
            sa.Column("governance_followup_opened_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "governance_followup_due_at" not in column_names:
        op.add_column(
            "growth_reporting_subscriptions",
            sa.Column("governance_followup_due_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "governance_followup_last_notified_at" not in column_names:
        op.add_column(
            "growth_reporting_subscriptions",
            sa.Column("governance_followup_last_notified_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "governance_followup_resolved_at" not in column_names:
        op.add_column(
            "growth_reporting_subscriptions",
            sa.Column("governance_followup_resolved_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "governance_followup_resolution_code" not in column_names:
        op.add_column(
            "growth_reporting_subscriptions",
            sa.Column("governance_followup_resolution_code", sa.String(length=120), nullable=True),
        )

    index_names = {index["name"] for index in inspector.get_indexes("growth_reporting_subscriptions")}
    if "ix_growth_reporting_subscriptions_governance_followup_status" not in index_names:
        op.create_index(
            "ix_growth_reporting_subscriptions_governance_followup_status",
            "growth_reporting_subscriptions",
            ["governance_followup_status"],
        )
    if "ix_growth_reporting_subscriptions_governance_followup_reason_code" not in index_names:
        op.create_index(
            "ix_growth_reporting_subscriptions_governance_followup_reason_code",
            "growth_reporting_subscriptions",
            ["governance_followup_reason_code"],
        )
    if "ix_growth_reporting_subscriptions_governance_followup_due_at" not in index_names:
        op.create_index(
            "ix_growth_reporting_subscriptions_governance_followup_due_at",
            "growth_reporting_subscriptions",
            ["governance_followup_due_at"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("growth_reporting_subscriptions"):
        return

    index_names = {index["name"] for index in inspector.get_indexes("growth_reporting_subscriptions")}
    for index_name in (
        "ix_growth_reporting_subscriptions_governance_followup_due_at",
        "ix_growth_reporting_subscriptions_governance_followup_reason_code",
        "ix_growth_reporting_subscriptions_governance_followup_status",
    ):
        if index_name in index_names:
            op.drop_index(index_name, table_name="growth_reporting_subscriptions")

    for column_name in (
        "governance_followup_resolution_code",
        "governance_followup_resolved_at",
        "governance_followup_last_notified_at",
        "governance_followup_due_at",
        "governance_followup_opened_at",
        "governance_followup_reason_code",
        "governance_followup_status",
    ):
        if column_name in _column_names("growth_reporting_subscriptions"):
            op.drop_column("growth_reporting_subscriptions", column_name)
