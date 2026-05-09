"""Persisted daily rollups for customer growth reporting."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260422_p19_growth_rollups"
down_revision = "20260422_p18_cust_notif_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "growth_reporting_daily_rollups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("report_family", sa.String(length=24), nullable=False),
        sa.Column("metric_key", sa.String(length=80), nullable=False),
        sa.Column("metric_unit", sa.String(length=20), nullable=False, server_default="count"),
        sa.Column("dimension_key", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("dimension_value", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("metric_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default=""),
        sa.Column("source_watermark_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "report_date",
            "report_family",
            "metric_key",
            "dimension_key",
            "dimension_value",
            "currency_code",
            name="uq_growth_reporting_daily_rollups_metric",
        ),
    )
    op.create_index(
        "ix_growth_reporting_daily_rollups_report_date",
        "growth_reporting_daily_rollups",
        ["report_date"],
    )
    op.create_index(
        "ix_growth_reporting_daily_rollups_report_family",
        "growth_reporting_daily_rollups",
        ["report_family"],
    )
    op.create_index(
        "ix_growth_reporting_daily_rollups_metric_key",
        "growth_reporting_daily_rollups",
        ["metric_key"],
    )
    op.create_index(
        "ix_growth_reporting_daily_rollups_source_watermark_at",
        "growth_reporting_daily_rollups",
        ["source_watermark_at"],
    )
    op.create_index(
        "ix_growth_reporting_daily_rollups_refreshed_at",
        "growth_reporting_daily_rollups",
        ["refreshed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_growth_reporting_daily_rollups_refreshed_at", table_name="growth_reporting_daily_rollups")
    op.drop_index(
        "ix_growth_reporting_daily_rollups_source_watermark_at",
        table_name="growth_reporting_daily_rollups",
    )
    op.drop_index("ix_growth_reporting_daily_rollups_metric_key", table_name="growth_reporting_daily_rollups")
    op.drop_index(
        "ix_growth_reporting_daily_rollups_report_family",
        table_name="growth_reporting_daily_rollups",
    )
    op.drop_index("ix_growth_reporting_daily_rollups_report_date", table_name="growth_reporting_daily_rollups")
    op.drop_table("growth_reporting_daily_rollups")
