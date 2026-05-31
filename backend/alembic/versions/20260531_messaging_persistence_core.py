"""Messaging persistence core tables.

Revision ID: 20260531_messaging_core
Revises: 20260531_redact_webhook_logs
Create Date: 2026-05-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260531_messaging_core"
down_revision = "20260531_redact_webhook_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "messaging_conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=40), nullable=False),
        sa.Column("customer_account_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("response_state", sa.String(length=30), nullable=False, server_default="none"),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("subject", sa.String(length=160), nullable=False),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_admin_id", sa.Uuid(), nullable=True),
        sa.Column("related_support_ticket_id", sa.Uuid(), nullable=True),
        sa.Column("last_message_id", sa.Uuid(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status in ('open', 'closed', 'archived', 'locked')",
            name="ck_messaging_conversations_status",
        ),
        sa.CheckConstraint("customer_account_id is not null", name="ck_messaging_conversations_customer_required"),
        sa.ForeignKeyConstraint(["assigned_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_account_id"], ["mobile_users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["related_support_ticket_id"], ["support_tickets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_messaging_conversations_public_id"),
    )
    op.create_index("ix_messaging_conversations_public_id", "messaging_conversations", ["public_id"])
    op.create_index(
        "ix_messaging_conversations_customer_account_id", "messaging_conversations", ["customer_account_id"]
    )
    op.create_index("ix_messaging_conversations_assigned_admin_id", "messaging_conversations", ["assigned_admin_id"])
    op.create_index("ix_messaging_conversations_category", "messaging_conversations", ["category"])
    op.create_index("ix_messaging_conversations_priority", "messaging_conversations", ["priority"])
    op.create_index("ix_messaging_conversations_status", "messaging_conversations", ["status"])
    op.create_index("ix_messaging_conversations_last_message_id", "messaging_conversations", ["last_message_id"])
    op.create_index(
        "ix_messaging_conversations_customer_status_updated",
        "messaging_conversations",
        ["customer_account_id", "status", "updated_at"],
    )
    op.create_index(
        "ix_messaging_conversations_assigned_status_updated",
        "messaging_conversations",
        ["assigned_admin_id", "status", "updated_at"],
    )
    op.create_index(
        "ix_messaging_conversations_status_priority_category_updated",
        "messaging_conversations",
        ["status", "priority", "category", "updated_at"],
    )

    op.create_table(
        "messaging_conversation_participants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("participant_type", sa.String(length=20), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("can_read", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("can_write", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.CheckConstraint(
            "participant_type in ('customer', 'admin', 'team', 'system')",
            name="ck_messaging_participants_type",
        ),
        sa.CheckConstraint(
            "(participant_type in ('customer', 'admin') and participant_id is not null) "
            "or participant_type in ('team', 'system')",
            name="ck_messaging_participants_actor_required",
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["messaging_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_messaging_participants_actor_can_read",
        "messaging_conversation_participants",
        ["participant_type", "participant_id", "can_read"],
    )
    op.create_index(
        "ix_messaging_conversation_participants_conversation_id",
        "messaging_conversation_participants",
        ["conversation_id"],
    )
    op.create_index(
        "ix_messaging_conversation_participants_participant_id",
        "messaging_conversation_participants",
        ["participant_id"],
    )
    op.create_index(
        "ix_messaging_conversation_participants_participant_type",
        "messaging_conversation_participants",
        ["participant_type"],
    )
    op.create_index(
        "uq_messaging_participants_active_role",
        "messaging_conversation_participants",
        ["conversation_id", "participant_type", "participant_id", "role"],
        unique=True,
        postgresql_where=sa.text("left_at IS NULL"),
    )
    op.create_index(
        "uq_messaging_participants_active_customer",
        "messaging_conversation_participants",
        ["conversation_id"],
        unique=True,
        postgresql_where=sa.text("left_at IS NULL AND participant_type = 'customer'"),
    )

    op.create_table(
        "messaging_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=40), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("sender_type", sa.String(length=20), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("body_format", sa.String(length=20), nullable=False, server_default="plain_text"),
        sa.Column("client_message_id", sa.String(length=80), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("reply_to_message_id", sa.Uuid(), nullable=True),
        sa.Column("redacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.CheckConstraint(
            "sender_type in ('customer', 'admin', 'system')",
            name="ck_messaging_messages_sender_type",
        ),
        sa.CheckConstraint(
            "visibility != 'internal' or sender_type in ('admin', 'system')",
            name="ck_messaging_messages_internal_sender",
        ),
        sa.CheckConstraint(
            "sender_type = 'system' or sender_id is not null",
            name="ck_messaging_messages_actor_required",
        ),
        sa.CheckConstraint("body_format = 'plain_text'", name="ck_messaging_messages_plain_text"),
        sa.ForeignKeyConstraint(["conversation_id"], ["messaging_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reply_to_message_id"], ["messaging_messages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_messaging_messages_idempotency_key"),
        sa.UniqueConstraint("public_id", name="uq_messaging_messages_public_id"),
    )
    op.create_foreign_key(
        "fk_messaging_conversations_last_message_id",
        "messaging_conversations",
        "messaging_messages",
        ["last_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_messaging_messages_conversation_id", "messaging_messages", ["conversation_id"])
    op.create_index("ix_messaging_messages_idempotency_key", "messaging_messages", ["idempotency_key"])
    op.create_index("ix_messaging_messages_public_id", "messaging_messages", ["public_id"])
    op.create_index("ix_messaging_messages_sender_id", "messaging_messages", ["sender_id"])
    op.create_index("ix_messaging_messages_sender_type", "messaging_messages", ["sender_type"])
    op.create_index("ix_messaging_messages_visibility", "messaging_messages", ["visibility"])
    op.create_index(
        "ix_messaging_messages_conversation_created", "messaging_messages", ["conversation_id", "created_at"]
    )
    op.create_index(
        "ix_messaging_messages_sender_created", "messaging_messages", ["sender_type", "sender_id", "created_at"]
    )
    op.create_index(
        "uq_messaging_messages_client_message",
        "messaging_messages",
        ["conversation_id", "sender_type", "sender_id", "client_message_id"],
        unique=True,
        postgresql_where=sa.text("client_message_id IS NOT NULL"),
    )

    op.create_table(
        "messaging_message_read_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("participant_type", sa.String(length=20), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("last_read_message_id", sa.Uuid(), nullable=True),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["conversation_id"], ["messaging_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_read_message_id"], ["messaging_messages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id",
            "participant_type",
            "participant_id",
            name="uq_messaging_read_states_conversation_actor",
        ),
    )
    op.create_index(
        "ix_messaging_message_read_states_conversation_id", "messaging_message_read_states", ["conversation_id"]
    )
    op.create_index(
        "ix_messaging_message_read_states_participant_id", "messaging_message_read_states", ["participant_id"]
    )
    op.create_index(
        "ix_messaging_message_read_states_participant_type", "messaging_message_read_states", ["participant_type"]
    )
    op.create_index(
        "ix_messaging_read_states_actor_updated",
        "messaging_message_read_states",
        ["participant_type", "participant_id", "updated_at"],
    )

    op.create_table(
        "broadcast_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("audience_type", sa.String(length=40), nullable=False),
        sa.Column("audience_filter", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("template_key", sa.String(length=120), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("action_url", sa.String(length=500), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["approved_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["admin_users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_broadcast_campaigns_public_id"),
    )
    op.create_index("ix_broadcast_campaigns_public_id", "broadcast_campaigns", ["public_id"])
    op.create_index("ix_broadcast_campaigns_status", "broadcast_campaigns", ["status"])
    op.create_index("ix_broadcast_campaigns_audience_type", "broadcast_campaigns", ["audience_type"])
    op.create_index("ix_broadcast_campaigns_scheduled_at", "broadcast_campaigns", ["scheduled_at"])
    op.create_index("ix_broadcast_campaigns_created_by_admin_id", "broadcast_campaigns", ["created_by_admin_id"])
    op.create_index("ix_broadcast_campaigns_approved_by_admin_id", "broadcast_campaigns", ["approved_by_admin_id"])
    op.create_index("ix_broadcast_campaigns_status_scheduled", "broadcast_campaigns", ["status", "scheduled_at"])
    op.create_index("ix_broadcast_campaigns_audience_status", "broadcast_campaigns", ["audience_type", "status"])

    op.create_table(
        "site_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notification_type", sa.String(length=30), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("action_url", sa.String(length=500), nullable=True),
        sa.Column("aggregate_type", sa.String(length=80), nullable=True),
        sa.Column("aggregate_id", sa.String(length=160), nullable=True),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("broadcast_campaign_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_actor_type", sa.String(length=20), nullable=False),
        sa.Column("created_by_actor_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["broadcast_campaign_id"], ["broadcast_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["messaging_conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["message_id"], ["messaging_messages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_site_notifications_notification_type", "site_notifications", ["notification_type"])
    op.create_index("ix_site_notifications_severity", "site_notifications", ["severity"])
    op.create_index("ix_site_notifications_conversation_id", "site_notifications", ["conversation_id"])
    op.create_index("ix_site_notifications_message_id", "site_notifications", ["message_id"])
    op.create_index("ix_site_notifications_broadcast_campaign_id", "site_notifications", ["broadcast_campaign_id"])
    op.create_index("ix_site_notifications_expires_at", "site_notifications", ["expires_at"])
    op.create_index("ix_site_notifications_aggregate", "site_notifications", ["aggregate_type", "aggregate_id"])
    op.create_index(
        "ix_site_notifications_conversation_created", "site_notifications", ["conversation_id", "created_at"]
    )
    op.create_index(
        "ix_site_notifications_broadcast_created", "site_notifications", ["broadcast_campaign_id", "created_at"]
    )

    op.create_table(
        "site_notification_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_type", sa.String(length=20), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=True),
        sa.Column("delivery_channel", sa.String(length=20), nullable=False, server_default="site"),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["notification_id"], ["site_notifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notification_id",
            "recipient_type",
            "recipient_id",
            "delivery_channel",
            name="uq_site_notification_deliveries_recipient_channel",
        ),
        sa.CheckConstraint("recipient_id is not null", name="ck_site_notification_deliveries_recipient_required"),
    )
    op.create_index(
        "ix_site_notification_deliveries_notification_id", "site_notification_deliveries", ["notification_id"]
    )
    op.create_index("ix_site_notification_deliveries_recipient_id", "site_notification_deliveries", ["recipient_id"])
    op.create_index(
        "ix_site_notification_deliveries_recipient_type", "site_notification_deliveries", ["recipient_type"]
    )
    op.create_index("ix_site_notification_deliveries_status", "site_notification_deliveries", ["status"])
    op.create_index(
        "ix_site_notification_deliveries_recipient_status_created",
        "site_notification_deliveries",
        ["recipient_type", "recipient_id", "status", "created_at"],
    )
    op.create_index(
        "ix_site_notification_deliveries_status_created", "site_notification_deliveries", ["status", "created_at"]
    )

    op.create_table(
        "broadcast_campaign_recipients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_type", sa.String(length=20), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column("site_notification_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("skip_reason", sa.String(length=160), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("materialized_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["campaign_id"], ["broadcast_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_notification_id"], ["site_notifications.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "recipient_type",
            "recipient_id",
            name="uq_broadcast_campaign_recipients_campaign_recipient",
        ),
    )
    op.create_index("ix_broadcast_campaign_recipients_campaign_id", "broadcast_campaign_recipients", ["campaign_id"])
    op.create_index("ix_broadcast_campaign_recipients_recipient_id", "broadcast_campaign_recipients", ["recipient_id"])
    op.create_index(
        "ix_broadcast_campaign_recipients_recipient_type", "broadcast_campaign_recipients", ["recipient_type"]
    )
    op.create_index("ix_broadcast_campaign_recipients_status", "broadcast_campaign_recipients", ["status"])
    op.create_index(
        "ix_broadcast_campaign_recipients_site_notification_id",
        "broadcast_campaign_recipients",
        ["site_notification_id"],
    )
    op.create_index(
        "ix_broadcast_campaign_recipients_campaign_status",
        "broadcast_campaign_recipients",
        ["campaign_id", "status"],
    )
    op.create_index(
        "ix_broadcast_campaign_recipients_recipient_created",
        "broadcast_campaign_recipients",
        ["recipient_type", "recipient_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_broadcast_campaign_recipients_recipient_created", table_name="broadcast_campaign_recipients")
    op.drop_index("ix_broadcast_campaign_recipients_campaign_status", table_name="broadcast_campaign_recipients")
    op.drop_index("ix_broadcast_campaign_recipients_site_notification_id", table_name="broadcast_campaign_recipients")
    op.drop_index("ix_broadcast_campaign_recipients_status", table_name="broadcast_campaign_recipients")
    op.drop_index("ix_broadcast_campaign_recipients_recipient_type", table_name="broadcast_campaign_recipients")
    op.drop_index("ix_broadcast_campaign_recipients_recipient_id", table_name="broadcast_campaign_recipients")
    op.drop_index("ix_broadcast_campaign_recipients_campaign_id", table_name="broadcast_campaign_recipients")
    op.drop_table("broadcast_campaign_recipients")

    op.drop_index("ix_site_notification_deliveries_status_created", table_name="site_notification_deliveries")
    op.drop_index(
        "ix_site_notification_deliveries_recipient_status_created",
        table_name="site_notification_deliveries",
    )
    op.drop_index("ix_site_notification_deliveries_status", table_name="site_notification_deliveries")
    op.drop_index("ix_site_notification_deliveries_recipient_type", table_name="site_notification_deliveries")
    op.drop_index("ix_site_notification_deliveries_recipient_id", table_name="site_notification_deliveries")
    op.drop_index("ix_site_notification_deliveries_notification_id", table_name="site_notification_deliveries")
    op.drop_table("site_notification_deliveries")

    op.drop_index("ix_site_notifications_broadcast_created", table_name="site_notifications")
    op.drop_index("ix_site_notifications_conversation_created", table_name="site_notifications")
    op.drop_index("ix_site_notifications_aggregate", table_name="site_notifications")
    op.drop_index("ix_site_notifications_expires_at", table_name="site_notifications")
    op.drop_index("ix_site_notifications_broadcast_campaign_id", table_name="site_notifications")
    op.drop_index("ix_site_notifications_message_id", table_name="site_notifications")
    op.drop_index("ix_site_notifications_conversation_id", table_name="site_notifications")
    op.drop_index("ix_site_notifications_severity", table_name="site_notifications")
    op.drop_index("ix_site_notifications_notification_type", table_name="site_notifications")
    op.drop_table("site_notifications")

    op.drop_index("ix_broadcast_campaigns_audience_status", table_name="broadcast_campaigns")
    op.drop_index("ix_broadcast_campaigns_status_scheduled", table_name="broadcast_campaigns")
    op.drop_index("ix_broadcast_campaigns_approved_by_admin_id", table_name="broadcast_campaigns")
    op.drop_index("ix_broadcast_campaigns_created_by_admin_id", table_name="broadcast_campaigns")
    op.drop_index("ix_broadcast_campaigns_scheduled_at", table_name="broadcast_campaigns")
    op.drop_index("ix_broadcast_campaigns_audience_type", table_name="broadcast_campaigns")
    op.drop_index("ix_broadcast_campaigns_status", table_name="broadcast_campaigns")
    op.drop_index("ix_broadcast_campaigns_public_id", table_name="broadcast_campaigns")
    op.drop_table("broadcast_campaigns")

    op.drop_index("ix_messaging_read_states_actor_updated", table_name="messaging_message_read_states")
    op.drop_index("ix_messaging_message_read_states_participant_type", table_name="messaging_message_read_states")
    op.drop_index("ix_messaging_message_read_states_participant_id", table_name="messaging_message_read_states")
    op.drop_index("ix_messaging_message_read_states_conversation_id", table_name="messaging_message_read_states")
    op.drop_table("messaging_message_read_states")

    op.drop_index("uq_messaging_messages_client_message", table_name="messaging_messages")
    op.drop_index("ix_messaging_messages_sender_created", table_name="messaging_messages")
    op.drop_index("ix_messaging_messages_conversation_created", table_name="messaging_messages")
    op.drop_index("ix_messaging_messages_visibility", table_name="messaging_messages")
    op.drop_index("ix_messaging_messages_sender_type", table_name="messaging_messages")
    op.drop_index("ix_messaging_messages_sender_id", table_name="messaging_messages")
    op.drop_index("ix_messaging_messages_public_id", table_name="messaging_messages")
    op.drop_index("ix_messaging_messages_idempotency_key", table_name="messaging_messages")
    op.drop_index("ix_messaging_messages_conversation_id", table_name="messaging_messages")
    op.drop_constraint(
        "fk_messaging_conversations_last_message_id",
        "messaging_conversations",
        type_="foreignkey",
    )
    op.drop_table("messaging_messages")

    op.drop_index("uq_messaging_participants_active_customer", table_name="messaging_conversation_participants")
    op.drop_index("uq_messaging_participants_active_role", table_name="messaging_conversation_participants")
    op.drop_index(
        "ix_messaging_conversation_participants_participant_type", table_name="messaging_conversation_participants"
    )
    op.drop_index(
        "ix_messaging_conversation_participants_participant_id", table_name="messaging_conversation_participants"
    )
    op.drop_index(
        "ix_messaging_conversation_participants_conversation_id", table_name="messaging_conversation_participants"
    )
    op.drop_index("ix_messaging_participants_actor_can_read", table_name="messaging_conversation_participants")
    op.drop_table("messaging_conversation_participants")

    op.drop_index("ix_messaging_conversations_status_priority_category_updated", table_name="messaging_conversations")
    op.drop_index("ix_messaging_conversations_assigned_status_updated", table_name="messaging_conversations")
    op.drop_index("ix_messaging_conversations_customer_status_updated", table_name="messaging_conversations")
    op.drop_index("ix_messaging_conversations_last_message_id", table_name="messaging_conversations")
    op.drop_index("ix_messaging_conversations_status", table_name="messaging_conversations")
    op.drop_index("ix_messaging_conversations_priority", table_name="messaging_conversations")
    op.drop_index("ix_messaging_conversations_category", table_name="messaging_conversations")
    op.drop_index("ix_messaging_conversations_assigned_admin_id", table_name="messaging_conversations")
    op.drop_index("ix_messaging_conversations_customer_account_id", table_name="messaging_conversations")
    op.drop_index("ix_messaging_conversations_public_id", table_name="messaging_conversations")
    op.drop_table("messaging_conversations")
