"""Referral attribution sessions and claim metadata.

Revision ID: 20260619_referral_attribution
Revises: 20260610_mobile_public_uid
Create Date: 2026-06-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260619_referral_attribution"
down_revision: str | Sequence[str] | None = "20260610_mobile_public_uid"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.Uuid()


def upgrade() -> None:
    uuid_type = _uuid_type()

    op.create_table(
        "referral_attribution_sessions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("growth_code_id", uuid_type, nullable=False),
        sa.Column("growth_code_touchpoint_id", uuid_type, nullable=True),
        sa.Column("referrer_user_id", uuid_type, nullable=False),
        sa.Column("claimed_by_user_id", uuid_type, nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("source_host", sa.String(length=255), nullable=True),
        sa.Column("source_path", sa.String(length=500), nullable=True),
        sa.Column("campaign_params", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("evidence_payload", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["claimed_by_user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["growth_code_touchpoint_id"], ["growth_code_touchpoints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["referrer_user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_referral_attribution_sessions_token_hash"),
    )
    op.create_index("ix_referral_attr_sessions_token_hash", "referral_attribution_sessions", ["token_hash"])
    op.create_index("ix_referral_attr_sessions_growth_code_id", "referral_attribution_sessions", ["growth_code_id"])
    op.create_index(
        "ix_referral_attr_sessions_growth_touchpoint_id",
        "referral_attribution_sessions",
        ["growth_code_touchpoint_id"],
    )
    op.create_index(
        "ix_referral_attr_sessions_referrer_user_id",
        "referral_attribution_sessions",
        ["referrer_user_id"],
    )
    op.create_index(
        "ix_referral_attr_sessions_claimed_by_user_id",
        "referral_attribution_sessions",
        ["claimed_by_user_id"],
    )
    op.create_index("ix_referral_attr_sessions_status", "referral_attribution_sessions", ["status"])
    op.create_index("ix_referral_attr_sessions_first_seen_at", "referral_attribution_sessions", ["first_seen_at"])
    op.create_index("ix_referral_attr_sessions_expires_at", "referral_attribution_sessions", ["expires_at"])
    op.create_index("ix_referral_attr_sessions_claimed_at", "referral_attribution_sessions", ["claimed_at"])

    op.add_column("mobile_users", sa.Column("referral_claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("mobile_users", sa.Column("referral_source_code_id", uuid_type, nullable=True))
    op.add_column("mobile_users", sa.Column("referral_attribution_session_id", uuid_type, nullable=True))
    op.create_index("ix_mobile_users_referred_by_user_id", "mobile_users", ["referred_by_user_id"])
    op.create_index("ix_mobile_users_referral_source_code_id", "mobile_users", ["referral_source_code_id"])
    op.create_index(
        "ix_mobile_users_referral_attribution_session_id",
        "mobile_users",
        ["referral_attribution_session_id"],
    )
    op.create_foreign_key(
        "fk_mobile_users_referral_source_code_id",
        "mobile_users",
        "growth_codes",
        ["referral_source_code_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_mobile_users_referral_attribution_session_id",
        "mobile_users",
        "referral_attribution_sessions",
        ["referral_attribution_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_mobile_users_no_self_referral",
        "mobile_users",
        "referred_by_user_id IS NULL OR referred_by_user_id <> id",
    )


def downgrade() -> None:
    op.drop_constraint("ck_mobile_users_no_self_referral", "mobile_users", type_="check")
    op.drop_constraint("fk_mobile_users_referral_attribution_session_id", "mobile_users", type_="foreignkey")
    op.drop_constraint("fk_mobile_users_referral_source_code_id", "mobile_users", type_="foreignkey")
    op.drop_index("ix_mobile_users_referral_attribution_session_id", table_name="mobile_users")
    op.drop_index("ix_mobile_users_referral_source_code_id", table_name="mobile_users")
    op.drop_index("ix_mobile_users_referred_by_user_id", table_name="mobile_users")
    op.drop_column("mobile_users", "referral_attribution_session_id")
    op.drop_column("mobile_users", "referral_source_code_id")
    op.drop_column("mobile_users", "referral_claimed_at")

    op.drop_index("ix_referral_attr_sessions_claimed_at", table_name="referral_attribution_sessions")
    op.drop_index("ix_referral_attr_sessions_expires_at", table_name="referral_attribution_sessions")
    op.drop_index("ix_referral_attr_sessions_first_seen_at", table_name="referral_attribution_sessions")
    op.drop_index("ix_referral_attr_sessions_status", table_name="referral_attribution_sessions")
    op.drop_index("ix_referral_attr_sessions_claimed_by_user_id", table_name="referral_attribution_sessions")
    op.drop_index("ix_referral_attr_sessions_referrer_user_id", table_name="referral_attribution_sessions")
    op.drop_index("ix_referral_attr_sessions_growth_touchpoint_id", table_name="referral_attribution_sessions")
    op.drop_index("ix_referral_attr_sessions_growth_code_id", table_name="referral_attribution_sessions")
    op.drop_index("ix_referral_attr_sessions_token_hash", table_name="referral_attribution_sessions")
    op.drop_table("referral_attribution_sessions")
