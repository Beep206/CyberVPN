"""Partner workspace core organization, settings, and legal acceptance tables."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260420_phase10_partner_workspace_core"
down_revision = "20260420_phase9_partner_application_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partner_workspace_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("operating_regions", sa.Text(), nullable=True),
        sa.Column("languages", sa.Text(), nullable=True),
        sa.Column("contact_name", sa.String(length=120), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("support_contact", sa.String(length=255), nullable=True),
        sa.Column("technical_contact", sa.String(length=255), nullable=True),
        sa.Column("finance_contact", sa.String(length=255), nullable=True),
        sa.Column("business_description", sa.Text(), nullable=True),
        sa.Column("acquisition_channels", sa.Text(), nullable=True),
        sa.Column("preferred_currency", sa.String(length=10), nullable=False, server_default="USD"),
        sa.Column("require_mfa_for_workspace", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("prefer_passkeys", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reviewed_active_sessions", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("partner_account_id"),
    )
    op.create_index(
        "ix_partner_workspace_profiles_partner_account_id",
        "partner_workspace_profiles",
        ["partner_account_id"],
    )

    op.create_table(
        "partner_workspace_legal_acceptances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_account_id", sa.Uuid(), nullable=False),
        sa.Column("document_kind", sa.String(length=40), nullable=False),
        sa.Column("document_version", sa.String(length=40), nullable=False),
        sa.Column("accepted_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["accepted_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "partner_account_id",
            "document_kind",
            "document_version",
            name="uq_partner_workspace_legal_acceptance_document_version",
        ),
    )
    op.create_index(
        "ix_partner_workspace_legal_acceptances_partner_account_id",
        "partner_workspace_legal_acceptances",
        ["partner_account_id"],
    )
    op.create_index(
        "ix_partner_workspace_legal_acceptances_document_kind",
        "partner_workspace_legal_acceptances",
        ["document_kind"],
    )
    op.create_index(
        "ix_partner_workspace_legal_acceptances_accepted_by_admin_user_id",
        "partner_workspace_legal_acceptances",
        ["accepted_by_admin_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_partner_workspace_legal_acceptances_accepted_by_admin_user_id",
        table_name="partner_workspace_legal_acceptances",
    )
    op.drop_index(
        "ix_partner_workspace_legal_acceptances_document_kind",
        table_name="partner_workspace_legal_acceptances",
    )
    op.drop_index(
        "ix_partner_workspace_legal_acceptances_partner_account_id",
        table_name="partner_workspace_legal_acceptances",
    )
    op.drop_table("partner_workspace_legal_acceptances")

    op.drop_index(
        "ix_partner_workspace_profiles_partner_account_id",
        table_name="partner_workspace_profiles",
    )
    op.drop_table("partner_workspace_profiles")
