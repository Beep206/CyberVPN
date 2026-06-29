"""Add lifetime invite campaign fields for Growth Codes v7.2.

Revision ID: 20260629_invite_lifetime_v72
Revises: 20260628_invite_v7
Create Date: 2026-06-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260629_invite_lifetime_v72"
down_revision: str | Sequence[str] | None = "20260628_invite_v7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    op.add_column(
        "invite_campaign_versions",
        sa.Column("grant_duration_mode", sa.String(length=20), nullable=False, server_default="fixed_days"),
    )
    op.add_column(
        "invite_campaign_versions",
        sa.Column("child_grant_duration_mode", sa.String(length=20), nullable=False, server_default="fixed_days"),
    )
    op.add_column("invite_campaign_versions", sa.Column("grant_device_limit_override", sa.Integer(), nullable=True))
    op.add_column(
        "invite_campaign_versions",
        sa.Column("child_grant_device_limit_override", sa.Integer(), nullable=True),
    )
    op.add_column(
        "invite_campaign_versions",
        sa.Column("root_invite_expiry_mode", sa.String(length=20), nullable=False, server_default="relative"),
    )
    op.add_column("invite_campaign_versions", sa.Column("root_invite_expiry_days", sa.Integer(), nullable=True))
    op.add_column(
        "invite_campaign_versions",
        sa.Column("root_invite_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "invite_campaign_versions",
        sa.Column("child_invite_expiry_mode", sa.String(length=20), nullable=False, server_default="relative"),
    )
    op.add_column(
        "invite_campaign_versions",
        sa.Column("child_invite_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "invite_codes",
        sa.Column("grant_duration_mode", sa.String(length=20), nullable=False, server_default="fixed_days"),
    )
    op.add_column(
        "invite_codes",
        sa.Column("child_grant_duration_mode", sa.String(length=20), nullable=False, server_default="fixed_days"),
    )
    op.add_column("invite_codes", sa.Column("grant_device_limit_override", sa.Integer(), nullable=True))
    op.add_column("invite_codes", sa.Column("child_grant_device_limit_override", sa.Integer(), nullable=True))
    op.add_column(
        "invite_codes",
        sa.Column("child_invite_expiry_mode", sa.String(length=20), nullable=False, server_default="relative"),
    )

    op.add_column(
        "invite_batches",
        sa.Column("grant_duration_mode", sa.String(length=20), nullable=False, server_default="fixed_days"),
    )
    op.add_column(
        "invite_batches",
        sa.Column("child_grant_duration_mode", sa.String(length=20), nullable=False, server_default="fixed_days"),
    )
    op.add_column("invite_batches", sa.Column("grant_device_limit_override", sa.Integer(), nullable=True))
    op.add_column("invite_batches", sa.Column("child_grant_device_limit_override", sa.Integer(), nullable=True))
    op.add_column(
        "invite_batches",
        sa.Column("child_invite_expiry_mode", sa.String(length=20), nullable=False, server_default="relative"),
    )
    op.add_column(
        "invite_tree_closure",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
    )
    op.add_column("invite_tree_closure", sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE invite_campaign_versions SET root_invite_expiry_days = 30 WHERE root_invite_expiry_days IS NULL")
    op.execute(
        "UPDATE invite_batches SET expiry_mode = 'none', expiry_days = NULL "
        "WHERE expires_at IS NULL AND expiry_mode <> 'none'"
    )
    op.execute(
        "UPDATE invite_batches SET expiry_mode = 'absolute' "
        "WHERE expires_at IS NOT NULL AND expiry_days IS NULL AND expiry_mode <> 'absolute'"
    )
    op.execute(
        "UPDATE invite_batches SET expiry_mode = 'relative' "
        "WHERE expires_at IS NOT NULL AND expiry_days IS NOT NULL AND expiry_mode <> 'relative'"
    )

    if is_sqlite:
        with op.batch_alter_table("invite_batches", recreate="always") as batch_op:
            batch_op.drop_constraint("ck_invite_batches_friend_days_positive", type_="check")
            batch_op.create_check_constraint("ck_invite_batches_friend_days_non_negative", "friend_days >= 0")
    else:
        op.drop_constraint("ck_invite_batches_friend_days_positive", "invite_batches", type_="check")
        op.create_check_constraint(
            "ck_invite_batches_friend_days_non_negative",
            "invite_batches",
            "friend_days >= 0",
        )
        _create_constraints()


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        irreversible_rows = bind.execute(
            sa.text(
                """
                SELECT
                    (SELECT COUNT(*) FROM invite_campaign_versions
                     WHERE grant_duration_mode = 'lifetime'
                        OR child_grant_duration_mode = 'lifetime'
                        OR root_invite_expiry_mode = 'none'
                        OR child_invite_expiry_mode = 'none')
                  + (SELECT COUNT(*) FROM invite_codes
                     WHERE grant_duration_mode = 'lifetime'
                        OR child_grant_duration_mode = 'lifetime'
                        OR child_invite_expiry_mode = 'none')
                  + (SELECT COUNT(*) FROM invite_batches
                     WHERE grant_duration_mode = 'lifetime'
                        OR child_grant_duration_mode = 'lifetime'
                        OR child_invite_expiry_mode = 'none'
                        OR expiry_mode = 'none'
                        OR friend_days <= 0)
                """
            )
        ).scalar()
        if int(irreversible_rows or 0) > 0:
            raise RuntimeError("Cannot downgrade v7.2 lifetime invite schema while lifetime/no-expiry data exists")
    else:
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM invite_campaign_versions
                    WHERE grant_duration_mode = 'lifetime'
                       OR child_grant_duration_mode = 'lifetime'
                       OR root_invite_expiry_mode = 'none'
                       OR child_invite_expiry_mode = 'none'
                )
                OR EXISTS (
                    SELECT 1 FROM invite_codes
                    WHERE grant_duration_mode = 'lifetime'
                       OR child_grant_duration_mode = 'lifetime'
                       OR child_invite_expiry_mode = 'none'
                )
                OR EXISTS (
                    SELECT 1 FROM invite_batches
                    WHERE grant_duration_mode = 'lifetime'
                       OR child_grant_duration_mode = 'lifetime'
                       OR child_invite_expiry_mode = 'none'
                       OR expiry_mode = 'none'
                       OR friend_days <= 0
                ) THEN
                    RAISE EXCEPTION 'Cannot downgrade v7.2 lifetime invite schema while lifetime/no-expiry data exists';
                END IF;
            END $$;
            """
        )

    op.execute("UPDATE invite_batches SET friend_days = 1 WHERE friend_days <= 0")
    if is_sqlite:
        with op.batch_alter_table("invite_batches", recreate="always") as batch_op:
            batch_op.drop_constraint("ck_invite_batches_friend_days_non_negative", type_="check")
            batch_op.create_check_constraint("ck_invite_batches_friend_days_positive", "friend_days > 0")
    else:
        _drop_constraints()
        op.drop_constraint("ck_invite_batches_friend_days_non_negative", "invite_batches", type_="check")
        op.create_check_constraint("ck_invite_batches_friend_days_positive", "invite_batches", "friend_days > 0")

    for table_name, column_names in (
        (
            "invite_batches",
            (
                "child_invite_expiry_mode",
                "child_grant_device_limit_override",
                "grant_device_limit_override",
                "child_grant_duration_mode",
                "grant_duration_mode",
            ),
        ),
        (
            "invite_codes",
            (
                "child_invite_expiry_mode",
                "child_grant_device_limit_override",
                "grant_device_limit_override",
                "child_grant_duration_mode",
                "grant_duration_mode",
            ),
        ),
        (
            "invite_campaign_versions",
            (
                "child_invite_expires_at",
                "child_invite_expiry_mode",
                "root_invite_expires_at",
                "root_invite_expiry_days",
                "root_invite_expiry_mode",
                "child_grant_device_limit_override",
                "grant_device_limit_override",
                "child_grant_duration_mode",
                "grant_duration_mode",
            ),
        ),
        (
            "invite_tree_closure",
            (
                "reversed_at",
                "status",
            ),
        ),
    ):
        for column_name in column_names:
            op.drop_column(table_name, column_name)


def _create_constraints() -> None:
    op.create_check_constraint(
        "ck_invite_campaign_versions_grant_duration_mode",
        "invite_campaign_versions",
        "grant_duration_mode IN ('fixed_days','lifetime')",
    )
    op.create_check_constraint(
        "ck_invite_campaign_versions_child_grant_duration_mode",
        "invite_campaign_versions",
        "child_grant_duration_mode IN ('fixed_days','lifetime')",
    )
    op.create_check_constraint(
        "ck_invite_campaign_versions_root_expiry_mode",
        "invite_campaign_versions",
        "root_invite_expiry_mode IN ('relative','absolute','none')",
    )
    op.create_check_constraint(
        "ck_invite_campaign_versions_child_expiry_mode",
        "invite_campaign_versions",
        "child_invite_expiry_mode IN ('relative','absolute','none')",
    )
    op.create_check_constraint(
        "ck_invite_campaign_versions_device_override_positive",
        "invite_campaign_versions",
        "(grant_device_limit_override IS NULL OR grant_device_limit_override > 0) "
        "AND (child_grant_device_limit_override IS NULL OR child_grant_device_limit_override > 0)",
    )
    op.create_check_constraint(
        "ck_invite_codes_grant_duration_mode",
        "invite_codes",
        "grant_duration_mode IN ('fixed_days','lifetime')",
    )
    op.create_check_constraint(
        "ck_invite_codes_child_grant_duration_mode",
        "invite_codes",
        "child_grant_duration_mode IN ('fixed_days','lifetime')",
    )
    op.create_check_constraint(
        "ck_invite_codes_child_expiry_mode",
        "invite_codes",
        "child_invite_expiry_mode IN ('relative','absolute','none')",
    )
    op.create_check_constraint(
        "ck_invite_codes_device_override_positive",
        "invite_codes",
        "(grant_device_limit_override IS NULL OR grant_device_limit_override > 0) "
        "AND (child_grant_device_limit_override IS NULL OR child_grant_device_limit_override > 0)",
    )
    op.create_check_constraint(
        "ck_invite_batches_grant_duration_mode",
        "invite_batches",
        "grant_duration_mode IN ('fixed_days','lifetime')",
    )
    op.create_check_constraint(
        "ck_invite_batches_child_grant_duration_mode",
        "invite_batches",
        "child_grant_duration_mode IN ('fixed_days','lifetime')",
    )
    op.create_check_constraint(
        "ck_invite_batches_child_expiry_mode",
        "invite_batches",
        "child_invite_expiry_mode IN ('relative','absolute','none')",
    )
    op.create_check_constraint(
        "ck_invite_batches_device_override_positive",
        "invite_batches",
        "(grant_device_limit_override IS NULL OR grant_device_limit_override > 0) "
        "AND (child_grant_device_limit_override IS NULL OR child_grant_device_limit_override > 0)",
    )


def _drop_constraints() -> None:
    for table_name, constraint_names in (
        (
            "invite_batches",
            (
                "ck_invite_batches_device_override_positive",
                "ck_invite_batches_child_expiry_mode",
                "ck_invite_batches_child_grant_duration_mode",
                "ck_invite_batches_grant_duration_mode",
            ),
        ),
        (
            "invite_codes",
            (
                "ck_invite_codes_device_override_positive",
                "ck_invite_codes_child_expiry_mode",
                "ck_invite_codes_child_grant_duration_mode",
                "ck_invite_codes_grant_duration_mode",
            ),
        ),
        (
            "invite_campaign_versions",
            (
                "ck_invite_campaign_versions_device_override_positive",
                "ck_invite_campaign_versions_child_expiry_mode",
                "ck_invite_campaign_versions_root_expiry_mode",
                "ck_invite_campaign_versions_child_grant_duration_mode",
                "ck_invite_campaign_versions_grant_duration_mode",
            ),
        ),
    ):
        for constraint_name in constraint_names:
            op.drop_constraint(constraint_name, table_name, type_="check")
