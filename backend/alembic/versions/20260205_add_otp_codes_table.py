"""Add otp_codes table and is_email_verified column.

Revision ID: 20260205_otp_codes
Revises: 20260205_mobile_auth
Create Date: 2026-02-05

Creates otp_codes table for email verification codes and adds
is_email_verified column to admin_users table.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260205_otp_codes"
down_revision: str | None = "20260205_mobile_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Note: is_email_verified column is created in initial migration

    # Create otp_codes table
    op.create_table(
        "otp_codes",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(6), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False, server_default="email_verification"),
        sa.Column("attempts_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("resend_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_resends", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("last_resend_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_otp_codes")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["admin_users.id"],
            name=op.f("fk_otp_codes_user_id_admin_users"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("code ~ '^[0-9]{6}$'", name="ck_otp_codes_valid_code"),
        sa.CheckConstraint(
            "purpose IN ('email_verification', 'password_reset', 'login_2fa')",
            name="ck_otp_codes_valid_purpose",
        ),
    )

    # Create indexes
    op.create_index(op.f("ix_otp_codes_user_id"), "otp_codes", ["user_id"])
    op.create_index(
        "ix_otp_codes_expires_at_pending",
        "otp_codes",
        ["expires_at"],
        postgresql_where=sa.text("verified_at IS NULL"),
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_otp_codes_expires_at_pending", table_name="otp_codes")
    op.drop_index(op.f("ix_otp_codes_user_id"), table_name="otp_codes")

    # Drop otp_codes table
    op.drop_table("otp_codes")

    # Note: is_email_verified column is dropped in initial migration downgrade
