"""Persist observed Remnawave consumer-group lag for Admin health.

Revision ID: 20260901_stream_group_lag
Revises: 20260831_gift_redemption_safety
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260901_stream_group_lag"
down_revision: str | Sequence[str] | None = "20260831_gift_redemption_safety"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "remnawave_stream_checkpoints",
        sa.Column("observed_group_lag", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_remnawave_stream_checkpoint_group_lag_nonnegative",
        "remnawave_stream_checkpoints",
        "observed_group_lag IS NULL OR observed_group_lag >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_remnawave_stream_checkpoint_group_lag_nonnegative",
        "remnawave_stream_checkpoints",
        type_="check",
    )
    op.drop_column("remnawave_stream_checkpoints", "observed_group_lag")
