"""Serialize one-use gift redemption and enforce a single terminal claim.

Revision ID: 20260831_gift_redemption_safety
Revises: 20260831_drop_receipts
Create Date: 2026-08-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260831_gift_redemption_safety"
down_revision: str | Sequence[str] | None = "20260831_drop_receipts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX_NAME = "uq_growth_code_redemptions_redeemed_gift"


def upgrade() -> None:
    duplicate = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT growth_code_id "
                "FROM growth_code_redemptions "
                "WHERE code_type = 'gift' AND status = 'redeemed' "
                "GROUP BY growth_code_id "
                "HAVING count(*) > 1 "
                "LIMIT 1"
            )
        )
        .first()
    )
    if duplicate is not None:
        raise RuntimeError("Duplicate redeemed gift rows must be reconciled before enabling the one-use gift invariant")

    op.create_index(
        _INDEX_NAME,
        "growth_code_redemptions",
        ["growth_code_id"],
        unique=True,
        postgresql_where=sa.text("code_type = 'gift' AND status = 'redeemed'"),
        sqlite_where=sa.text("code_type = 'gift' AND status = 'redeemed'"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="growth_code_redemptions")
