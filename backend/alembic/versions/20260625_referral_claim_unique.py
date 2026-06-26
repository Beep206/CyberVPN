"""Enforce one claimed referral attribution session per user.

Revision ID: 20260625_referral_claim_unique
Revises: 20260622_partner_owner_ranges
Create Date: 2026-06-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260625_referral_claim_unique"
down_revision: str | Sequence[str] | None = "20260622_partner_owner_ranges"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CLAIMED_BY_UNIQUE_INDEX = "uq_referral_attr_sessions_claimed_by_user_id"


def upgrade() -> None:
    bind = op.get_bind()
    _assert_no_duplicate_claimed_users(bind)
    op.create_index(
        CLAIMED_BY_UNIQUE_INDEX,
        "referral_attribution_sessions",
        ["claimed_by_user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        CLAIMED_BY_UNIQUE_INDEX,
        table_name="referral_attribution_sessions",
    )


def _assert_no_duplicate_claimed_users(bind: sa.Connection) -> None:
    duplicate = bind.execute(
        sa.text(
            """
            SELECT claimed_by_user_id, COUNT(*) AS claimed_count
            FROM referral_attribution_sessions
            WHERE claimed_by_user_id IS NOT NULL
            GROUP BY claimed_by_user_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot add unique referral claim index while a user has multiple claimed "
            "referral attribution sessions. Resolve duplicate claimed_by_user_id rows first."
        )
