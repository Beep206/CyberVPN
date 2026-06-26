"""Allow internal-settlement order status.

Revision ID: 20260625_internal_status
Revises: 20260625_growth_v6_foundation
Create Date: 2026-06-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260625_internal_status"
down_revision: str | Sequence[str] | None = "20260625_growth_v6_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.alter_column(
            "settlement_status",
            existing_type=sa.String(length=20),
            type_=sa.String(length=40),
            existing_nullable=False,
            existing_server_default="pending_payment",
        )


def downgrade() -> None:
    op.execute(
        "UPDATE orders SET settlement_status = 'pending_payment' "
        "WHERE settlement_status = 'pending_internal_settlement'"
    )
    with op.batch_alter_table("orders") as batch_op:
        batch_op.alter_column(
            "settlement_status",
            existing_type=sa.String(length=40),
            type_=sa.String(length=20),
            existing_nullable=False,
            existing_server_default="pending_payment",
        )
