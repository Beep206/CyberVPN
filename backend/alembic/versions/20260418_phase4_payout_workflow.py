"""Phase 4 payout instructions and executions."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260418_phase4_payout_workflow"
down_revision = "20260418_phase4_partner_payout_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payout_instructions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("partner_statement_id", sa.Uuid(), nullable=False),
        sa.Column("partner_payout_account_id", sa.Uuid(), nullable=False),
        sa.Column("instruction_key", sa.String(length=160), nullable=False),
        sa.Column("instruction_status", sa.String(length=30), nullable=False, server_default="pending_approval"),
        sa.Column("payout_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("instruction_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason_code", sa.String(length=80), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_statement_id"], ["partner_statements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["partner_payout_account_id"],
            ["partner_payout_accounts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rejected_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("partner_statement_id"),
    )
    op.create_index("ix_payout_instructions_partner_account_id", "payout_instructions", ["partner_account_id"])
    op.create_index("ix_payout_instructions_partner_statement_id", "payout_instructions", ["partner_statement_id"])
    op.create_index(
        "ix_payout_instructions_partner_payout_account_id",
        "payout_instructions",
        ["partner_payout_account_id"],
    )
    op.create_index("ix_payout_instructions_instruction_key", "payout_instructions", ["instruction_key"], unique=True)
    op.create_index(
        "ix_payout_instructions_instruction_status",
        "payout_instructions",
        ["instruction_status"],
    )
    op.create_index(
        "ix_payout_instructions_created_by_admin_user_id",
        "payout_instructions",
        ["created_by_admin_user_id"],
    )
    op.create_index(
        "ix_payout_instructions_approved_by_admin_user_id",
        "payout_instructions",
        ["approved_by_admin_user_id"],
    )
    op.create_index("ix_payout_instructions_approved_at", "payout_instructions", ["approved_at"])
    op.create_index(
        "ix_payout_instructions_rejected_by_admin_user_id",
        "payout_instructions",
        ["rejected_by_admin_user_id"],
    )
    op.create_index("ix_payout_instructions_rejected_at", "payout_instructions", ["rejected_at"])
    op.create_index("ix_payout_instructions_completed_at", "payout_instructions", ["completed_at"])

    op.create_table(
        "payout_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payout_instruction_id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("partner_statement_id", sa.Uuid(), nullable=False),
        sa.Column("partner_payout_account_id", sa.Uuid(), nullable=False),
        sa.Column("execution_key", sa.String(length=180), nullable=False),
        sa.Column("execution_mode", sa.String(length=20), nullable=False, server_default="dry_run"),
        sa.Column("execution_status", sa.String(length=20), nullable=False, server_default="requested"),
        sa.Column("request_idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("external_reference", sa.String(length=255), nullable=True),
        sa.Column("execution_payload", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=False),
        sa.Column("requested_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("submitted_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconciled_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payout_instruction_id"], ["payout_instructions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_statement_id"], ["partner_statements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["partner_payout_account_id"],
            ["partner_payout_accounts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["requested_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submitted_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["completed_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reconciled_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "payout_instruction_id",
            "request_idempotency_key",
            name="uq_payout_execution_instruction_idempotency",
        ),
    )
    op.create_index("ix_payout_executions_payout_instruction_id", "payout_executions", ["payout_instruction_id"])
    op.create_index("ix_payout_executions_partner_account_id", "payout_executions", ["partner_account_id"])
    op.create_index("ix_payout_executions_partner_statement_id", "payout_executions", ["partner_statement_id"])
    op.create_index(
        "ix_payout_executions_partner_payout_account_id",
        "payout_executions",
        ["partner_payout_account_id"],
    )
    op.create_index("ix_payout_executions_execution_key", "payout_executions", ["execution_key"], unique=True)
    op.create_index("ix_payout_executions_execution_mode", "payout_executions", ["execution_mode"])
    op.create_index("ix_payout_executions_execution_status", "payout_executions", ["execution_status"])
    op.create_index(
        "ix_payout_executions_request_idempotency_key",
        "payout_executions",
        ["request_idempotency_key"],
    )
    op.create_index("ix_payout_executions_external_reference", "payout_executions", ["external_reference"])
    op.create_index(
        "ix_payout_executions_requested_by_admin_user_id",
        "payout_executions",
        ["requested_by_admin_user_id"],
    )
    op.create_index(
        "ix_payout_executions_submitted_by_admin_user_id",
        "payout_executions",
        ["submitted_by_admin_user_id"],
    )
    op.create_index("ix_payout_executions_submitted_at", "payout_executions", ["submitted_at"])
    op.create_index(
        "ix_payout_executions_completed_by_admin_user_id",
        "payout_executions",
        ["completed_by_admin_user_id"],
    )
    op.create_index("ix_payout_executions_completed_at", "payout_executions", ["completed_at"])
    op.create_index(
        "ix_payout_executions_reconciled_by_admin_user_id",
        "payout_executions",
        ["reconciled_by_admin_user_id"],
    )
    op.create_index("ix_payout_executions_reconciled_at", "payout_executions", ["reconciled_at"])


def downgrade() -> None:
    op.drop_index("ix_payout_executions_reconciled_at", table_name="payout_executions")
    op.drop_index("ix_payout_executions_reconciled_by_admin_user_id", table_name="payout_executions")
    op.drop_index("ix_payout_executions_completed_at", table_name="payout_executions")
    op.drop_index("ix_payout_executions_completed_by_admin_user_id", table_name="payout_executions")
    op.drop_index("ix_payout_executions_submitted_at", table_name="payout_executions")
    op.drop_index("ix_payout_executions_submitted_by_admin_user_id", table_name="payout_executions")
    op.drop_index("ix_payout_executions_requested_by_admin_user_id", table_name="payout_executions")
    op.drop_index("ix_payout_executions_external_reference", table_name="payout_executions")
    op.drop_index("ix_payout_executions_request_idempotency_key", table_name="payout_executions")
    op.drop_index("ix_payout_executions_execution_status", table_name="payout_executions")
    op.drop_index("ix_payout_executions_execution_mode", table_name="payout_executions")
    op.drop_index("ix_payout_executions_execution_key", table_name="payout_executions")
    op.drop_index("ix_payout_executions_partner_payout_account_id", table_name="payout_executions")
    op.drop_index("ix_payout_executions_partner_statement_id", table_name="payout_executions")
    op.drop_index("ix_payout_executions_partner_account_id", table_name="payout_executions")
    op.drop_index("ix_payout_executions_payout_instruction_id", table_name="payout_executions")
    op.drop_table("payout_executions")

    op.drop_index("ix_payout_instructions_completed_at", table_name="payout_instructions")
    op.drop_index("ix_payout_instructions_rejected_at", table_name="payout_instructions")
    op.drop_index("ix_payout_instructions_rejected_by_admin_user_id", table_name="payout_instructions")
    op.drop_index("ix_payout_instructions_approved_at", table_name="payout_instructions")
    op.drop_index("ix_payout_instructions_approved_by_admin_user_id", table_name="payout_instructions")
    op.drop_index("ix_payout_instructions_created_by_admin_user_id", table_name="payout_instructions")
    op.drop_index("ix_payout_instructions_instruction_status", table_name="payout_instructions")
    op.drop_index("ix_payout_instructions_instruction_key", table_name="payout_instructions")
    op.drop_index("ix_payout_instructions_partner_payout_account_id", table_name="payout_instructions")
    op.drop_index("ix_payout_instructions_partner_statement_id", table_name="payout_instructions")
    op.drop_index("ix_payout_instructions_partner_account_id", table_name="payout_instructions")
    op.drop_table("payout_instructions")
