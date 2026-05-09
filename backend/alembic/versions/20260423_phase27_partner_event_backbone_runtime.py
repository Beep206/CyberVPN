"""partner event backbone runtime tables

Revision ID: 20260423_p27_partner_events
Revises: 20260422_p18_partner_bot, 20260422_p26_growth_gov_fups
Create Date: 2026-04-23 12:00:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260423_p27_partner_events"
down_revision: Union[str, Sequence[str], None] = (
    "20260422_p18_partner_bot",
    "20260422_p26_growth_gov_fups",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid_type():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def upgrade() -> None:
    op.create_table(
        "outbox_consumer_receipts",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("consumer_key", sa.String(length=80), nullable=False),
        sa.Column("event_key", sa.String(length=160), nullable=False),
        sa.Column("event_name", sa.String(length=120), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="processed"),
        sa.Column("metadata_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("consumer_key", "event_key", name="uq_outbox_consumer_receipts_consumer_event"),
    )
    op.create_index(
        "ix_outbox_consumer_receipts_consumer_key",
        "outbox_consumer_receipts",
        ["consumer_key"],
        unique=False,
    )
    op.create_index(
        "ix_outbox_consumer_receipts_event_key",
        "outbox_consumer_receipts",
        ["event_key"],
        unique=False,
    )

    op.create_table(
        "partner_workspace_feed_events",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("workspace_id", _uuid_type(), nullable=False),
        sa.Column("event_key", sa.String(length=160), nullable=False),
        sa.Column("event_name", sa.String(length=120), nullable=False),
        sa.Column("event_family", sa.String(length=40), nullable=False),
        sa.Column("aggregate_type", sa.String(length=60), nullable=False),
        sa.Column("aggregate_id", sa.String(length=160), nullable=False),
        sa.Column("consumer_key", sa.String(length=80), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key"),
    )
    op.create_index(
        "ix_partner_workspace_feed_events_workspace_id",
        "partner_workspace_feed_events",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_partner_workspace_feed_events_event_name",
        "partner_workspace_feed_events",
        ["event_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_partner_workspace_feed_events_event_name", table_name="partner_workspace_feed_events")
    op.drop_index("ix_partner_workspace_feed_events_workspace_id", table_name="partner_workspace_feed_events")
    op.drop_table("partner_workspace_feed_events")
    op.drop_index("ix_outbox_consumer_receipts_event_key", table_name="outbox_consumer_receipts")
    op.drop_index("ix_outbox_consumer_receipts_consumer_key", table_name="outbox_consumer_receipts")
    op.drop_table("outbox_consumer_receipts")
