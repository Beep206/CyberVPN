"""Add Growth v6.2 FX lifecycle and connection session state.

Revision ID: 20260627_growth_v62_db
Revises: 20260626_reg_access_idem
Create Date: 2026-06-27
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260627_growth_v62_db"
down_revision: str | Sequence[str] | None = "20260626_reg_access_idem"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    json_type = _json_type(bind)

    _create_fx_provider_configs(json_type, bind)
    _extend_fx_rate_snapshots()
    _backfill_fx_rate_snapshot_lifecycle(bind)
    _create_fx_provider_refresh_runs(json_type, bind)
    _create_customer_connection_sessions(json_type, bind)


def downgrade() -> None:
    op.drop_table("customer_connection_sessions")
    op.drop_table("fx_provider_refresh_runs")

    with op.batch_alter_table("fx_rate_snapshots") as batch_op:
        batch_op.drop_index("ix_fx_rate_snapshots_approved_by_admin_id")
        batch_op.drop_index("ix_fx_rate_snapshots_checksum")
        batch_op.drop_index("ix_fx_rate_snapshots_approval_state")
        batch_op.drop_index("ix_fx_rate_snapshots_provider_config_id")
        batch_op.drop_constraint("ck_fx_rate_snapshots_provider_priority_non_negative", type_="check")
        batch_op.drop_constraint("ck_fx_rate_snapshots_approval_state", type_="check")
        batch_op.drop_constraint("fk_fx_rate_snapshots_approved_by_admin_id_admin_users", type_="foreignkey")
        batch_op.drop_constraint("fk_fx_rate_snapshots_provider_config_id_fx_provider_configs", type_="foreignkey")
        batch_op.drop_column("raw_provider_payload_hash")
        batch_op.drop_column("checksum")
        batch_op.drop_column("rejection_reason")
        batch_op.drop_column("approved_at")
        batch_op.drop_column("approved_by_admin_id")
        batch_op.drop_column("approval_state")
        batch_op.drop_column("provider_priority")
        batch_op.drop_column("provider_config_id")

    op.drop_table("fx_provider_configs")


def _create_fx_provider_configs(json_type: sa.types.TypeEngine, bind: sa.Connection) -> None:
    op.create_table(
        "fx_provider_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_key", sa.String(length=80), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("supported_pairs", json_type, nullable=False, server_default=_json_default(bind, "[]")),
        sa.Column("stale_after_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("rate_ttl_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("requires_admin_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata", json_type, nullable=False, server_default=_json_default(bind, "{}")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("priority >= 0", name="ck_fx_provider_configs_priority_non_negative"),
        sa.CheckConstraint("stale_after_seconds > 0", name="ck_fx_provider_configs_stale_after_positive"),
        sa.CheckConstraint("rate_ttl_seconds > 0", name="ck_fx_provider_configs_rate_ttl_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_key", name="uq_fx_provider_configs_provider_key"),
    )
    op.create_index("ix_fx_provider_configs_enabled", "fx_provider_configs", ["enabled"])
    op.create_index("ix_fx_provider_configs_priority", "fx_provider_configs", ["priority"])


def _extend_fx_rate_snapshots() -> None:
    with op.batch_alter_table("fx_rate_snapshots") as batch_op:
        batch_op.add_column(sa.Column("provider_config_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("provider_priority", sa.Integer(), nullable=False, server_default="100"))
        batch_op.add_column(sa.Column("approval_state", sa.String(length=20), nullable=False, server_default="pending"))
        batch_op.add_column(sa.Column("approved_by_admin_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("rejection_reason", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("checksum", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("raw_provider_payload_hash", sa.String(length=128), nullable=True))
        batch_op.create_foreign_key(
            "fk_fx_rate_snapshots_provider_config_id_fx_provider_configs",
            "fx_provider_configs",
            ["provider_config_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_fx_rate_snapshots_approved_by_admin_id_admin_users",
            "admin_users",
            ["approved_by_admin_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_check_constraint(
            "ck_fx_rate_snapshots_provider_priority_non_negative",
            "provider_priority >= 0",
        )
        batch_op.create_check_constraint(
            "ck_fx_rate_snapshots_approval_state",
            "approval_state IN ('pending','approved','rejected','expired')",
        )
        batch_op.create_index("ix_fx_rate_snapshots_provider_config_id", ["provider_config_id"])
        batch_op.create_index("ix_fx_rate_snapshots_approval_state", ["approval_state"])
        batch_op.create_index("ix_fx_rate_snapshots_checksum", ["checksum"])
        batch_op.create_index("ix_fx_rate_snapshots_approved_by_admin_id", ["approved_by_admin_id"])


def _create_fx_provider_refresh_runs(json_type: sa.types.TypeEngine, bind: sa.Connection) -> None:
    op.create_table(
        "fx_provider_refresh_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_config_id", sa.Uuid(), nullable=True),
        sa.Column("provider_key", sa.String(length=80), nullable=False),
        sa.Column("run_key", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("trigger_type", sa.String(length=30), nullable=False),
        sa.Column("requested_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pairs_requested", json_type, nullable=False, server_default=_json_default(bind, "[]")),
        sa.Column("pairs_succeeded", json_type, nullable=False, server_default=_json_default(bind, "[]")),
        sa.Column("pairs_failed", json_type, nullable=False, server_default=_json_default(bind, "[]")),
        sa.Column("created_snapshot_ids", json_type, nullable=False, server_default=_json_default(bind, "[]")),
        sa.Column("provider_payload_hash", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", json_type, nullable=False, server_default=_json_default(bind, "{}")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('pending','running','succeeded','failed','partial','cancelled')",
            name="ck_fx_provider_refresh_runs_status",
        ),
        sa.CheckConstraint(
            "trigger_type IN ('scheduled','admin','manual','system_retry')",
            name="ck_fx_provider_refresh_runs_trigger_type",
        ),
        sa.ForeignKeyConstraint(["provider_config_id"], ["fx_provider_configs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_key", name="uq_fx_provider_refresh_runs_run_key"),
    )
    op.create_index(
        "ix_fx_provider_refresh_runs_provider_config_id",
        "fx_provider_refresh_runs",
        ["provider_config_id"],
    )
    op.create_index("ix_fx_provider_refresh_runs_provider_key", "fx_provider_refresh_runs", ["provider_key"])
    op.create_index("ix_fx_provider_refresh_runs_status", "fx_provider_refresh_runs", ["status"])
    op.create_index("ix_fx_provider_refresh_runs_trigger_type", "fx_provider_refresh_runs", ["trigger_type"])
    op.create_index(
        "ix_fx_provider_refresh_runs_requested_by_admin_id",
        "fx_provider_refresh_runs",
        ["requested_by_admin_id"],
    )
    op.create_index("ix_fx_provider_refresh_runs_started_at", "fx_provider_refresh_runs", ["started_at"])


def _create_customer_connection_sessions(json_type: sa.types.TypeEngine, bind: sa.Connection) -> None:
    op.create_table(
        "customer_connection_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("mobile_user_id", sa.Uuid(), nullable=False),
        sa.Column("onboarding_state_id", sa.Uuid(), nullable=True),
        sa.Column("source_surface", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("subscription_config_hash", sa.String(length=128), nullable=False),
        sa.Column("session_key_hash", sa.String(length=128), nullable=True),
        sa.Column("selected_platform", sa.String(length=20), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_source_surface", sa.String(length=30), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", json_type, nullable=False, server_default=_json_default(bind, "{}")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "source_surface IN ('web','miniapp','telegram_bot')",
            name="ck_customer_connection_sessions_source_surface",
        ),
        sa.CheckConstraint(
            "acknowledged_source_surface IS NULL OR acknowledged_source_surface IN ('web','miniapp','telegram_bot')",
            name="ck_customer_connection_sessions_ack_surface",
        ),
        sa.CheckConstraint(
            "status IN ('pending','available','acknowledged','expired','unavailable','cancelled')",
            name="ck_customer_connection_sessions_status",
        ),
        sa.CheckConstraint(
            "selected_platform IS NULL OR selected_platform IN ('ios','android','windows','macos','linux','unknown')",
            name="ck_customer_connection_sessions_platform",
        ),
        sa.ForeignKeyConstraint(["mobile_user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["onboarding_state_id"], ["customer_onboarding_states.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mobile_user_id",
            "subscription_config_hash",
            name="uq_customer_connection_sessions_user_config_hash",
        ),
        sa.UniqueConstraint("session_key_hash", name="uq_customer_connection_sessions_session_key_hash"),
    )
    for column_name in (
        "mobile_user_id",
        "onboarding_state_id",
        "source_surface",
        "status",
        "subscription_config_hash",
        "selected_platform",
        "acknowledged_at",
        "expires_at",
    ):
        op.create_index(
            f"ix_customer_connection_sessions_{column_name}",
            "customer_connection_sessions",
            [column_name],
        )


def _backfill_fx_rate_snapshot_lifecycle(bind: sa.Connection) -> None:
    rows = bind.execute(
        sa.text(
            """
            SELECT id,
                   base_currency,
                   quote_currency,
                   rate,
                   inverse_rate,
                   source_type,
                   provider_key,
                   provider_rate_id,
                   observed_at,
                   fetched_at,
                   valid_until,
                   status,
                   metadata
            FROM fx_rate_snapshots
            """
        )
    ).mappings()
    for row in rows:
        metadata = row["metadata"] if isinstance(row["metadata"], Mapping) else {}
        priority = _positive_int(metadata.get("provider_priority"), default=100)
        approval_state = _approval_state(str(row["status"]))
        approved_at = _optional_datetime(metadata.get("approved_at"))
        raw_payload_hash = _optional_string(metadata.get("raw_provider_payload_hash"))
        checksum = _checksum(
            {
                "base_currency": row["base_currency"],
                "quote_currency": row["quote_currency"],
                "rate": row["rate"],
                "inverse_rate": row["inverse_rate"],
                "source_type": row["source_type"],
                "provider_key": row["provider_key"],
                "provider_rate_id": row["provider_rate_id"],
                "observed_at": row["observed_at"],
                "fetched_at": row["fetched_at"],
                "valid_until": row["valid_until"],
                "status": row["status"],
            }
        )
        bind.execute(
            sa.text(
                """
                UPDATE fx_rate_snapshots
                SET provider_priority = :provider_priority,
                    approval_state = :approval_state,
                    approved_at = :approved_at,
                    checksum = :checksum,
                    raw_provider_payload_hash = :raw_provider_payload_hash
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "provider_priority": priority,
                "approval_state": approval_state,
                "approved_at": approved_at,
                "checksum": checksum,
                "raw_provider_payload_hash": raw_payload_hash,
            },
        )


def _approval_state(status: str) -> str:
    normalized = status.strip().lower()
    if normalized in {"pending", "pending_approval"}:
        return "pending"
    if normalized in {"rejected", "declined"}:
        return "rejected"
    if normalized == "expired":
        return "expired"
    return "approved"


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _optional_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _optional_string(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _checksum(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        {key: _json_safe(value) for key, value in sorted(payload.items())},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _json_type(bind: sa.Connection) -> sa.types.TypeEngine:
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_default(bind: sa.Connection, value: str) -> sa.TextClause:
    if bind.dialect.name == "postgresql":
        return sa.text(f"'{value}'::jsonb")
    return sa.text(f"'{value}'")
