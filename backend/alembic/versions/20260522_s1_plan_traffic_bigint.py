"""Use BIGINT for subscription plan traffic limits.

Revision ID: 20260522_s1_plan_traffic_bigint
Revises: 20260520_stage1_webhook_logs
Create Date: 2026-05-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260522_s1_plan_traffic_bigint"
down_revision: str | Sequence[str] | None = "20260520_stage1_webhook_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "subscription_plans",
        "traffic_limit_bytes",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "subscription_plans",
        "traffic_limit_bytes",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
