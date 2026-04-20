"""Phase 8 risk governance workflows."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260419_phase8_risk_governance_workflows"
down_revision = "20260418_phase7_partner_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risk_review_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("risk_review_id", sa.Uuid(), nullable=False),
        sa.Column("attachment_type", sa.String(length=40), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("attachment_metadata", sa.JSON(), nullable=False),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["risk_review_id"], ["risk_reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        "ix_risk_review_attachments_risk_review_id",
        "risk_review_attachments",
        ["risk_review_id"],
    )
    op.create_index(
        "ix_risk_review_attachments_attachment_type",
        "risk_review_attachments",
        ["attachment_type"],
    )
    op.create_index(
        "ix_risk_review_attachments_created_by_admin_user_id",
        "risk_review_attachments",
        ["created_by_admin_user_id"],
    )

    op.create_table(
        "governance_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("risk_subject_id", sa.Uuid(), nullable=False),
        sa.Column("risk_review_id", sa.Uuid(), nullable=True),
        sa.Column("action_type", sa.String(length=40), nullable=False),
        sa.Column("action_status", sa.String(length=20), nullable=False, server_default="requested"),
        sa.Column("target_type", sa.String(length=60), nullable=True),
        sa.Column("target_ref", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("action_payload", sa.JSON(), nullable=False),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("applied_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["risk_subject_id"], ["risk_subjects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["risk_review_id"], ["risk_reviews.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["applied_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_governance_actions_risk_subject_id", "governance_actions", ["risk_subject_id"])
    op.create_index("ix_governance_actions_risk_review_id", "governance_actions", ["risk_review_id"])
    op.create_index("ix_governance_actions_action_type", "governance_actions", ["action_type"])
    op.create_index("ix_governance_actions_action_status", "governance_actions", ["action_status"])
    op.create_index("ix_governance_actions_target_type", "governance_actions", ["target_type"])
    op.create_index("ix_governance_actions_target_ref", "governance_actions", ["target_ref"])
    op.create_index(
        "ix_governance_actions_created_by_admin_user_id",
        "governance_actions",
        ["created_by_admin_user_id"],
    )
    op.create_index(
        "ix_governance_actions_applied_by_admin_user_id",
        "governance_actions",
        ["applied_by_admin_user_id"],
    )
    op.create_index("ix_governance_actions_applied_at", "governance_actions", ["applied_at"])


def downgrade() -> None:
    op.drop_index("ix_governance_actions_applied_at", table_name="governance_actions")
    op.drop_index(
        "ix_governance_actions_applied_by_admin_user_id",
        table_name="governance_actions",
    )
    op.drop_index(
        "ix_governance_actions_created_by_admin_user_id",
        table_name="governance_actions",
    )
    op.drop_index("ix_governance_actions_target_ref", table_name="governance_actions")
    op.drop_index("ix_governance_actions_target_type", table_name="governance_actions")
    op.drop_index("ix_governance_actions_action_status", table_name="governance_actions")
    op.drop_index("ix_governance_actions_action_type", table_name="governance_actions")
    op.drop_index("ix_governance_actions_risk_review_id", table_name="governance_actions")
    op.drop_index("ix_governance_actions_risk_subject_id", table_name="governance_actions")
    op.drop_table("governance_actions")

    op.drop_index(
        "ix_risk_review_attachments_created_by_admin_user_id",
        table_name="risk_review_attachments",
    )
    op.drop_index(
        "ix_risk_review_attachments_attachment_type",
        table_name="risk_review_attachments",
    )
    op.drop_index(
        "ix_risk_review_attachments_risk_review_id",
        table_name="risk_review_attachments",
    )
    op.drop_table("risk_review_attachments")
