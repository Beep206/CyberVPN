"""Partner bot runtime and provisioning foundation."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260422_phase18_partner_bot_foundation"
down_revision = "20260422_phase17_customer_growth_notification_delivery_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partner_bots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("storefront_id", sa.Uuid(), nullable=True),
        sa.Column("bot_key", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("short_description", sa.String(length=255), nullable=True),
        sa.Column("long_description", sa.Text(), nullable=True),
        sa.Column("telegram_bot_id", sa.String(length=64), nullable=True),
        sa.Column("telegram_username", sa.String(length=64), nullable=True),
        sa.Column("managed_by_bot_id", sa.String(length=64), nullable=True),
        sa.Column("default_locale", sa.String(length=16), nullable=False, server_default="en-EN"),
        sa.Column("primary_color", sa.String(length=20), nullable=True),
        sa.Column("provisioning_path", sa.String(length=20), nullable=False, server_default="managed_bot"),
        sa.Column("token_status", sa.String(length=20), nullable=False, server_default="missing"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("release_channel", sa.String(length=20), nullable=False, server_default="stable"),
        sa.Column("provisioning_last_error", sa.Text(), nullable=True),
        sa.Column("provisioning_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provisioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspension_reason_code", sa.String(length=80), nullable=True),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("partner_account_id", "bot_key", name="uq_partner_bots_workspace_bot_key"),
    )
    op.create_index("ix_partner_bots_partner_account_id", "partner_bots", ["partner_account_id"])
    op.create_index("ix_partner_bots_storefront_id", "partner_bots", ["storefront_id"])
    op.create_index("ix_partner_bots_bot_key", "partner_bots", ["bot_key"])
    op.create_index("ix_partner_bots_telegram_bot_id", "partner_bots", ["telegram_bot_id"])
    op.create_index("ix_partner_bots_telegram_username", "partner_bots", ["telegram_username"])
    op.create_index("ix_partner_bots_managed_by_bot_id", "partner_bots", ["managed_by_bot_id"])
    op.create_index("ix_partner_bots_provisioning_path", "partner_bots", ["provisioning_path"])
    op.create_index("ix_partner_bots_token_status", "partner_bots", ["token_status"])
    op.create_index("ix_partner_bots_status", "partner_bots", ["status"])
    op.create_index("ix_partner_bots_created_by_admin_user_id", "partner_bots", ["created_by_admin_user_id"])
    op.create_index("ix_partner_bots_updated_by_admin_user_id", "partner_bots", ["updated_by_admin_user_id"])

    op.create_table(
        "partner_bot_provisioning_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_bot_id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("provisioning_path", sa.String(length=20), nullable=False, server_default="managed_bot"),
        sa.Column("job_status", sa.String(length=40), nullable=False, server_default="queued"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("result_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["partner_bot_id"], ["partner_bots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_partner_bot_provisioning_jobs_partner_bot_id",
        "partner_bot_provisioning_jobs",
        ["partner_bot_id"],
    )
    op.create_index(
        "ix_partner_bot_provisioning_jobs_partner_account_id",
        "partner_bot_provisioning_jobs",
        ["partner_account_id"],
    )
    op.create_index(
        "ix_partner_bot_provisioning_jobs_requested_by_admin_user_id",
        "partner_bot_provisioning_jobs",
        ["requested_by_admin_user_id"],
    )
    op.create_index(
        "ix_partner_bot_provisioning_jobs_job_status",
        "partner_bot_provisioning_jobs",
        ["job_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_partner_bot_provisioning_jobs_job_status", table_name="partner_bot_provisioning_jobs")
    op.drop_index(
        "ix_partner_bot_provisioning_jobs_requested_by_admin_user_id",
        table_name="partner_bot_provisioning_jobs",
    )
    op.drop_index("ix_partner_bot_provisioning_jobs_partner_account_id", table_name="partner_bot_provisioning_jobs")
    op.drop_index("ix_partner_bot_provisioning_jobs_partner_bot_id", table_name="partner_bot_provisioning_jobs")
    op.drop_table("partner_bot_provisioning_jobs")

    op.drop_index("ix_partner_bots_updated_by_admin_user_id", table_name="partner_bots")
    op.drop_index("ix_partner_bots_created_by_admin_user_id", table_name="partner_bots")
    op.drop_index("ix_partner_bots_status", table_name="partner_bots")
    op.drop_index("ix_partner_bots_token_status", table_name="partner_bots")
    op.drop_index("ix_partner_bots_provisioning_path", table_name="partner_bots")
    op.drop_index("ix_partner_bots_managed_by_bot_id", table_name="partner_bots")
    op.drop_index("ix_partner_bots_telegram_username", table_name="partner_bots")
    op.drop_index("ix_partner_bots_telegram_bot_id", table_name="partner_bots")
    op.drop_index("ix_partner_bots_bot_key", table_name="partner_bots")
    op.drop_index("ix_partner_bots_storefront_id", table_name="partner_bots")
    op.drop_index("ix_partner_bots_partner_account_id", table_name="partner_bots")
    op.drop_table("partner_bots")
