"""Add public numeric UID to mobile users.

Revision ID: 20260610_mobile_public_uid
Revises: 20260531_offer_channels_jsonb, 20260603_passkey_credentials, 20260609_refresh_token_owner
Create Date: 2026-06-10
"""

from __future__ import annotations

import secrets
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260610_mobile_public_uid"
down_revision: str | Sequence[str] | None = (
    "20260531_offer_channels_jsonb",
    "20260603_passkey_credentials",
    "20260609_refresh_token_owner",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PUBLIC_UID_MIN = 10_000_000
PUBLIC_UID_MAX = 99_999_999
PUBLIC_UID_RANGE = PUBLIC_UID_MAX - PUBLIC_UID_MIN + 1


def _generate_public_uid(used_values: set[int]) -> int:
    for _attempt in range(100):
        candidate = PUBLIC_UID_MIN + secrets.randbelow(PUBLIC_UID_RANGE)
        if candidate not in used_values:
            used_values.add(candidate)
            return candidate

    raise RuntimeError("Unable to allocate unique mobile user public_uid during migration")


def upgrade() -> None:
    op.add_column("mobile_users", sa.Column("public_uid", sa.BigInteger(), nullable=True))

    bind = op.get_bind()
    used_values = {
        int(row.public_uid)
        for row in bind.execute(sa.text("select public_uid from mobile_users where public_uid is not null"))
    }
    rows = bind.execute(sa.text("select id from mobile_users where public_uid is null order by created_at, id")).all()
    for row in rows:
        bind.execute(
            sa.text("update mobile_users set public_uid = :public_uid where id = :id"),
            {"public_uid": _generate_public_uid(used_values), "id": row.id},
        )

    op.alter_column("mobile_users", "public_uid", existing_type=sa.BigInteger(), nullable=False)
    op.create_index("ix_mobile_users_public_uid", "mobile_users", ["public_uid"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_mobile_users_public_uid", table_name="mobile_users")
    op.drop_column("mobile_users", "public_uid")
