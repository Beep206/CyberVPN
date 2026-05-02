"""phase13 growth code quote reservations

Revision ID: 20260421_phase13_growth_code_quote_reservations
Revises: 20260421_phase12_growth_codes_backbone
Create Date: 2026-04-21 11:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260421_phase13_growth_code_quote_reservations"
down_revision = "20260421_phase12_growth_codes_backbone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("growth_code_reservations") as batch_op:
        batch_op.add_column(sa.Column("quote_session_id", sa.Uuid(), nullable=True))
        batch_op.create_index(
            "ix_growth_code_reservations_quote_session_id",
            ["quote_session_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_growth_code_reservations_quote_session_id_quote_sessions",
            "quote_sessions",
            ["quote_session_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("growth_code_reservations") as batch_op:
        batch_op.drop_constraint(
            "fk_growth_code_reservations_quote_session_id_quote_sessions",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_growth_code_reservations_quote_session_id")
        batch_op.drop_column("quote_session_id")
