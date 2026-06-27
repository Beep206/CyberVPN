"""Add Growth reversal event ledger.

Revision ID: 20260626_growth_reversals
Revises: 20260626_gr_rule_active
Create Date: 2026-06-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260626_growth_reversals"
down_revision: str | Sequence[str] | None = "20260626_gr_rule_active"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    json_type = _json_type(bind)
    op.create_table(
        "growth_reversal_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("refund_id", sa.Uuid(), nullable=True),
        sa.Column("payment_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("reason_code", sa.String(length=120), nullable=False),
        sa.Column("event_status", sa.String(length=24), nullable=False, server_default="applied"),
        sa.Column("event_payload", json_type, nullable=False, server_default=_json_default(bind, "{}")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "event_type IN ('refund', 'zero_payment_cancellation', 'campaign_revoke')",
            name="ck_growth_reversal_events_event_type",
        ),
        sa.ForeignKeyConstraint(["campaign_id"], ["growth_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["refund_id"], ["refunds.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_growth_reversal_events_idempotency_key"),
    )
    for column_name in (
        "event_type",
        "event_id",
        "order_id",
        "refund_id",
        "payment_id",
        "campaign_id",
        "idempotency_key",
        "created_at",
    ):
        op.create_index(f"ix_growth_reversal_events_{column_name}", "growth_reversal_events", [column_name])


def downgrade() -> None:
    op.drop_table("growth_reversal_events")


def _json_type(bind: sa.Connection) -> sa.types.TypeEngine:
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_default(bind: sa.Connection, value: str) -> sa.TextClause:
    if bind.dialect.name == "postgresql":
        return sa.text(f"'{value}'::jsonb")
    return sa.text(f"'{value}'")
