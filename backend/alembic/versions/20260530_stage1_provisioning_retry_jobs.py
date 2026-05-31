"""Create durable Stage 1 provisioning retry jobs table.

Revision ID: 20260530_s1_provisioning_retry
Revises: 20260527_msub08_service_identity
Create Date: 2026-05-30 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260530_s1_provisioning_retry"
down_revision: str | Sequence[str] | None = "20260527_msub08_service_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def _json_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB()
    return sa.JSON()


def _empty_json_default() -> sa.TextClause:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.text("'{}'::jsonb")
    return sa.text("'{}'")


def upgrade() -> None:
    op.create_table(
        "stage1_provisioning_retry_jobs",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("queue_name", sa.String(length=80), nullable=False),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("correlation_id", sa.String(length=160), nullable=False),
        sa.Column("customer_account_id", _uuid_type(), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.String(length=80), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=False),
        sa.Column("provisioning_state", sa.String(length=80), nullable=False),
        sa.Column("payment_state", sa.String(length=80), nullable=True),
        sa.Column("support_state", sa.String(length=80), nullable=False),
        sa.Column("request_payload", _json_type(), nullable=False),
        sa.Column("result_payload", _json_type(), nullable=False, server_default=_empty_json_default()),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=120), nullable=False, server_default=""),
        sa.Column(
            "last_error_message",
            sa.String(length=240),
            nullable=False,
            server_default="Remnawave provisioning attempt failed; details redacted.",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "operation",
            "correlation_id",
            name="uq_stage1_provisioning_retry_operation_correlation",
        ),
    )
    op.create_index(
        "ix_stage1_provisioning_retry_customer_account_id",
        "stage1_provisioning_retry_jobs",
        ["customer_account_id"],
        unique=False,
    )
    op.create_index("ix_stage1_provisioning_retry_state", "stage1_provisioning_retry_jobs", ["state"], unique=False)
    op.create_index(
        "ix_stage1_provisioning_retry_due",
        "stage1_provisioning_retry_jobs",
        ["queue_name", "state", "next_attempt_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_stage1_provisioning_retry_due", table_name="stage1_provisioning_retry_jobs")
    op.drop_index("ix_stage1_provisioning_retry_state", table_name="stage1_provisioning_retry_jobs")
    op.drop_index("ix_stage1_provisioning_retry_customer_account_id", table_name="stage1_provisioning_retry_jobs")
    op.drop_table("stage1_provisioning_retry_jobs")
