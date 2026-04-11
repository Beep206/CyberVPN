"""Add customer_staff_notes table for admin customer support workflows.

Revision ID: 20260410_customer_staff_notes
Revises: f4916143ce02
Create Date: 2026-04-10
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "20260410_customer_staff_notes"
down_revision: str | None = "f4916143ce02"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_staff_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("mobile_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "admin_id",
            UUID(as_uuid=True),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("category", sa.String(length=20), nullable=False, server_default="general"),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_customer_staff_notes_user_id",
        "customer_staff_notes",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_customer_staff_notes_admin_id",
        "customer_staff_notes",
        ["admin_id"],
        unique=False,
    )
    op.create_index(
        "ix_customer_staff_notes_created_at",
        "customer_staff_notes",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_customer_staff_notes_created_at", table_name="customer_staff_notes")
    op.drop_index("ix_customer_staff_notes_admin_id", table_name="customer_staff_notes")
    op.drop_index("ix_customer_staff_notes_user_id", table_name="customer_staff_notes")
    op.drop_table("customer_staff_notes")
