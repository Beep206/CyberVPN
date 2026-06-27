"""Add Growth reservation capacity context.

Revision ID: 20260626_growth_res_capacity
Revises: 20260626_growth_reversals
Create Date: 2026-06-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260626_growth_res_capacity"
down_revision: str | Sequence[str] | None = "20260626_growth_reversals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    json_type = postgresql.JSONB() if bind.dialect.name == "postgresql" else sa.JSON()
    json_default = sa.text("'{}'::jsonb") if bind.dialect.name == "postgresql" else sa.text("'{}'")

    with op.batch_alter_table("growth_code_reservations") as batch_op:
        batch_op.add_column(sa.Column("risk_subject_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("risk_decision_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("device_key_hash", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("velocity_bucket", sa.String(length=160), nullable=True))
        batch_op.add_column(
            sa.Column("capacity_context", json_type, nullable=False, server_default=json_default),
        )
        batch_op.create_foreign_key(
            "fk_growth_code_reservations_risk_subject_id_risk_subjects",
            "risk_subjects",
            ["risk_subject_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_growth_code_reservations_risk_subject_id", ["risk_subject_id"])
        batch_op.create_index("ix_growth_code_reservations_risk_decision_id", ["risk_decision_id"])
        batch_op.create_index("ix_growth_code_reservations_device_key_hash", ["device_key_hash"])
        batch_op.create_index("ix_growth_code_reservations_velocity_bucket", ["velocity_bucket"])

    op.create_table(
        "growth_code_capacity_counters",
        sa.Column("growth_code_id", sa.Uuid(), nullable=False),
        sa.Column("capacity_dimension", sa.String(length=30), nullable=False),
        sa.Column("capacity_key_hash", sa.String(length=128), nullable=False),
        sa.Column("reserved_uses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_uses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "capacity_dimension IN ('risk_subject', 'device', 'velocity')",
            name="ck_growth_code_capacity_counters_dimension",
        ),
        sa.CheckConstraint("reserved_uses >= 0", name="ck_growth_code_capacity_counters_reserved_non_negative"),
        sa.CheckConstraint("consumed_uses >= 0", name="ck_growth_code_capacity_counters_consumed_non_negative"),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "growth_code_id",
            "capacity_dimension",
            "capacity_key_hash",
            name="pk_growth_code_capacity_counters",
        ),
    )
    op.create_index(
        "ix_growth_code_capacity_counters_dimension_key",
        "growth_code_capacity_counters",
        ["capacity_dimension", "capacity_key_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_growth_code_capacity_counters_dimension_key", table_name="growth_code_capacity_counters")
    op.drop_table("growth_code_capacity_counters")

    with op.batch_alter_table("growth_code_reservations") as batch_op:
        batch_op.drop_index("ix_growth_code_reservations_velocity_bucket")
        batch_op.drop_index("ix_growth_code_reservations_device_key_hash")
        batch_op.drop_index("ix_growth_code_reservations_risk_decision_id")
        batch_op.drop_index("ix_growth_code_reservations_risk_subject_id")
        batch_op.drop_constraint(
            "fk_growth_code_reservations_risk_subject_id_risk_subjects",
            type_="foreignkey",
        )
        batch_op.drop_column("capacity_context")
        batch_op.drop_column("velocity_bucket")
        batch_op.drop_column("device_key_hash")
        batch_op.drop_column("risk_decision_id")
        batch_op.drop_column("risk_subject_id")
