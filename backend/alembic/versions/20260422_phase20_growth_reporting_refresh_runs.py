"""phase20_growth_reporting_refresh_runs

Revision ID: 20260422_p20_growth_refresh
Revises: 20260422_p19_growth_rollups
Create Date: 2026-04-22 22:10:00.000000
"""


import sqlalchemy as sa

from alembic import op

revision = "20260422_p20_growth_refresh"
down_revision = "20260422_p19_growth_rollups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "growth_reporting_refresh_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trigger_kind", sa.String(length=20), nullable=False),
        sa.Column("refresh_status", sa.String(length=20), nullable=False),
        sa.Column("requested_window_days", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.Date(), nullable=False),
        sa.Column("window_end", sa.Date(), nullable=False),
        sa.Column("latest_rollup_date", sa.Date(), nullable=True),
        sa.Column("rows_written", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("families_updated", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_growth_reporting_refresh_runs_trigger_kind",
        "growth_reporting_refresh_runs",
        ["trigger_kind"],
    )
    op.create_index(
        "ix_growth_reporting_refresh_runs_refresh_status",
        "growth_reporting_refresh_runs",
        ["refresh_status"],
    )
    op.create_index(
        "ix_growth_reporting_refresh_runs_window_start",
        "growth_reporting_refresh_runs",
        ["window_start"],
    )
    op.create_index(
        "ix_growth_reporting_refresh_runs_window_end",
        "growth_reporting_refresh_runs",
        ["window_end"],
    )
    op.create_index(
        "ix_growth_reporting_refresh_runs_refreshed_at",
        "growth_reporting_refresh_runs",
        ["refreshed_at"],
    )
    op.create_index(
        "ix_growth_reporting_refresh_runs_created_at",
        "growth_reporting_refresh_runs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_growth_reporting_refresh_runs_created_at", table_name="growth_reporting_refresh_runs")
    op.drop_index("ix_growth_reporting_refresh_runs_refreshed_at", table_name="growth_reporting_refresh_runs")
    op.drop_index("ix_growth_reporting_refresh_runs_window_end", table_name="growth_reporting_refresh_runs")
    op.drop_index("ix_growth_reporting_refresh_runs_window_start", table_name="growth_reporting_refresh_runs")
    op.drop_index("ix_growth_reporting_refresh_runs_refresh_status", table_name="growth_reporting_refresh_runs")
    op.drop_index("ix_growth_reporting_refresh_runs_trigger_kind", table_name="growth_reporting_refresh_runs")
    op.drop_table("growth_reporting_refresh_runs")
