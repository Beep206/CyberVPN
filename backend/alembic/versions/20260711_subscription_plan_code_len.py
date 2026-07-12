"""Widen subscription plan code for explicit regional products.

Revision ID: 20260711_plan_code_len
Revises: 20260701_invite_source_len
Create Date: 2026-07-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260711_plan_code_len"
down_revision: str | Sequence[str] | None = "20260701_invite_source_len"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "subscription_plans",
        "plan_code",
        existing_type=sa.String(length=20),
        type_=sa.String(length=40),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM subscription_plans
                    WHERE length(plan_code) > 20
                ) THEN
                    RAISE EXCEPTION
                        'Cannot shrink subscription_plans.plan_code while values longer than 20 characters exist';
                END IF;
            END
            $$
            """
        )
    )
    op.alter_column(
        "subscription_plans",
        "plan_code",
        existing_type=sa.String(length=40),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
