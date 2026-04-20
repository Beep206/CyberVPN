"""Add policy version, legal document, and acceptance evidence foundations.

Revision ID: 20260417_phase1_policy_versions_and_legal_docs
Revises: 20260417_phase1_offers_pricebooks
Create Date: 2026-04-18 00:35:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260417_phase1_policy_versions_and_legal_docs"
down_revision: str | None = "20260417_phase1_offers_pricebooks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_family", sa.String(length=50), nullable=False),
        sa.Column("policy_key", sa.String(length=80), nullable=False),
        sa.Column("subject_type", sa.String(length=40), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("approval_state", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("version_status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_admin_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_admin_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("supersedes_policy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["approved_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supersedes_policy_version_id"], ["policy_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_family",
            "policy_key",
            "version_number",
            name="uq_policy_versions_family_key_version",
        ),
    )
    op.create_index(op.f("ix_policy_versions_policy_family"), "policy_versions", ["policy_family"], unique=False)
    op.create_index(op.f("ix_policy_versions_policy_key"), "policy_versions", ["policy_key"], unique=False)
    op.create_index(op.f("ix_policy_versions_subject_type"), "policy_versions", ["subject_type"], unique=False)
    op.create_index(op.f("ix_policy_versions_subject_id"), "policy_versions", ["subject_id"], unique=False)
    op.create_index(
        op.f("ix_policy_versions_approval_state"),
        "policy_versions",
        ["approval_state"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_versions_version_status"),
        "policy_versions",
        ["version_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_versions_effective_from"),
        "policy_versions",
        ["effective_from"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_versions_created_by_admin_user_id"),
        "policy_versions",
        ["created_by_admin_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_versions_approved_by_admin_user_id"),
        "policy_versions",
        ["approved_by_admin_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_versions_supersedes_policy_version_id"),
        "policy_versions",
        ["supersedes_policy_version_id"],
        unique=False,
    )

    op.create_table(
        "legal_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_key", sa.String(length=80), nullable=False),
        sa.Column("document_type", sa.String(length=30), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False, server_default="en-EN"),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("policy_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_key", "locale", "policy_version_id", name="uq_legal_documents_key_locale_policy"),
        sa.UniqueConstraint("policy_version_id"),
    )
    op.create_index(op.f("ix_legal_documents_document_key"), "legal_documents", ["document_key"], unique=False)
    op.create_index(op.f("ix_legal_documents_document_type"), "legal_documents", ["document_type"], unique=False)
    op.create_index(op.f("ix_legal_documents_locale"), "legal_documents", ["locale"], unique=False)
    op.create_index(
        op.f("ix_legal_documents_policy_version_id"),
        "legal_documents",
        ["policy_version_id"],
        unique=True,
    )

    op.create_table(
        "storefront_legal_doc_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("set_key", sa.String(length=80), nullable=False),
        sa.Column("storefront_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("auth_realm_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("policy_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("set_key", "policy_version_id", name="uq_legal_doc_sets_key_policy"),
        sa.UniqueConstraint("policy_version_id"),
    )
    op.create_index(
        op.f("ix_storefront_legal_doc_sets_set_key"),
        "storefront_legal_doc_sets",
        ["set_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_storefront_legal_doc_sets_storefront_id"),
        "storefront_legal_doc_sets",
        ["storefront_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_storefront_legal_doc_sets_auth_realm_id"),
        "storefront_legal_doc_sets",
        ["auth_realm_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_storefront_legal_doc_sets_policy_version_id"),
        "storefront_legal_doc_sets",
        ["policy_version_id"],
        unique=True,
    )

    op.create_table(
        "storefront_legal_doc_set_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("legal_document_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("legal_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["legal_document_id"], ["legal_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["legal_document_set_id"], ["storefront_legal_doc_sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("legal_document_set_id", "legal_document_id", name="uq_legal_doc_set_item_document"),
    )
    op.create_index(
        op.f("ix_storefront_legal_doc_set_items_legal_document_set_id"),
        "storefront_legal_doc_set_items",
        ["legal_document_set_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_storefront_legal_doc_set_items_legal_document_id"),
        "storefront_legal_doc_set_items",
        ["legal_document_id"],
        unique=False,
    )

    op.create_table(
        "accepted_legal_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("legal_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("legal_document_set_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("storefront_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("auth_realm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_principal_type", sa.String(length=30), nullable=False),
        sa.Column("acceptance_channel", sa.String(length=50), nullable=False),
        sa.Column("quote_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("checkout_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("device_context", sa.JSON(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            """
            (
                CASE WHEN legal_document_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN legal_document_set_id IS NOT NULL THEN 1 ELSE 0 END
            ) = 1
            """,
            name="ck_accepted_legal_documents_exactly_one_target",
        ),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["legal_document_id"], ["legal_documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["legal_document_set_id"], ["storefront_legal_doc_sets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_accepted_legal_documents_legal_document_id"),
        "accepted_legal_documents",
        ["legal_document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_accepted_legal_documents_legal_document_set_id"),
        "accepted_legal_documents",
        ["legal_document_set_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_accepted_legal_documents_storefront_id"),
        "accepted_legal_documents",
        ["storefront_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_accepted_legal_documents_auth_realm_id"),
        "accepted_legal_documents",
        ["auth_realm_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_accepted_legal_documents_actor_principal_id"),
        "accepted_legal_documents",
        ["actor_principal_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_accepted_legal_documents_actor_principal_type"),
        "accepted_legal_documents",
        ["actor_principal_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_accepted_legal_documents_quote_session_id"),
        "accepted_legal_documents",
        ["quote_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_accepted_legal_documents_checkout_session_id"),
        "accepted_legal_documents",
        ["checkout_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_accepted_legal_documents_order_id"),
        "accepted_legal_documents",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_accepted_legal_documents_accepted_at"),
        "accepted_legal_documents",
        ["accepted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_accepted_legal_documents_accepted_at"), table_name="accepted_legal_documents")
    op.drop_index(op.f("ix_accepted_legal_documents_order_id"), table_name="accepted_legal_documents")
    op.drop_index(op.f("ix_accepted_legal_documents_checkout_session_id"), table_name="accepted_legal_documents")
    op.drop_index(op.f("ix_accepted_legal_documents_quote_session_id"), table_name="accepted_legal_documents")
    op.drop_index(op.f("ix_accepted_legal_documents_actor_principal_type"), table_name="accepted_legal_documents")
    op.drop_index(op.f("ix_accepted_legal_documents_actor_principal_id"), table_name="accepted_legal_documents")
    op.drop_index(op.f("ix_accepted_legal_documents_auth_realm_id"), table_name="accepted_legal_documents")
    op.drop_index(op.f("ix_accepted_legal_documents_storefront_id"), table_name="accepted_legal_documents")
    op.drop_index(op.f("ix_accepted_legal_documents_legal_document_set_id"), table_name="accepted_legal_documents")
    op.drop_index(op.f("ix_accepted_legal_documents_legal_document_id"), table_name="accepted_legal_documents")
    op.drop_table("accepted_legal_documents")

    op.drop_index(
        op.f("ix_storefront_legal_doc_set_items_legal_document_id"),
        table_name="storefront_legal_doc_set_items",
    )
    op.drop_index(
        op.f("ix_storefront_legal_doc_set_items_legal_document_set_id"),
        table_name="storefront_legal_doc_set_items",
    )
    op.drop_table("storefront_legal_doc_set_items")

    op.drop_index(op.f("ix_storefront_legal_doc_sets_policy_version_id"), table_name="storefront_legal_doc_sets")
    op.drop_index(op.f("ix_storefront_legal_doc_sets_auth_realm_id"), table_name="storefront_legal_doc_sets")
    op.drop_index(op.f("ix_storefront_legal_doc_sets_storefront_id"), table_name="storefront_legal_doc_sets")
    op.drop_index(op.f("ix_storefront_legal_doc_sets_set_key"), table_name="storefront_legal_doc_sets")
    op.drop_table("storefront_legal_doc_sets")

    op.drop_index(op.f("ix_legal_documents_policy_version_id"), table_name="legal_documents")
    op.drop_index(op.f("ix_legal_documents_locale"), table_name="legal_documents")
    op.drop_index(op.f("ix_legal_documents_document_type"), table_name="legal_documents")
    op.drop_index(op.f("ix_legal_documents_document_key"), table_name="legal_documents")
    op.drop_table("legal_documents")

    op.drop_index(op.f("ix_policy_versions_supersedes_policy_version_id"), table_name="policy_versions")
    op.drop_index(op.f("ix_policy_versions_approved_by_admin_user_id"), table_name="policy_versions")
    op.drop_index(op.f("ix_policy_versions_created_by_admin_user_id"), table_name="policy_versions")
    op.drop_index(op.f("ix_policy_versions_effective_from"), table_name="policy_versions")
    op.drop_index(op.f("ix_policy_versions_version_status"), table_name="policy_versions")
    op.drop_index(op.f("ix_policy_versions_approval_state"), table_name="policy_versions")
    op.drop_index(op.f("ix_policy_versions_subject_id"), table_name="policy_versions")
    op.drop_index(op.f("ix_policy_versions_subject_type"), table_name="policy_versions")
    op.drop_index(op.f("ix_policy_versions_policy_key"), table_name="policy_versions")
    op.drop_index(op.f("ix_policy_versions_policy_family"), table_name="policy_versions")
    op.drop_table("policy_versions")
