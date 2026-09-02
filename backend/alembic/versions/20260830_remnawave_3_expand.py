"""Expand CyberVPN persistence for the Remnawave 2.8 -> 3.4 cutover.

Revision ID: 20260830_remnawave_3_expand
Revises: 20260711_plan_code_len
Create Date: 2026-08-30

This is intentionally an expand-only release migration: legacy UUID/provider
columns stay present for the independently rehearsed 2.8 rollback adapter.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_remnawave_3_expand"
down_revision: str | Sequence[str] | None = "20260711_plan_code_len"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mobile_users",
        sa.Column(
            "subscription_auto_renew_enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
            comment="CyberVPN-owned renewal opt-in migrated from Remnawave 2.8",
        ),
    )
    op.add_column(
        "mobile_users",
        sa.Column(
            "remnawave_user_id",
            sa.BigInteger(),
            nullable=True,
            comment="Canonical Remnawave 3.x numeric user id; UUID remains rollback-only",
        ),
    )
    op.create_index(
        "uq_mobile_users_remnawave_user_id_not_null",
        "mobile_users",
        ["remnawave_user_id"],
        unique=True,
        postgresql_where=sa.text("remnawave_user_id IS NOT NULL"),
    )

    op.add_column(
        "service_identities",
        sa.Column(
            "provider_numeric_subject_id",
            sa.BigInteger(),
            nullable=True,
            comment="Canonical numeric provider id; provider_subject_ref is the legacy rollback reference",
        ),
    )
    op.create_index(
        "ix_service_identities_provider_numeric_subject_id",
        "service_identities",
        ["provider_numeric_subject_id"],
        unique=False,
    )
    op.create_index(
        "uq_service_identities_remnawave_numeric_subscription",
        "service_identities",
        ["provider_name", "provider_numeric_subject_id"],
        unique=True,
        postgresql_where=sa.text("provider_numeric_subject_id IS NOT NULL AND identity_scope = 'subscription'"),
    )

    op.create_table(
        "remnawave_identity_reconciliations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("legacy_uuid", sa.String(length=36), nullable=True),
        sa.Column("numeric_user_id", sa.BigInteger(), nullable=True),
        sa.Column("reconciliation_state", sa.String(length=16), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "reconciliation_state IN ('pending', 'mapped', 'missing', 'duplicate', 'conflict')",
            name="ck_remnawave_reconciliation_state",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject_type", "subject_id", name="uq_remnawave_reconciliation_subject"),
    )
    op.create_index(
        "ix_remnawave_reconciliation_subject_numeric",
        "remnawave_identity_reconciliations",
        ["subject_type", "numeric_user_id"],
        unique=False,
    )
    op.create_index(
        "uq_remnawave_reconciliation_mapped_numeric",
        "remnawave_identity_reconciliations",
        ["subject_type", "numeric_user_id"],
        unique=True,
        postgresql_where=sa.text("numeric_user_id IS NOT NULL AND reconciliation_state = 'mapped'"),
    )
    op.create_index(
        "uq_remnawave_reconciliation_mapped_legacy",
        "remnawave_identity_reconciliations",
        ["subject_type", "legacy_uuid"],
        unique=True,
        postgresql_where=sa.text("legacy_uuid IS NOT NULL AND reconciliation_state = 'mapped'"),
    )
    for column in ("subject_type", "subject_id", "legacy_uuid", "numeric_user_id", "reconciliation_state"):
        op.create_index(
            f"ix_remnawave_identity_reconciliations_{column}",
            "remnawave_identity_reconciliations",
            [column],
        )

    op.create_table(
        "partner_remnawave_resource_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("resource_uuid", sa.Uuid(), nullable=False),
        sa.Column("permission_keys", sa.JSON(), nullable=False),
        sa.Column("granted_by_admin_user_id", sa.Uuid(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_by_admin_user_id", sa.Uuid(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("audit_reason", sa.String(length=500), nullable=False),
        sa.CheckConstraint(
            "resource_type IN ('node', 'host', 'profile', 'squad', 'tag', 'integration', 'shared_list')",
            name="ck_partner_remnawave_resource_type",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["partner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by_admin_user_id"], ["admin_users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revoked_by_admin_user_id"], ["admin_users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "resource_type", "resource_uuid", name="uq_partner_remnawave_grant"),
    )
    for column in (
        "workspace_id",
        "resource_type",
        "resource_uuid",
        "granted_by_admin_user_id",
        "revoked_by_admin_user_id",
        "revoked_at",
    ):
        op.create_index(
            f"ix_partner_remnawave_resource_grants_{column}",
            "partner_remnawave_resource_grants",
            [column],
        )

    op.create_table(
        "remnawave_stream_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("stream_name", sa.String(length=64), nullable=False),
        sa.Column("message_id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=12), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("processing_status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("redacted_error", sa.String(length=500), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "processing_status IN ('processing', 'committed', 'retry', 'dead_letter')",
            name="ck_remnawave_stream_receipt_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stream_name", "message_id", name="uq_remnawave_stream_receipt"),
    )
    for column in ("stream_name", "processing_status", "processed_at", "expires_at"):
        op.create_index(f"ix_remnawave_stream_receipts_{column}", "remnawave_stream_receipts", [column])

    op.create_table(
        "remnawave_stream_dead_letters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("stream_name", sa.String(length=64), nullable=False),
        sa.Column("message_id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=12), nullable=True),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=False),
        sa.Column("redacted_error", sa.String(length=500), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stream_name", "message_id", name="uq_remnawave_stream_dlq"),
    )
    for column in ("stream_name", "error_code", "expires_at"):
        op.create_index(f"ix_remnawave_stream_dead_letters_{column}", "remnawave_stream_dead_letters", [column])

    op.create_table(
        "remnawave_user_usage_hourly",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bucket_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("node_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("total_bytes", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bucket_at", "node_id", "user_id", name="uq_remnawave_user_usage_hour"),
    )
    for column in ("bucket_at", "node_id", "user_id", "expires_at"):
        op.create_index(f"ix_remnawave_user_usage_hourly_{column}", "remnawave_user_usage_hourly", [column])

    op.create_table(
        "remnawave_subscription_request_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("stream_message_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_type", sa.String(length=80), nullable=False),
        sa.Column("response_rule_name", sa.String(length=160), nullable=True),
        sa.Column("request_ip_hmac", sa.String(length=64), nullable=True),
        sa.Column("user_agent_family", sa.String(length=80), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stream_message_id", name="uq_remnawave_subscription_request_event"),
    )
    for column in ("user_id", "requested_at", "response_type", "request_ip_hmac", "expires_at"):
        op.create_index(
            f"ix_remnawave_subscription_request_events_{column}",
            "remnawave_subscription_request_events",
            [column],
        )

    op.create_table(
        "remnawave_node_user_presence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("ip_hmac", sa.String(length=64), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_id", "user_id", "ip_hmac", name="uq_remnawave_node_user_presence"),
    )
    for column in ("node_id", "user_id", "last_seen_at", "snapshot_at", "expires_at"):
        op.create_index(f"ix_remnawave_node_user_presence_{column}", "remnawave_node_user_presence", [column])

    op.create_table(
        "remnawave_node_connections_hourly",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bucket_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("node_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("connection_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bucket_at", "node_id", "user_id", name="uq_remnawave_node_connections_hour"),
    )
    for column in ("bucket_at", "node_id", "user_id", "expires_at"):
        op.create_index(
            f"ix_remnawave_node_connections_hourly_{column}",
            "remnawave_node_connections_hourly",
            [column],
        )

    op.create_table(
        "remnawave_stream_gaps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("gap_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("loss_kind", sa.String(length=16), nullable=False),
        sa.Column("stream_name", sa.String(length=64), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("missing_message_ids", sa.JSON(), nullable=False),
        sa.Column("missing_count", sa.Integer(), nullable=False),
        sa.Column("from_message_id", sa.String(length=64), nullable=True),
        sa.Column("to_message_id", sa.String(length=64), nullable=True),
        sa.Column("reconciliation_status", sa.String(length=16), nullable=False),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redacted_detail", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(loss_kind = 'exact_ids' AND missing_count >= 1 AND missing_count <= 1000) "
            "OR (loss_kind = 'unknown_range' AND missing_count = 0)",
            name="ck_remnawave_stream_gap_missing_count",
        ),
        sa.CheckConstraint(
            "reconciliation_status IN ('pending', 'running', 'reconciled', 'partial', 'failed')",
            name="ck_remnawave_stream_gap_status",
        ),
        sa.CheckConstraint(
            "(reconciliation_status IN ('pending', 'running') AND expires_at IS NULL) OR "
            "(reconciliation_status IN ('reconciled', 'partial', 'failed') AND expires_at IS NOT NULL)",
            name="ck_remnawave_stream_gap_terminal_expiry",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gap_fingerprint", name="uq_remnawave_stream_gap_fingerprint"),
    )
    for column in ("stream_name", "detected_at", "reconciliation_status", "expires_at"):
        op.create_index(f"ix_remnawave_stream_gaps_{column}", "remnawave_stream_gaps", [column])

    op.create_table(
        "remnawave_stream_checkpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("stream_name", sa.String(length=64), nullable=False),
        sa.Column("last_committed_message_id", sa.String(length=64), nullable=True),
        sa.Column("last_committed_ms", sa.BigInteger(), nullable=True),
        sa.Column("last_committed_sequence", sa.BigInteger(), nullable=True),
        sa.Column("observed_identity_hmac", sa.String(length=64), nullable=True),
        sa.Column("observed_first_message_id", sa.String(length=64), nullable=True),
        sa.Column("observed_last_message_id", sa.String(length=64), nullable=True),
        sa.Column("observed_group_last_delivered_id", sa.String(length=64), nullable=True),
        sa.Column("observed_group_pending_count", sa.Integer(), nullable=False),
        sa.Column("observed_group_pending_min_id", sa.String(length=64), nullable=True),
        sa.Column("observed_group_pending_max_id", sa.String(length=64), nullable=True),
        sa.Column("stream_exists", sa.Boolean(), nullable=False),
        sa.Column("group_exists", sa.Boolean(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stream_name", name="uq_remnawave_stream_checkpoint"),
    )
    op.create_index(
        "ix_remnawave_stream_checkpoints_stream_name",
        "remnawave_stream_checkpoints",
        ["stream_name"],
    )


def downgrade() -> None:
    op.drop_table("remnawave_stream_checkpoints")
    op.drop_table("remnawave_stream_gaps")
    op.drop_table("remnawave_node_connections_hourly")
    op.drop_table("remnawave_node_user_presence")
    op.drop_table("remnawave_subscription_request_events")
    op.drop_table("remnawave_user_usage_hourly")
    op.drop_table("remnawave_stream_dead_letters")
    op.drop_table("remnawave_stream_receipts")
    op.drop_table("partner_remnawave_resource_grants")
    op.drop_table("remnawave_identity_reconciliations")

    op.drop_index("uq_service_identities_remnawave_numeric_subscription", table_name="service_identities")
    op.drop_index("ix_service_identities_provider_numeric_subject_id", table_name="service_identities")
    op.drop_column("service_identities", "provider_numeric_subject_id")
    op.drop_index("uq_mobile_users_remnawave_user_id_not_null", table_name="mobile_users")
    op.drop_column("mobile_users", "remnawave_user_id")
    op.drop_column("mobile_users", "subscription_auto_renew_enabled")
