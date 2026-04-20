"""Add phase 1 risk graph foundation.

Revision ID: 20260418_phase1_risk_foundation
Revises: 20260417_phase1_policy_versions_and_legal_docs
Create Date: 2026-04-18 03:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260418_phase1_risk_foundation"
down_revision: str | None = "20260417_phase1_policy_versions_and_legal_docs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "risk_subjects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal_class", sa.String(length=30), nullable=False),
        sa.Column("principal_subject", sa.String(length=120), nullable=False),
        sa.Column("auth_realm_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("storefront_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="low"),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "principal_class",
            "principal_subject",
            "auth_realm_id",
            name="uq_risk_subjects_principal_realm",
        ),
    )
    op.create_index(op.f("ix_risk_subjects_principal_class"), "risk_subjects", ["principal_class"], unique=False)
    op.create_index(op.f("ix_risk_subjects_principal_subject"), "risk_subjects", ["principal_subject"], unique=False)
    op.create_index(op.f("ix_risk_subjects_auth_realm_id"), "risk_subjects", ["auth_realm_id"], unique=False)
    op.create_index(op.f("ix_risk_subjects_storefront_id"), "risk_subjects", ["storefront_id"], unique=False)

    op.create_table(
        "risk_identifiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identifier_type", sa.String(length=40), nullable=False),
        sa.Column("value_hash", sa.String(length=64), nullable=False),
        sa.Column("value_preview", sa.String(length=120), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["risk_subject_id"], ["risk_subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "risk_subject_id",
            "identifier_type",
            "value_hash",
            name="uq_risk_identifiers_subject_type_hash",
        ),
    )
    op.create_index(
        op.f("ix_risk_identifiers_risk_subject_id"),
        "risk_identifiers",
        ["risk_subject_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_risk_identifiers_identifier_type"),
        "risk_identifiers",
        ["identifier_type"],
        unique=False,
    )
    op.create_index(op.f("ix_risk_identifiers_value_hash"), "risk_identifiers", ["value_hash"], unique=False)

    op.create_table(
        "risk_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("left_subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("right_subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("link_type", sa.String(length=40), nullable=False),
        sa.Column("identifier_type", sa.String(length=40), nullable=False),
        sa.Column("source_identifier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["left_subject_id"], ["risk_subjects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["right_subject_id"], ["risk_subjects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_identifier_id"], ["risk_identifiers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "left_subject_id",
            "right_subject_id",
            "identifier_type",
            name="uq_risk_links_subject_pair_identifier_type",
        ),
    )
    op.create_index(op.f("ix_risk_links_left_subject_id"), "risk_links", ["left_subject_id"], unique=False)
    op.create_index(op.f("ix_risk_links_right_subject_id"), "risk_links", ["right_subject_id"], unique=False)
    op.create_index(op.f("ix_risk_links_link_type"), "risk_links", ["link_type"], unique=False)
    op.create_index(op.f("ix_risk_links_identifier_type"), "risk_links", ["identifier_type"], unique=False)
    op.create_index(
        op.f("ix_risk_links_source_identifier_id"),
        "risk_links",
        ["source_identifier_id"],
        unique=False,
    )

    op.create_table(
        "risk_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("decision", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_by_admin_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_by_admin_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["risk_subject_id"], ["risk_subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risk_reviews_risk_subject_id"), "risk_reviews", ["risk_subject_id"], unique=False)
    op.create_index(op.f("ix_risk_reviews_review_type"), "risk_reviews", ["review_type"], unique=False)
    op.create_index(op.f("ix_risk_reviews_status"), "risk_reviews", ["status"], unique=False)
    op.create_index(op.f("ix_risk_reviews_decision"), "risk_reviews", ["decision"], unique=False)
    op.create_index(
        op.f("ix_risk_reviews_created_by_admin_user_id"),
        "risk_reviews",
        ["created_by_admin_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_risk_reviews_resolved_by_admin_user_id"),
        "risk_reviews",
        ["resolved_by_admin_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_risk_reviews_resolved_by_admin_user_id"), table_name="risk_reviews")
    op.drop_index(op.f("ix_risk_reviews_created_by_admin_user_id"), table_name="risk_reviews")
    op.drop_index(op.f("ix_risk_reviews_decision"), table_name="risk_reviews")
    op.drop_index(op.f("ix_risk_reviews_status"), table_name="risk_reviews")
    op.drop_index(op.f("ix_risk_reviews_review_type"), table_name="risk_reviews")
    op.drop_index(op.f("ix_risk_reviews_risk_subject_id"), table_name="risk_reviews")
    op.drop_table("risk_reviews")

    op.drop_index(op.f("ix_risk_links_source_identifier_id"), table_name="risk_links")
    op.drop_index(op.f("ix_risk_links_identifier_type"), table_name="risk_links")
    op.drop_index(op.f("ix_risk_links_link_type"), table_name="risk_links")
    op.drop_index(op.f("ix_risk_links_right_subject_id"), table_name="risk_links")
    op.drop_index(op.f("ix_risk_links_left_subject_id"), table_name="risk_links")
    op.drop_table("risk_links")

    op.drop_index(op.f("ix_risk_identifiers_value_hash"), table_name="risk_identifiers")
    op.drop_index(op.f("ix_risk_identifiers_identifier_type"), table_name="risk_identifiers")
    op.drop_index(op.f("ix_risk_identifiers_risk_subject_id"), table_name="risk_identifiers")
    op.drop_table("risk_identifiers")

    op.drop_index(op.f("ix_risk_subjects_storefront_id"), table_name="risk_subjects")
    op.drop_index(op.f("ix_risk_subjects_auth_realm_id"), table_name="risk_subjects")
    op.drop_index(op.f("ix_risk_subjects_principal_subject"), table_name="risk_subjects")
    op.drop_index(op.f("ix_risk_subjects_principal_class"), table_name="risk_subjects")
    op.drop_table("risk_subjects")
