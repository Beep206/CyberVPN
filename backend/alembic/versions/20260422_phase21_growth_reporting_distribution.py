"""phase21_growth_reporting_distribution

Revision ID: 20260422_p21_growth_distribution
Revises: 20260422_p20_growth_refresh
Create Date: 2026-04-22 23:40:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260422_p21_growth_distribution"
down_revision = "20260422_p20_growth_refresh"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("growth_reporting_subscriptions"):
        op.create_table(
            "growth_reporting_subscriptions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("recipient_email", sa.String(length=320), nullable=False),
            sa.Column("recipient_name", sa.String(length=160), nullable=True),
            sa.Column("audience_key", sa.String(length=32), nullable=False),
            sa.Column("delivery_channel", sa.String(length=20), nullable=False, server_default="email"),
            sa.Column("cadence", sa.String(length=20), nullable=False),
            sa.Column("report_window_days", sa.Integer(), nullable=False, server_default="30"),
            sa.Column("subscription_status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("next_delivery_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_delivery_attempt_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("latest_delivery_status", sa.String(length=20), nullable=True),
            sa.Column("latest_delivery_reason", sa.String(length=120), nullable=True),
            sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
            sa.Column("updated_by_admin_user_id", sa.Uuid(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["updated_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_growth_reporting_subscriptions_recipient_email",
            "growth_reporting_subscriptions",
            ["recipient_email"],
        )
        op.create_index(
            "ix_growth_reporting_subscriptions_audience_key",
            "growth_reporting_subscriptions",
            ["audience_key"],
        )
        op.create_index(
            "ix_growth_reporting_subscriptions_cadence",
            "growth_reporting_subscriptions",
            ["cadence"],
        )
        op.create_index(
            "ix_growth_reporting_subscriptions_subscription_status",
            "growth_reporting_subscriptions",
            ["subscription_status"],
        )
        op.create_index(
            "ix_growth_reporting_subscriptions_next_delivery_at",
            "growth_reporting_subscriptions",
            ["next_delivery_at"],
        )
        op.create_index(
            "ix_growth_reporting_subscriptions_latest_delivery_status",
            "growth_reporting_subscriptions",
            ["latest_delivery_status"],
        )
        op.create_index(
            "ix_growth_reporting_subscriptions_created_by_admin_user_id",
            "growth_reporting_subscriptions",
            ["created_by_admin_user_id"],
        )
        op.create_index(
            "ix_growth_reporting_subscriptions_updated_by_admin_user_id",
            "growth_reporting_subscriptions",
            ["updated_by_admin_user_id"],
        )

    if not inspector.has_table("growth_reporting_deliveries"):
        op.create_table(
            "growth_reporting_deliveries",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("subscription_id", sa.Uuid(), nullable=False),
            sa.Column("recipient_email", sa.String(length=320), nullable=False),
            sa.Column("recipient_name", sa.String(length=160), nullable=True),
            sa.Column("audience_key", sa.String(length=32), nullable=False),
            sa.Column("delivery_channel", sa.String(length=20), nullable=False, server_default="email"),
            sa.Column("cadence", sa.String(length=20), nullable=False),
            sa.Column("report_window_days", sa.Integer(), nullable=False),
            sa.Column("delivery_status", sa.String(length=20), nullable=False),
            sa.Column("status_reason", sa.String(length=120), nullable=True),
            sa.Column("window_start", sa.Date(), nullable=False),
            sa.Column("window_end", sa.Date(), nullable=False),
            sa.Column("freshness_status", sa.String(length=20), nullable=False, server_default="fresh"),
            sa.Column("artifact_checksum", sa.String(length=64), nullable=True),
            sa.Column("artifact_payload", sa.JSON(), nullable=False),
            sa.Column("provider_name", sa.String(length=40), nullable=True),
            sa.Column("provider_message_id", sa.String(length=255), nullable=True),
            sa.Column("failure_message", sa.String(length=1000), nullable=True),
            sa.Column("planned_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["subscription_id"], ["growth_reporting_subscriptions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_growth_reporting_deliveries_subscription_id",
            "growth_reporting_deliveries",
            ["subscription_id"],
        )
        op.create_index(
            "ix_growth_reporting_deliveries_recipient_email",
            "growth_reporting_deliveries",
            ["recipient_email"],
        )
        op.create_index(
            "ix_growth_reporting_deliveries_audience_key",
            "growth_reporting_deliveries",
            ["audience_key"],
        )
        op.create_index(
            "ix_growth_reporting_deliveries_cadence",
            "growth_reporting_deliveries",
            ["cadence"],
        )
        op.create_index(
            "ix_growth_reporting_deliveries_delivery_status",
            "growth_reporting_deliveries",
            ["delivery_status"],
        )
        op.create_index(
            "ix_growth_reporting_deliveries_window_start",
            "growth_reporting_deliveries",
            ["window_start"],
        )
        op.create_index(
            "ix_growth_reporting_deliveries_window_end",
            "growth_reporting_deliveries",
            ["window_end"],
        )
        op.create_index(
            "ix_growth_reporting_deliveries_delivered_at",
            "growth_reporting_deliveries",
            ["delivered_at"],
        )
        op.create_index(
            "ix_growth_reporting_deliveries_planned_at",
            "growth_reporting_deliveries",
            ["planned_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("growth_reporting_deliveries"):
        op.drop_index("ix_growth_reporting_deliveries_planned_at", table_name="growth_reporting_deliveries")
        op.drop_index("ix_growth_reporting_deliveries_delivered_at", table_name="growth_reporting_deliveries")
        op.drop_index("ix_growth_reporting_deliveries_window_end", table_name="growth_reporting_deliveries")
        op.drop_index("ix_growth_reporting_deliveries_window_start", table_name="growth_reporting_deliveries")
        op.drop_index("ix_growth_reporting_deliveries_delivery_status", table_name="growth_reporting_deliveries")
        op.drop_index("ix_growth_reporting_deliveries_cadence", table_name="growth_reporting_deliveries")
        op.drop_index("ix_growth_reporting_deliveries_audience_key", table_name="growth_reporting_deliveries")
        op.drop_index("ix_growth_reporting_deliveries_recipient_email", table_name="growth_reporting_deliveries")
        op.drop_index("ix_growth_reporting_deliveries_subscription_id", table_name="growth_reporting_deliveries")
        op.drop_table("growth_reporting_deliveries")

    if inspector.has_table("growth_reporting_subscriptions"):
        op.drop_index(
            "ix_growth_reporting_subscriptions_updated_by_admin_user_id",
            table_name="growth_reporting_subscriptions",
        )
        op.drop_index(
            "ix_growth_reporting_subscriptions_created_by_admin_user_id",
            table_name="growth_reporting_subscriptions",
        )
        op.drop_index(
            "ix_growth_reporting_subscriptions_latest_delivery_status",
            table_name="growth_reporting_subscriptions",
        )
        op.drop_index(
            "ix_growth_reporting_subscriptions_next_delivery_at",
            table_name="growth_reporting_subscriptions",
        )
        op.drop_index(
            "ix_growth_reporting_subscriptions_subscription_status",
            table_name="growth_reporting_subscriptions",
        )
        op.drop_index("ix_growth_reporting_subscriptions_cadence", table_name="growth_reporting_subscriptions")
        op.drop_index("ix_growth_reporting_subscriptions_audience_key", table_name="growth_reporting_subscriptions")
        op.drop_index(
            "ix_growth_reporting_subscriptions_recipient_email",
            table_name="growth_reporting_subscriptions",
        )
        op.drop_table("growth_reporting_subscriptions")
