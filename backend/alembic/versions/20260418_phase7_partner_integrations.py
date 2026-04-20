"""Phase 7 partner integrations and reporting token foundation."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260418_phase7_partner_integrations"
down_revision = "20260418_phase7_event_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partner_integration_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("credential_kind", sa.String(length=40), nullable=False),
        sa.Column(
            "credential_status",
            sa.String(length=30),
            nullable=False,
            server_default="pending_rotation",
        ),
        sa.Column("credential_hash", sa.String(length=128), nullable=False),
        sa.Column("token_hint", sa.String(length=60), nullable=False),
        sa.Column("scope_key", sa.String(length=80), nullable=False),
        sa.Column("destination_ref", sa.String(length=255), nullable=True),
        sa.Column("credential_metadata", sa.JSON(), nullable=False),
        sa.Column("created_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("rotated_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("last_rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rotated_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "partner_account_id",
            "credential_kind",
            name="uq_partner_integration_credentials_partner_kind",
        ),
    )
    op.create_index(
        "ix_partner_integration_credentials_partner_account_id",
        "partner_integration_credentials",
        ["partner_account_id"],
    )
    op.create_index(
        "ix_partner_integration_credentials_credential_kind",
        "partner_integration_credentials",
        ["credential_kind"],
    )
    op.create_index(
        "ix_partner_integration_credentials_credential_status",
        "partner_integration_credentials",
        ["credential_status"],
    )
    op.create_index(
        "ix_partner_integration_credentials_credential_hash",
        "partner_integration_credentials",
        ["credential_hash"],
    )
    op.create_index(
        "ix_partner_integration_credentials_created_by_admin_user_id",
        "partner_integration_credentials",
        ["created_by_admin_user_id"],
    )
    op.create_index(
        "ix_partner_integration_credentials_rotated_by_admin_user_id",
        "partner_integration_credentials",
        ["rotated_by_admin_user_id"],
    )
    op.create_index(
        "ix_partner_integration_credentials_last_rotated_at",
        "partner_integration_credentials",
        ["last_rotated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_partner_integration_credentials_last_rotated_at",
        table_name="partner_integration_credentials",
    )
    op.drop_index(
        "ix_partner_integration_credentials_rotated_by_admin_user_id",
        table_name="partner_integration_credentials",
    )
    op.drop_index(
        "ix_partner_integration_credentials_created_by_admin_user_id",
        table_name="partner_integration_credentials",
    )
    op.drop_index(
        "ix_partner_integration_credentials_credential_hash",
        table_name="partner_integration_credentials",
    )
    op.drop_index(
        "ix_partner_integration_credentials_credential_status",
        table_name="partner_integration_credentials",
    )
    op.drop_index(
        "ix_partner_integration_credentials_credential_kind",
        table_name="partner_integration_credentials",
    )
    op.drop_index(
        "ix_partner_integration_credentials_partner_account_id",
        table_name="partner_integration_credentials",
    )
    op.drop_table("partner_integration_credentials")
