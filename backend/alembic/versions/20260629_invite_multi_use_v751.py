"""Add multi-use invite code accounting for Growth Codes v7.5.1.

Revision ID: 20260629_invite_multi_use_v751
Revises: 20260629_invite_lifetime_v72
Create Date: 2026-06-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260629_invite_multi_use_v751"
down_revision: str | Sequence[str] | None = "20260629_invite_lifetime_v72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    json_type = _json_type(bind)
    json_empty_object = _json_default(bind, "{}")

    with op.batch_alter_table("invite_codes") as batch_op:
        batch_op.add_column(sa.Column("usage_mode", sa.String(length=20), nullable=False, server_default="single_use"))
        batch_op.add_column(sa.Column("max_redemptions", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("redeemed_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("active_redemptions_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("reversed_redemptions_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("first_redeemed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("last_redeemed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("exhausted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("per_user_redemption_cap", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("multi_use_policy", json_type, nullable=False, server_default=json_empty_object))
        batch_op.create_index("ix_invite_codes_usage_mode", ["usage_mode"])

    with op.batch_alter_table("invite_campaign_versions") as batch_op:
        batch_op.add_column(
            sa.Column("root_usage_mode", sa.String(length=20), nullable=False, server_default="single_use")
        )
        batch_op.add_column(sa.Column("root_max_redemptions", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("root_per_user_redemption_cap", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(
            sa.Column("child_usage_mode", sa.String(length=20), nullable=False, server_default="single_use")
        )
        batch_op.add_column(sa.Column("child_max_redemptions", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("child_per_user_redemption_cap", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(sa.Column("multi_use_policy", json_type, nullable=False, server_default=json_empty_object))

    with op.batch_alter_table("invite_batches") as batch_op:
        batch_op.add_column(sa.Column("usage_mode", sa.String(length=20), nullable=False, server_default="single_use"))
        batch_op.add_column(sa.Column("max_redemptions_per_code", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("per_user_redemption_cap", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("multi_use_policy", json_type, nullable=False, server_default=json_empty_object))
        batch_op.create_index("ix_invite_batches_usage_mode", ["usage_mode"])

    with op.batch_alter_table("invite_redemptions") as batch_op:
        batch_op.add_column(
            sa.Column("usage_mode_snapshot", sa.String(length=20), nullable=False, server_default="single_use")
        )
        batch_op.add_column(sa.Column("redemption_sequence", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("code_redemptions_count_after", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("device_key_hash", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("client_ip_hash", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("user_agent_hash", sa.String(length=128), nullable=True))
        batch_op.create_index("ix_invite_redemptions_usage_mode_snapshot", ["usage_mode_snapshot"])

    _backfill_legacy_multi_use_columns(bind)

    op.drop_index("uq_invite_redemptions_redeemed_invite_code_id", table_name="invite_redemptions")
    op.create_index(
        "uq_invite_redemptions_redeemed_invite_code_id",
        "invite_redemptions",
        ["invite_code_id"],
        unique=True,
        postgresql_where=sa.text("status = 'redeemed' AND usage_mode_snapshot = 'single_use'"),
        sqlite_where=sa.text("status = 'redeemed' AND usage_mode_snapshot = 'single_use'"),
    )
    op.create_index(
        "uq_invite_redemptions_code_user_active",
        "invite_redemptions",
        ["invite_code_id", "invitee_user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'redeemed'"),
        sqlite_where=sa.text("status = 'redeemed'"),
    )

    if not is_sqlite:
        _create_constraints()


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    _assert_safe_downgrade(bind)

    if not is_sqlite:
        _drop_constraints()

    op.drop_index("uq_invite_redemptions_code_user_active", table_name="invite_redemptions")
    op.drop_index("uq_invite_redemptions_redeemed_invite_code_id", table_name="invite_redemptions")
    op.create_index(
        "uq_invite_redemptions_redeemed_invite_code_id",
        "invite_redemptions",
        ["invite_code_id"],
        unique=True,
        postgresql_where=sa.text("status = 'redeemed'"),
        sqlite_where=sa.text("status = 'redeemed'"),
    )

    with op.batch_alter_table("invite_redemptions") as batch_op:
        batch_op.drop_index("ix_invite_redemptions_usage_mode_snapshot")
        for column_name in (
            "user_agent_hash",
            "client_ip_hash",
            "device_key_hash",
            "code_redemptions_count_after",
            "redemption_sequence",
            "usage_mode_snapshot",
        ):
            batch_op.drop_column(column_name)

    with op.batch_alter_table("invite_batches") as batch_op:
        batch_op.drop_index("ix_invite_batches_usage_mode")
        for column_name in (
            "multi_use_policy",
            "per_user_redemption_cap",
            "max_redemptions_per_code",
            "usage_mode",
        ):
            batch_op.drop_column(column_name)

    with op.batch_alter_table("invite_campaign_versions") as batch_op:
        for column_name in (
            "multi_use_policy",
            "child_per_user_redemption_cap",
            "child_max_redemptions",
            "child_usage_mode",
            "root_per_user_redemption_cap",
            "root_max_redemptions",
            "root_usage_mode",
        ):
            batch_op.drop_column(column_name)

    with op.batch_alter_table("invite_codes") as batch_op:
        batch_op.drop_index("ix_invite_codes_usage_mode")
        for column_name in (
            "multi_use_policy",
            "per_user_redemption_cap",
            "exhausted_at",
            "last_redeemed_at",
            "first_redeemed_at",
            "reversed_redemptions_count",
            "active_redemptions_count",
            "redeemed_count",
            "max_redemptions",
            "usage_mode",
        ):
            batch_op.drop_column(column_name)


def _json_type(bind: sa.Connection) -> sa.types.TypeEngine:
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_default(bind: sa.Connection, value: str) -> sa.TextClause:
    if bind.dialect.name == "postgresql":
        return sa.text(f"'{value}'::jsonb")
    return sa.text(f"'{value}'")


def _backfill_legacy_multi_use_columns(bind: sa.Connection) -> None:
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                """
                UPDATE invite_codes
                   SET max_redemptions = 1,
                       redeemed_count = CASE WHEN is_used THEN 1 ELSE 0 END,
                       active_redemptions_count = CASE WHEN is_used THEN 1 ELSE 0 END,
                       reversed_redemptions_count = 0,
                       first_redeemed_at = used_at,
                       last_redeemed_at = used_at,
                       exhausted_at = CASE WHEN is_used THEN used_at ELSE NULL END,
                       per_user_redemption_cap = 1,
                       multi_use_policy = '{}'::jsonb
                """
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE invite_campaign_versions
                   SET root_usage_mode = 'single_use',
                       root_max_redemptions = 1,
                       root_per_user_redemption_cap = 1,
                       child_usage_mode = 'single_use',
                       child_max_redemptions = 1,
                       child_per_user_redemption_cap = 1,
                       multi_use_policy = '{}'::jsonb
                """
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE invite_batches
                   SET usage_mode = 'single_use',
                       max_redemptions_per_code = 1,
                       per_user_redemption_cap = 1,
                       multi_use_policy = '{}'::jsonb
                """
            )
        )
    else:
        bind.execute(
            sa.text(
                """
                UPDATE invite_codes
                   SET max_redemptions = 1,
                       redeemed_count = CASE WHEN is_used THEN 1 ELSE 0 END,
                       active_redemptions_count = CASE WHEN is_used THEN 1 ELSE 0 END,
                       reversed_redemptions_count = 0,
                       first_redeemed_at = used_at,
                       last_redeemed_at = used_at,
                       exhausted_at = CASE WHEN is_used THEN used_at ELSE NULL END,
                       per_user_redemption_cap = 1,
                       multi_use_policy = '{}'
                """
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE invite_campaign_versions
                   SET root_usage_mode = 'single_use',
                       root_max_redemptions = 1,
                       root_per_user_redemption_cap = 1,
                       child_usage_mode = 'single_use',
                       child_max_redemptions = 1,
                       child_per_user_redemption_cap = 1,
                       multi_use_policy = '{}'
                """
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE invite_batches
                   SET usage_mode = 'single_use',
                       max_redemptions_per_code = 1,
                       per_user_redemption_cap = 1,
                       multi_use_policy = '{}'
                """
            )
        )
    bind.execute(
        sa.text(
            """
            UPDATE invite_redemptions
               SET usage_mode_snapshot = 'single_use',
                   redemption_sequence = CASE WHEN status = 'redeemed' THEN 1 ELSE NULL END,
                   code_redemptions_count_after = CASE WHEN status = 'redeemed' THEN 1 ELSE NULL END,
                   device_key_hash = NULL,
                   client_ip_hash = NULL,
                   user_agent_hash = NULL
            """
        )
    )


def _assert_safe_downgrade(bind: sa.Connection) -> None:
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                          FROM invite_codes
                         WHERE usage_mode = 'multi_use'
                            OR COALESCE(redeemed_count, 0) > 1
                            OR COALESCE(active_redemptions_count, 0) > 1
                            OR COALESCE(reversed_redemptions_count, 0) > 0
                    )
                    OR EXISTS (
                        SELECT 1
                          FROM invite_redemptions
                         WHERE usage_mode_snapshot = 'multi_use'
                            OR COALESCE(redemption_sequence, 1) > 1
                    )
                    OR EXISTS (
                        SELECT invite_code_id
                          FROM invite_redemptions
                         WHERE status = 'redeemed'
                         GROUP BY invite_code_id
                        HAVING COUNT(*) > 1
                    )
                    OR EXISTS (
                        SELECT 1
                          FROM invite_campaign_versions
                         WHERE root_usage_mode = 'multi_use'
                            OR child_usage_mode = 'multi_use'
                            OR COALESCE(root_max_redemptions, 1) <> 1
                            OR COALESCE(child_max_redemptions, 1) <> 1
                            OR COALESCE(root_per_user_redemption_cap, 1) <> 1
                            OR COALESCE(child_per_user_redemption_cap, 1) <> 1
                            OR COALESCE(multi_use_policy, '{}'::jsonb) <> '{}'::jsonb
                    )
                    OR EXISTS (
                        SELECT 1
                          FROM invite_batches
                         WHERE usage_mode = 'multi_use'
                            OR COALESCE(max_redemptions_per_code, 1) <> 1
                            OR COALESCE(per_user_redemption_cap, 1) <> 1
                            OR COALESCE(multi_use_policy, '{}'::jsonb) <> '{}'::jsonb
                    ) THEN
                        RAISE EXCEPTION USING MESSAGE =
                            'Cannot downgrade v7.5.1 multi-use invite schema while multi-use data exists';
                    END IF;
                END $$;
                """
            )
        )
        return
    unsafe = bind.execute(
        sa.text(
            """
            SELECT
                (SELECT COUNT(*) FROM invite_codes
                  WHERE usage_mode = 'multi_use'
                     OR COALESCE(redeemed_count, 0) > 1
                     OR COALESCE(active_redemptions_count, 0) > 1
                     OR COALESCE(reversed_redemptions_count, 0) > 0)
              + (SELECT COUNT(*) FROM invite_redemptions
                  WHERE usage_mode_snapshot = 'multi_use'
                     OR COALESCE(redemption_sequence, 1) > 1)
              + (SELECT COUNT(*) FROM (
                    SELECT invite_code_id
                      FROM invite_redemptions
                     WHERE status = 'redeemed'
                     GROUP BY invite_code_id
                    HAVING COUNT(*) > 1
                ) AS repeated_codes)
              + (SELECT COUNT(*) FROM invite_campaign_versions
                  WHERE root_usage_mode = 'multi_use'
                     OR child_usage_mode = 'multi_use'
                     OR COALESCE(root_max_redemptions, 1) <> 1
                     OR COALESCE(child_max_redemptions, 1) <> 1
                     OR COALESCE(root_per_user_redemption_cap, 1) <> 1
                     OR COALESCE(child_per_user_redemption_cap, 1) <> 1
                     OR COALESCE(multi_use_policy, '{}') <> '{}')
              + (SELECT COUNT(*) FROM invite_batches
                  WHERE usage_mode = 'multi_use'
                     OR COALESCE(max_redemptions_per_code, 1) <> 1
                     OR COALESCE(per_user_redemption_cap, 1) <> 1
                     OR COALESCE(multi_use_policy, '{}') <> '{}')
            """
        )
    ).scalar()
    if int(unsafe or 0) > 0:
        raise RuntimeError("Cannot downgrade v7.5.1 multi-use invite schema while multi-use redemption data exists")


def _create_constraints() -> None:
    op.create_check_constraint(
        "ck_invite_codes_usage_mode",
        "invite_codes",
        "usage_mode IN ('single_use','multi_use')",
    )
    op.create_check_constraint(
        "ck_invite_codes_max_redemptions_positive",
        "invite_codes",
        "max_redemptions IS NULL OR max_redemptions > 0",
    )
    op.create_check_constraint(
        "ck_invite_codes_redemption_counts_non_negative",
        "invite_codes",
        "redeemed_count >= 0 AND active_redemptions_count >= 0 AND reversed_redemptions_count >= 0",
    )
    op.create_check_constraint(
        "ck_invite_codes_per_user_cap_positive",
        "invite_codes",
        "per_user_redemption_cap >= 1",
    )
    op.create_check_constraint(
        "ck_invite_campaign_versions_root_usage_mode",
        "invite_campaign_versions",
        "root_usage_mode IN ('single_use','multi_use')",
    )
    op.create_check_constraint(
        "ck_invite_campaign_versions_child_usage_mode",
        "invite_campaign_versions",
        "child_usage_mode IN ('single_use','multi_use')",
    )
    op.create_check_constraint(
        "ck_invite_campaign_versions_max_redemptions_positive",
        "invite_campaign_versions",
        "(root_max_redemptions IS NULL OR root_max_redemptions > 0) "
        "AND (child_max_redemptions IS NULL OR child_max_redemptions > 0)",
    )
    op.create_check_constraint(
        "ck_invite_campaign_versions_per_user_caps_positive",
        "invite_campaign_versions",
        "root_per_user_redemption_cap >= 1 AND child_per_user_redemption_cap >= 1",
    )
    op.create_check_constraint(
        "ck_invite_batches_usage_mode",
        "invite_batches",
        "usage_mode IN ('single_use','multi_use')",
    )
    op.create_check_constraint(
        "ck_invite_batches_max_redemptions_positive",
        "invite_batches",
        "max_redemptions_per_code IS NULL OR max_redemptions_per_code > 0",
    )
    op.create_check_constraint(
        "ck_invite_batches_per_user_cap_positive",
        "invite_batches",
        "per_user_redemption_cap >= 1",
    )
    op.create_check_constraint(
        "ck_invite_redemptions_usage_mode_snapshot",
        "invite_redemptions",
        "usage_mode_snapshot IN ('single_use','multi_use')",
    )


def _drop_constraints() -> None:
    for table_name, constraint_names in (
        (
            "invite_redemptions",
            ("ck_invite_redemptions_usage_mode_snapshot",),
        ),
        (
            "invite_batches",
            (
                "ck_invite_batches_per_user_cap_positive",
                "ck_invite_batches_max_redemptions_positive",
                "ck_invite_batches_usage_mode",
            ),
        ),
        (
            "invite_campaign_versions",
            (
                "ck_invite_campaign_versions_per_user_caps_positive",
                "ck_invite_campaign_versions_max_redemptions_positive",
                "ck_invite_campaign_versions_child_usage_mode",
                "ck_invite_campaign_versions_root_usage_mode",
            ),
        ),
        (
            "invite_codes",
            (
                "ck_invite_codes_per_user_cap_positive",
                "ck_invite_codes_redemption_counts_non_negative",
                "ck_invite_codes_max_redemptions_positive",
                "ck_invite_codes_usage_mode",
            ),
        ),
    ):
        for constraint_name in constraint_names:
            op.drop_constraint(constraint_name, table_name, type_="check")
