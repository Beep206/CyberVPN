"""Widen invite code source for child invite issuance.

Revision ID: 20260701_invite_source_len
Revises: 20260701_vpn_tester_aaa_v3
Create Date: 2026-07-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260701_invite_source_len"
down_revision: str | Sequence[str] | None = "20260701_vpn_tester_aaa_v3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("invite_codes") as batch_op:
        batch_op.alter_column(
            "source",
            existing_type=sa.String(length=20),
            type_=sa.String(length=40),
            existing_nullable=False,
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE invite_codes "
            "SET source = 'child_after_redeem' "
            "WHERE source = 'child_after_redemption'"
        )
    )
    op.execute(sa.text("UPDATE invite_codes SET source = left(source, 20) WHERE length(source) > 20"))
    with op.batch_alter_table("invite_codes") as batch_op:
        batch_op.alter_column(
            "source",
            existing_type=sa.String(length=40),
            type_=sa.String(length=20),
            existing_nullable=False,
        )
