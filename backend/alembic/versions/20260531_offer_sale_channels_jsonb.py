"""Convert offer sale channels to JSONB.

Revision ID: 20260531_offer_channels_jsonb
Revises: 20260530_s1_provisioning_retry, 20260531_redact_webhook_logs
Create Date: 2026-05-31 22:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260531_offer_channels_jsonb"
down_revision: str | Sequence[str] | None = (
    "20260530_s1_provisioning_retry",
    "20260531_redact_webhook_logs",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "offer_versions",
        "sale_channels",
        existing_type=sa.JSON(),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=False,
        postgresql_using="sale_channels::jsonb",
    )


def downgrade() -> None:
    op.alter_column(
        "offer_versions",
        "sale_channels",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=sa.JSON(),
        existing_nullable=False,
        postgresql_using="sale_channels::json",
    )
