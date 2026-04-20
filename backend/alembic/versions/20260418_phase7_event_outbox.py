"""Phase 7 reliable event outbox foundation."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260418_phase7_event_outbox"
down_revision = "20260418_phase5_device_credentials_and_delivery_channels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_key", sa.String(length=160), nullable=False),
        sa.Column("event_name", sa.String(length=120), nullable=False),
        sa.Column("event_family", sa.String(length=40), nullable=False),
        sa.Column("aggregate_type", sa.String(length=60), nullable=False),
        sa.Column("aggregate_id", sa.String(length=160), nullable=False),
        sa.Column("partition_key", sa.String(length=160), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("event_status", sa.String(length=30), nullable=False, server_default="pending_publication"),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.Column("actor_context", sa.JSON(), nullable=False),
        sa.Column("source_context", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key"),
    )
    op.create_index("ix_outbox_events_event_key", "outbox_events", ["event_key"], unique=True)
    op.create_index("ix_outbox_events_event_name", "outbox_events", ["event_name"])
    op.create_index("ix_outbox_events_event_family", "outbox_events", ["event_family"])
    op.create_index("ix_outbox_events_aggregate_type", "outbox_events", ["aggregate_type"])
    op.create_index("ix_outbox_events_aggregate_id", "outbox_events", ["aggregate_id"])
    op.create_index("ix_outbox_events_partition_key", "outbox_events", ["partition_key"])
    op.create_index("ix_outbox_events_event_status", "outbox_events", ["event_status"])

    op.create_table(
        "outbox_publications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("outbox_event_id", sa.Uuid(), nullable=False),
        sa.Column("consumer_key", sa.String(length=80), nullable=False),
        sa.Column("publication_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease_owner", sa.String(length=120), nullable=True),
        sa.Column("leased_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("publication_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["outbox_event_id"], ["outbox_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("outbox_event_id", "consumer_key", name="uq_outbox_publications_event_consumer"),
    )
    op.create_index("ix_outbox_publications_outbox_event_id", "outbox_publications", ["outbox_event_id"])
    op.create_index("ix_outbox_publications_consumer_key", "outbox_publications", ["consumer_key"])
    op.create_index("ix_outbox_publications_publication_status", "outbox_publications", ["publication_status"])
    op.create_index("ix_outbox_publications_lease_owner", "outbox_publications", ["lease_owner"])
    op.create_index("ix_outbox_publications_leased_until", "outbox_publications", ["leased_until"])


def downgrade() -> None:
    op.drop_index("ix_outbox_publications_leased_until", table_name="outbox_publications")
    op.drop_index("ix_outbox_publications_lease_owner", table_name="outbox_publications")
    op.drop_index("ix_outbox_publications_publication_status", table_name="outbox_publications")
    op.drop_index("ix_outbox_publications_consumer_key", table_name="outbox_publications")
    op.drop_index("ix_outbox_publications_outbox_event_id", table_name="outbox_publications")
    op.drop_table("outbox_publications")

    op.drop_index("ix_outbox_events_event_status", table_name="outbox_events")
    op.drop_index("ix_outbox_events_partition_key", table_name="outbox_events")
    op.drop_index("ix_outbox_events_aggregate_id", table_name="outbox_events")
    op.drop_index("ix_outbox_events_aggregate_type", table_name="outbox_events")
    op.drop_index("ix_outbox_events_event_family", table_name="outbox_events")
    op.drop_index("ix_outbox_events_event_name", table_name="outbox_events")
    op.drop_index("ix_outbox_events_event_key", table_name="outbox_events")
    op.drop_table("outbox_events")
