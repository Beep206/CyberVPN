"""Durable privacy request workflow.

Revision ID: 20260619_privacy_request
Revises: 20260619_referral_attribution
Create Date: 2026-06-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260619_privacy_request"
down_revision: str | Sequence[str] | None = "20260619_referral_attribution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIVE_STATUS_SQL = (
    "status IN ('submitted', 'identity_verification', 'pending_decision', 'approved', 'scheduled', 'failed')"
)
SCHEDULED_STATUS_SQL = "status IN ('approved', 'scheduled', 'failed')"


def _uuid_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.Uuid()


def _json_default() -> sa.TextClause:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.text("'{}'::jsonb")
    return sa.text("'{}'")


def _replace_support_customer_fk(*, ondelete: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return

    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys("support_tickets"):
        if fk.get("constrained_columns") == ["customer_account_id"] and fk.get("referred_table") == "mobile_users":
            op.drop_constraint(fk["name"], "support_tickets", type_="foreignkey")
            break

    op.create_foreign_key(
        "fk_support_tickets_customer_account_id_mobile_users",
        "support_tickets",
        "mobile_users",
        ["customer_account_id"],
        ["id"],
        ondelete=ondelete,
    )


def upgrade() -> None:
    uuid_type = _uuid_type()

    _replace_support_customer_fk(ondelete="SET NULL")

    op.create_table(
        "privacy_requests",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("public_id", sa.String(length=40), nullable=False),
        sa.Column("auth_realm_id", uuid_type, nullable=False),
        sa.Column("principal_type", sa.String(length=40), nullable=False),
        sa.Column("principal_subject", uuid_type, nullable=False),
        sa.Column("customer_account_id", uuid_type, nullable=True),
        sa.Column("support_ticket_id", uuid_type, nullable=False),
        sa.Column("request_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("notes_redacted", sa.Text(), nullable=True),
        sa.Column("locale", sa.String(length=10), nullable=True),
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=True),
        sa.Column("policy_snapshot", sa.JSON(), server_default=_json_default(), nullable=False),
        sa.Column("assigned_admin_id", uuid_type, nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("review_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("identity_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("identity_verified_by", uuid_type, nullable=True),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_by", uuid_type, nullable=True),
        sa.Column("decision_reason", sa.String(length=500), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fulfilled_by", uuid_type, nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_by", uuid_type, nullable=True),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("last_error_redacted", sa.String(length=500), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assigned_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_account_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["decision_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fulfilled_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["identity_verified_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["support_ticket_id"], ["support_tickets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_privacy_requests_public_id"),
        sa.UniqueConstraint("support_ticket_id", name="uq_privacy_requests_support_ticket_id"),
    )
    op.create_index("ix_privacy_requests_public_id", "privacy_requests", ["public_id"])
    op.create_index("ix_privacy_requests_auth_realm_id", "privacy_requests", ["auth_realm_id"])
    op.create_index("ix_privacy_requests_customer_account_id", "privacy_requests", ["customer_account_id"])
    op.create_index("ix_privacy_requests_support_ticket_id", "privacy_requests", ["support_ticket_id"])
    op.create_index("ix_privacy_requests_request_type", "privacy_requests", ["request_type"])
    op.create_index("ix_privacy_requests_status", "privacy_requests", ["status"])
    op.create_index("ix_privacy_requests_assigned_admin_id", "privacy_requests", ["assigned_admin_id"])
    op.create_index("ix_privacy_requests_status_submitted", "privacy_requests", ["status", "submitted_at"])
    op.create_index(
        "ix_privacy_requests_type_status_submitted",
        "privacy_requests",
        ["request_type", "status", "submitted_at"],
    )
    op.create_index(
        "ix_privacy_requests_assignee_status_updated",
        "privacy_requests",
        ["assigned_admin_id", "status", "updated_at"],
    )
    op.create_index(
        "ix_privacy_requests_principal_submitted",
        "privacy_requests",
        ["principal_subject", "submitted_at"],
    )
    op.create_index(
        "ix_privacy_requests_scheduled_due",
        "privacy_requests",
        ["scheduled_for"],
        postgresql_where=sa.text(SCHEDULED_STATUS_SQL),
        sqlite_where=sa.text(SCHEDULED_STATUS_SQL),
    )
    op.create_index(
        "uq_privacy_requests_active_principal",
        "privacy_requests",
        ["auth_realm_id", "principal_type", "principal_subject", "request_type"],
        unique=True,
        postgresql_where=sa.text(ACTIVE_STATUS_SQL),
        sqlite_where=sa.text(ACTIVE_STATUS_SQL),
    )
    op.create_index(
        "uq_privacy_requests_idempotency_key_hash",
        "privacy_requests",
        ["idempotency_key_hash"],
        unique=True,
        postgresql_where=sa.text("idempotency_key_hash IS NOT NULL"),
        sqlite_where=sa.text("idempotency_key_hash IS NOT NULL"),
    )

    op.create_table(
        "privacy_request_events",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("privacy_request_id", uuid_type, nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("actor_id", uuid_type, nullable=True),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=True),
        sa.Column("safe_summary", sa.String(length=500), nullable=False),
        sa.Column("metadata", sa.JSON(), server_default=_json_default(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["privacy_request_id"], ["privacy_requests.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_privacy_request_events_privacy_request_id", "privacy_request_events", ["privacy_request_id"])
    op.create_index("ix_privacy_request_events_event_type", "privacy_request_events", ["event_type"])
    op.create_index(
        "ix_privacy_request_events_request_created",
        "privacy_request_events",
        ["privacy_request_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_privacy_request_events_request_created", table_name="privacy_request_events")
    op.drop_index("ix_privacy_request_events_event_type", table_name="privacy_request_events")
    op.drop_index("ix_privacy_request_events_privacy_request_id", table_name="privacy_request_events")
    op.drop_table("privacy_request_events")

    op.drop_index("uq_privacy_requests_idempotency_key_hash", table_name="privacy_requests")
    op.drop_index("uq_privacy_requests_active_principal", table_name="privacy_requests")
    op.drop_index("ix_privacy_requests_scheduled_due", table_name="privacy_requests")
    op.drop_index("ix_privacy_requests_principal_submitted", table_name="privacy_requests")
    op.drop_index("ix_privacy_requests_assignee_status_updated", table_name="privacy_requests")
    op.drop_index("ix_privacy_requests_type_status_submitted", table_name="privacy_requests")
    op.drop_index("ix_privacy_requests_status_submitted", table_name="privacy_requests")
    op.drop_index("ix_privacy_requests_assigned_admin_id", table_name="privacy_requests")
    op.drop_index("ix_privacy_requests_status", table_name="privacy_requests")
    op.drop_index("ix_privacy_requests_request_type", table_name="privacy_requests")
    op.drop_index("ix_privacy_requests_support_ticket_id", table_name="privacy_requests")
    op.drop_index("ix_privacy_requests_customer_account_id", table_name="privacy_requests")
    op.drop_index("ix_privacy_requests_auth_realm_id", table_name="privacy_requests")
    op.drop_index("ix_privacy_requests_public_id", table_name="privacy_requests")
    op.drop_table("privacy_requests")

    _replace_support_customer_fk(ondelete="CASCADE")
