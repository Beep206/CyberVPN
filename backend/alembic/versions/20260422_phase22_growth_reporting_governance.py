"""phase22_growth_reporting_governance

Revision ID: 20260422_phase22_growth_reporting_governance
Revises: 20260422_phase21_growth_reporting_distribution
Create Date: 2026-04-22 23:58:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260422_phase22_growth_reporting_governance"
down_revision = "20260422_phase21_growth_reporting_distribution"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if inspector.has_table("growth_reporting_subscriptions"):
        column_names = _column_names("growth_reporting_subscriptions")
        if "template_key" not in column_names:
            op.add_column(
                "growth_reporting_subscriptions",
                sa.Column("template_key", sa.String(length=48), nullable=False, server_default="cross_function_exec"),
            )
        if "template_locale" not in column_names:
            op.add_column(
                "growth_reporting_subscriptions",
                sa.Column("template_locale", sa.String(length=16), nullable=False, server_default="en-EN"),
            )
        if "email_subject_prefix" not in column_names:
            op.add_column(
                "growth_reporting_subscriptions",
                sa.Column("email_subject_prefix", sa.String(length=120), nullable=True),
            )
        if "title_override" not in column_names:
            op.add_column(
                "growth_reporting_subscriptions",
                sa.Column("title_override", sa.String(length=160), nullable=True),
            )
        if "recipient_domain_policy" not in column_names:
            op.add_column(
                "growth_reporting_subscriptions",
                sa.Column("recipient_domain_policy", sa.String(length=24), nullable=False, server_default="allow_any"),
            )
        if "allowed_recipient_domains" not in column_names:
            op.add_column(
                "growth_reporting_subscriptions",
                sa.Column("allowed_recipient_domains", sa.JSON(), nullable=False, server_default="[]"),
            )
        if "suppressed_until" not in column_names:
            op.add_column(
                "growth_reporting_subscriptions",
                sa.Column("suppressed_until", sa.DateTime(timezone=True), nullable=True),
            )
        if "suppression_reason_code" not in column_names:
            op.add_column(
                "growth_reporting_subscriptions",
                sa.Column("suppression_reason_code", sa.String(length=80), nullable=True),
            )
        subscription_indexes = {index["name"] for index in inspector.get_indexes("growth_reporting_subscriptions")}
        if "ix_growth_reporting_subscriptions_suppressed_until" not in subscription_indexes:
            op.create_index(
                "ix_growth_reporting_subscriptions_suppressed_until",
                "growth_reporting_subscriptions",
                ["suppressed_until"],
            )

    if inspector.has_table("growth_reporting_deliveries"):
        column_names = _column_names("growth_reporting_deliveries")
        if "template_key" not in column_names:
            op.add_column(
                "growth_reporting_deliveries",
                sa.Column("template_key", sa.String(length=48), nullable=False, server_default="cross_function_exec"),
            )
        if "template_locale" not in column_names:
            op.add_column(
                "growth_reporting_deliveries",
                sa.Column("template_locale", sa.String(length=16), nullable=False, server_default="en-EN"),
            )
        if "subject_line" not in column_names:
            op.add_column(
                "growth_reporting_deliveries",
                sa.Column("subject_line", sa.String(length=255), nullable=False, server_default="Growth reporting digest"),
            )
        if "title_line" not in column_names:
            op.add_column(
                "growth_reporting_deliveries",
                sa.Column("title_line", sa.String(length=255), nullable=False, server_default="Growth reporting digest"),
            )
        if "recipient_domain_policy" not in column_names:
            op.add_column(
                "growth_reporting_deliveries",
                sa.Column("recipient_domain_policy", sa.String(length=24), nullable=False, server_default="allow_any"),
            )
        if "allowed_recipient_domains" not in column_names:
            op.add_column(
                "growth_reporting_deliveries",
                sa.Column("allowed_recipient_domains", sa.JSON(), nullable=False, server_default="[]"),
            )
        delivery_indexes = {index["name"] for index in inspector.get_indexes("growth_reporting_deliveries")}
        if "ix_growth_reporting_deliveries_template_key" not in delivery_indexes:
            op.create_index(
                "ix_growth_reporting_deliveries_template_key",
                "growth_reporting_deliveries",
                ["template_key"],
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if inspector.has_table("growth_reporting_deliveries"):
        delivery_indexes = {index["name"] for index in inspector.get_indexes("growth_reporting_deliveries")}
        if "ix_growth_reporting_deliveries_template_key" in delivery_indexes:
            op.drop_index("ix_growth_reporting_deliveries_template_key", table_name="growth_reporting_deliveries")
        for column_name in (
            "allowed_recipient_domains",
            "recipient_domain_policy",
            "title_line",
            "subject_line",
            "template_locale",
            "template_key",
        ):
            if column_name in _column_names("growth_reporting_deliveries"):
                op.drop_column("growth_reporting_deliveries", column_name)

    if inspector.has_table("growth_reporting_subscriptions"):
        subscription_indexes = {index["name"] for index in inspector.get_indexes("growth_reporting_subscriptions")}
        if "ix_growth_reporting_subscriptions_suppressed_until" in subscription_indexes:
            op.drop_index(
                "ix_growth_reporting_subscriptions_suppressed_until",
                table_name="growth_reporting_subscriptions",
            )
        for column_name in (
            "suppression_reason_code",
            "suppressed_until",
            "allowed_recipient_domains",
            "recipient_domain_policy",
            "title_override",
            "email_subject_prefix",
            "template_locale",
            "template_key",
        ):
            if column_name in _column_names("growth_reporting_subscriptions"):
                op.drop_column("growth_reporting_subscriptions", column_name)
