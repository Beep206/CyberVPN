"""Add audit provenance columns to user_devices.

Revision ID: 20260609_user_devices_audit
Revises: 20260609_session_device_refresh
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260609_user_devices_audit"
down_revision: str | Sequence[str] | None = "20260609_session_device_refresh"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_devices", sa.Column("first_user_agent", sa.String(length=512), nullable=True))
    op.add_column("user_devices", sa.Column("last_user_agent", sa.String(length=512), nullable=True))
    op.add_column("user_devices", sa.Column("last_ip_address", sa.String(length=45), nullable=True))
    op.add_column("user_devices", sa.Column("last_ip_source", sa.String(length=32), nullable=True))
    op.add_column("user_devices", sa.Column("last_proxy_peer", sa.String(length=45), nullable=True))


def downgrade() -> None:
    op.drop_column("user_devices", "last_proxy_peer")
    op.drop_column("user_devices", "last_ip_source")
    op.drop_column("user_devices", "last_ip_address")
    op.drop_column("user_devices", "last_user_agent")
    op.drop_column("user_devices", "first_user_agent")
