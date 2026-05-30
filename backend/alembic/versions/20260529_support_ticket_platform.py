"""Support ticket platform tables.

Revision ID: 20260529_support_tickets
Revises: 20260527_msub08_service_identity
Create Date: 2026-05-29
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260529_support_tickets"
down_revision = "20260527_msub08_service_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=40), nullable=False),
        sa.Column("owner_type", sa.String(length=20), nullable=False),
        sa.Column("customer_account_id", sa.Uuid(), nullable=True),
        sa.Column("partner_workspace_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_actor_type", sa.String(length=20), nullable=False),
        sa.Column("created_by_actor_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("subject", sa.String(length=120), nullable=False),
        sa.Column("last_message_preview", sa.String(length=180), nullable=False),
        sa.Column("assigned_admin_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_customer_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_support_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assigned_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_account_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_workspace_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_support_tickets_public_id"),
    )
    op.create_index("ix_support_tickets_public_id", "support_tickets", ["public_id"])
    op.create_index("ix_support_tickets_owner_type", "support_tickets", ["owner_type"])
    op.create_index("ix_support_tickets_customer_account_id", "support_tickets", ["customer_account_id"])
    op.create_index("ix_support_tickets_partner_workspace_id", "support_tickets", ["partner_workspace_id"])
    op.create_index("ix_support_tickets_assigned_admin_id", "support_tickets", ["assigned_admin_id"])
    op.create_index("ix_support_tickets_source", "support_tickets", ["source"])
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])
    op.create_index("ix_support_tickets_category", "support_tickets", ["category"])
    op.create_index("ix_support_tickets_priority", "support_tickets", ["priority"])
    op.create_index(
        "ix_support_tickets_customer_status_updated",
        "support_tickets",
        ["customer_account_id", "status", "updated_at"],
    )
    op.create_index(
        "ix_support_tickets_partner_status_updated",
        "support_tickets",
        ["partner_workspace_id", "status", "updated_at"],
    )
    op.create_index(
        "ix_support_tickets_admin_filters",
        "support_tickets",
        ["status", "priority", "category", "updated_at"],
    )

    op.create_table(
        "support_ticket_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("author_type", sa.String(length=20), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_ticket_messages_ticket_id", "support_ticket_messages", ["ticket_id"])
    op.create_index("ix_support_ticket_messages_visibility", "support_ticket_messages", ["visibility"])
    op.create_index(
        "ix_support_ticket_messages_ticket_created",
        "support_ticket_messages",
        ["ticket_id", "created_at"],
    )

    op.create_table(
        "support_ticket_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("from_value", sa.String(length=120), nullable=True),
        sa.Column("to_value", sa.String(length=120), nullable=True),
        sa.Column("audit_summary", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_ticket_events_ticket_id", "support_ticket_events", ["ticket_id"])
    op.create_index("ix_support_ticket_events_event_type", "support_ticket_events", ["event_type"])
    op.create_index(
        "ix_support_ticket_events_ticket_created",
        "support_ticket_events",
        ["ticket_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_support_ticket_events_ticket_created", table_name="support_ticket_events")
    op.drop_index("ix_support_ticket_events_event_type", table_name="support_ticket_events")
    op.drop_index("ix_support_ticket_events_ticket_id", table_name="support_ticket_events")
    op.drop_table("support_ticket_events")

    op.drop_index("ix_support_ticket_messages_ticket_created", table_name="support_ticket_messages")
    op.drop_index("ix_support_ticket_messages_visibility", table_name="support_ticket_messages")
    op.drop_index("ix_support_ticket_messages_ticket_id", table_name="support_ticket_messages")
    op.drop_table("support_ticket_messages")

    op.drop_index("ix_support_tickets_admin_filters", table_name="support_tickets")
    op.drop_index("ix_support_tickets_partner_status_updated", table_name="support_tickets")
    op.drop_index("ix_support_tickets_customer_status_updated", table_name="support_tickets")
    op.drop_index("ix_support_tickets_priority", table_name="support_tickets")
    op.drop_index("ix_support_tickets_category", table_name="support_tickets")
    op.drop_index("ix_support_tickets_status", table_name="support_tickets")
    op.drop_index("ix_support_tickets_source", table_name="support_tickets")
    op.drop_index("ix_support_tickets_assigned_admin_id", table_name="support_tickets")
    op.drop_index("ix_support_tickets_partner_workspace_id", table_name="support_tickets")
    op.drop_index("ix_support_tickets_customer_account_id", table_name="support_tickets")
    op.drop_index("ix_support_tickets_owner_type", table_name="support_tickets")
    op.drop_index("ix_support_tickets_public_id", table_name="support_tickets")
    op.drop_table("support_tickets")
