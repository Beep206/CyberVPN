"""Partner application onboarding draft, lanes, review requests, and attachments."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260420_phase9_partner_application_onboarding"
down_revision = "20260419_rb002_partner_workspace_workflows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partner_application_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("applicant_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("draft_payload", sa.JSON(), nullable=False),
        sa.Column("review_ready", sa.Boolean(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["applicant_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("partner_account_id"),
        sa.UniqueConstraint("applicant_admin_user_id"),
    )
    op.create_index(
        "ix_partner_application_drafts_partner_account_id",
        "partner_application_drafts",
        ["partner_account_id"],
    )
    op.create_index(
        "ix_partner_application_drafts_applicant_admin_user_id",
        "partner_application_drafts",
        ["applicant_admin_user_id"],
    )

    op.create_table(
        "partner_lane_applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("partner_application_draft_id", sa.Uuid(), nullable=False),
        sa.Column("lane_key", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("application_payload", sa.JSON(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason_code", sa.String(length=80), nullable=True),
        sa.Column("decision_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["partner_application_draft_id"],
            ["partner_application_drafts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "partner_account_id",
            "lane_key",
            name="uq_partner_lane_applications_account_lane",
        ),
    )
    op.create_index(
        "ix_partner_lane_applications_partner_account_id",
        "partner_lane_applications",
        ["partner_account_id"],
    )
    op.create_index(
        "ix_partner_lane_applications_partner_application_draft_id",
        "partner_lane_applications",
        ["partner_application_draft_id"],
    )
    op.create_index(
        "ix_partner_lane_applications_lane_key",
        "partner_lane_applications",
        ["lane_key"],
    )
    op.create_index(
        "ix_partner_lane_applications_status",
        "partner_lane_applications",
        ["status"],
    )

    op.create_table(
        "partner_application_review_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("partner_application_draft_id", sa.Uuid(), nullable=False),
        sa.Column("lane_application_id", sa.Uuid(), nullable=True),
        sa.Column("request_kind", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("required_fields", sa.JSON(), nullable=False),
        sa.Column("required_attachments", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("requested_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["partner_application_draft_id"],
            ["partner_application_drafts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lane_application_id"],
            ["partner_lane_applications.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_admin_user_id"],
            ["admin_users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_admin_user_id"],
            ["admin_users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_partner_application_review_requests_partner_account_id",
        "partner_application_review_requests",
        ["partner_account_id"],
    )
    op.create_index(
        "ix_partner_application_review_requests_partner_application_draft_id",
        "partner_application_review_requests",
        ["partner_application_draft_id"],
    )
    op.create_index(
        "ix_partner_application_review_requests_lane_application_id",
        "partner_application_review_requests",
        ["lane_application_id"],
    )
    op.create_index(
        "ix_partner_application_review_requests_request_kind",
        "partner_application_review_requests",
        ["request_kind"],
    )
    op.create_index(
        "ix_partner_application_review_requests_status",
        "partner_application_review_requests",
        ["status"],
    )
    op.create_index(
        "ix_partner_application_review_requests_requested_by_admin_user_id",
        "partner_application_review_requests",
        ["requested_by_admin_user_id"],
    )
    op.create_index(
        "ix_partner_application_review_requests_resolved_by_admin_user_id",
        "partner_application_review_requests",
        ["resolved_by_admin_user_id"],
    )
    op.create_index(
        "ix_partner_application_review_requests_requested_at",
        "partner_application_review_requests",
        ["requested_at"],
    )

    op.create_table(
        "partner_application_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("partner_application_draft_id", sa.Uuid(), nullable=False),
        sa.Column("lane_application_id", sa.Uuid(), nullable=True),
        sa.Column("review_request_id", sa.Uuid(), nullable=True),
        sa.Column("attachment_type", sa.String(length=40), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("attachment_metadata", sa.JSON(), nullable=False),
        sa.Column("uploaded_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["partner_application_draft_id"],
            ["partner_application_drafts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lane_application_id"],
            ["partner_lane_applications.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["review_request_id"],
            ["partner_application_review_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_admin_user_id"],
            ["admin_users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        "ix_partner_application_attachments_partner_account_id",
        "partner_application_attachments",
        ["partner_account_id"],
    )
    op.create_index(
        "ix_partner_application_attachments_partner_application_draft_id",
        "partner_application_attachments",
        ["partner_application_draft_id"],
    )
    op.create_index(
        "ix_partner_application_attachments_lane_application_id",
        "partner_application_attachments",
        ["lane_application_id"],
    )
    op.create_index(
        "ix_partner_application_attachments_review_request_id",
        "partner_application_attachments",
        ["review_request_id"],
    )
    op.create_index(
        "ix_partner_application_attachments_attachment_type",
        "partner_application_attachments",
        ["attachment_type"],
    )
    op.create_index(
        "ix_partner_application_attachments_uploaded_by_admin_user_id",
        "partner_application_attachments",
        ["uploaded_by_admin_user_id"],
    )
    op.create_index(
        "ix_partner_application_attachments_created_at",
        "partner_application_attachments",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_partner_application_attachments_created_at", table_name="partner_application_attachments")
    op.drop_index(
        "ix_partner_application_attachments_uploaded_by_admin_user_id",
        table_name="partner_application_attachments",
    )
    op.drop_index("ix_partner_application_attachments_attachment_type", table_name="partner_application_attachments")
    op.drop_index("ix_partner_application_attachments_review_request_id", table_name="partner_application_attachments")
    op.drop_index("ix_partner_application_attachments_lane_application_id", table_name="partner_application_attachments")
    op.drop_index(
        "ix_partner_application_attachments_partner_application_draft_id",
        table_name="partner_application_attachments",
    )
    op.drop_index("ix_partner_application_attachments_partner_account_id", table_name="partner_application_attachments")
    op.drop_table("partner_application_attachments")

    op.drop_index("ix_partner_application_review_requests_requested_at", table_name="partner_application_review_requests")
    op.drop_index(
        "ix_partner_application_review_requests_resolved_by_admin_user_id",
        table_name="partner_application_review_requests",
    )
    op.drop_index(
        "ix_partner_application_review_requests_requested_by_admin_user_id",
        table_name="partner_application_review_requests",
    )
    op.drop_index("ix_partner_application_review_requests_status", table_name="partner_application_review_requests")
    op.drop_index(
        "ix_partner_application_review_requests_request_kind",
        table_name="partner_application_review_requests",
    )
    op.drop_index(
        "ix_partner_application_review_requests_lane_application_id",
        table_name="partner_application_review_requests",
    )
    op.drop_index(
        "ix_partner_application_review_requests_partner_application_draft_id",
        table_name="partner_application_review_requests",
    )
    op.drop_index(
        "ix_partner_application_review_requests_partner_account_id",
        table_name="partner_application_review_requests",
    )
    op.drop_table("partner_application_review_requests")

    op.drop_index("ix_partner_lane_applications_status", table_name="partner_lane_applications")
    op.drop_index("ix_partner_lane_applications_lane_key", table_name="partner_lane_applications")
    op.drop_index(
        "ix_partner_lane_applications_partner_application_draft_id",
        table_name="partner_lane_applications",
    )
    op.drop_index("ix_partner_lane_applications_partner_account_id", table_name="partner_lane_applications")
    op.drop_table("partner_lane_applications")

    op.drop_index(
        "ix_partner_application_drafts_applicant_admin_user_id",
        table_name="partner_application_drafts",
    )
    op.drop_index("ix_partner_application_drafts_partner_account_id", table_name="partner_application_drafts")
    op.drop_table("partner_application_drafts")
