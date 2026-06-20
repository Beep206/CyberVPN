"""Partner attribution v2 canonical sessions and code policy.

Revision ID: 20260620_partner_attribution_v2
Revises: 20260619_privacy_request
Create Date: 2026-06-20
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260620_partner_attribution_v2"
down_revision: str | Sequence[str] | None = "20260619_privacy_request"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.Uuid()


def _json_default(payload: str) -> sa.TextClause:
    return sa.text(f"'{payload}'")


def _public_token_hash(code_id: object) -> str:
    token = f"px_{str(code_id).replace('-', '')}"
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _drop_fk(table_name: str, constrained_columns: list[str], referred_table: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys(table_name):
        if fk.get("constrained_columns") == constrained_columns and fk.get("referred_table") == referred_table:
            op.drop_constraint(fk["name"], table_name, type_="foreignkey")
            return


def upgrade() -> None:
    uuid_type = _uuid_type()

    op.add_column("partner_codes", sa.Column("code_normalized", sa.String(length=30), nullable=True))
    op.add_column("partner_codes", sa.Column("public_token_hash", sa.String(length=128), nullable=True))
    op.add_column(
        "partner_codes",
        sa.Column("code_kind", sa.String(length=32), server_default="starter_code", nullable=False),
    )
    op.add_column(
        "partner_codes",
        sa.Column("lifecycle_status", sa.String(length=24), server_default="active", nullable=False),
    )
    op.add_column(
        "partner_codes",
        sa.Column("owner_type", sa.String(length=30), server_default="affiliate", nullable=False),
    )
    op.add_column(
        "partner_codes",
        sa.Column("lane_key", sa.String(length=60), server_default="creator_affiliate", nullable=False),
    )
    op.add_column(
        "partner_codes",
        sa.Column("attribution_model", sa.String(length=40), server_default="last_eligible_touch", nullable=False),
    )
    op.add_column(
        "partner_codes",
        sa.Column("attribution_window_seconds", sa.Integer(), server_default=str(30 * 24 * 60 * 60), nullable=False),
    )
    op.add_column("partner_codes", sa.Column("commission_contract_id", uuid_type, nullable=True))
    op.add_column("partner_codes", sa.Column("policy_version_id", uuid_type, nullable=True))
    op.add_column("partner_codes", sa.Column("default_storefront_id", uuid_type, nullable=True))
    op.add_column("partner_codes", sa.Column("destination_path", sa.String(length=500), nullable=True))
    op.add_column(
        "partner_codes",
        sa.Column(
            "allowed_channels",
            sa.JSON(),
            server_default=_json_default('["content","telegram","storefront"]'),
            nullable=False,
        ),
    )
    op.add_column(
        "partner_codes",
        sa.Column("allowed_storefront_ids", sa.JSON(), server_default=_json_default('["*"]'), nullable=False),
    )
    op.add_column(
        "partner_codes",
        sa.Column("allowed_geographies", sa.JSON(), server_default=_json_default('["*"]'), nullable=False),
    )
    op.add_column(
        "partner_codes",
        sa.Column("sub_id_schema", sa.JSON(), server_default=_json_default("{}"), nullable=False),
    )
    op.add_column(
        "partner_codes",
        sa.Column("approval_status", sa.String(length=24), server_default="approved", nullable=False),
    )
    op.add_column("partner_codes", sa.Column("active_from", sa.DateTime(timezone=True), nullable=True))
    op.add_column("partner_codes", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("partner_codes", sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("partner_codes", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("partner_codes", sa.Column("created_by_admin_user_id", uuid_type, nullable=True))
    op.add_column("partner_codes", sa.Column("updated_by_admin_user_id", uuid_type, nullable=True))
    op.add_column("partner_codes", sa.Column("version", sa.Integer(), server_default="1", nullable=False))

    bind = op.get_bind()
    rows = (
        bind.execute(sa.text("SELECT id, code, is_active FROM partner_codes ORDER BY created_at, id")).mappings().all()
    )
    seen: set[str] = set()
    for row in rows:
        normalized = str(row["code"]).strip().upper()
        if normalized in seen:
            normalized = f"{normalized[:21]}_{str(row['id']).replace('-', '')[:8]}"
        seen.add(normalized)
        status = "active" if row["is_active"] else "paused"
        bind.execute(
            sa.text(
                """
                UPDATE partner_codes
                SET code_normalized = :code_normalized,
                    public_token_hash = :public_token_hash,
                    lifecycle_status = :lifecycle_status,
                    approval_status = 'approved'
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "code_normalized": normalized,
                "public_token_hash": _public_token_hash(row["id"]),
                "lifecycle_status": status,
            },
        )

    if bind.dialect.name != "sqlite":
        op.alter_column("partner_codes", "partner_user_id", existing_type=uuid_type, nullable=True)
        _drop_fk("partner_codes", ["partner_user_id"], "mobile_users")
        op.create_foreign_key(
            "fk_partner_codes_partner_user_id_mobile_users",
            "partner_codes",
            "mobile_users",
            ["partner_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.alter_column("partner_earnings", "partner_user_id", existing_type=uuid_type, nullable=True)
        _drop_fk("partner_earnings", ["partner_user_id"], "mobile_users")
        op.create_foreign_key(
            "fk_partner_earnings_partner_user_id_mobile_users",
            "partner_earnings",
            "mobile_users",
            ["partner_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.alter_column("partner_earnings", "partner_code_id", existing_type=uuid_type, nullable=True)
        _drop_fk("partner_earnings", ["partner_code_id"], "partner_codes")
        op.create_foreign_key(
            "fk_partner_earnings_partner_code_id_partner_codes",
            "partner_earnings",
            "partner_codes",
            ["partner_code_id"],
            ["id"],
            ondelete="SET NULL",
        )
        _drop_fk("earning_events", ["partner_user_id"], "mobile_users")
        op.alter_column("earning_events", "partner_user_id", existing_type=uuid_type, nullable=True)
        op.create_foreign_key(
            "fk_earning_events_partner_user_id_mobile_users",
            "earning_events",
            "mobile_users",
            ["partner_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_index("ix_partner_codes_code_normalized", "partner_codes", ["code_normalized"], unique=True)
    op.create_index("ix_partner_codes_public_token_hash", "partner_codes", ["public_token_hash"], unique=True)
    op.create_index("ix_partner_codes_lifecycle_status", "partner_codes", ["lifecycle_status"])
    op.create_index("ix_partner_codes_owner_type", "partner_codes", ["owner_type"])
    op.create_index("ix_partner_codes_lane_key", "partner_codes", ["lane_key"])
    op.create_index("ix_partner_codes_policy_version_id", "partner_codes", ["policy_version_id"])
    op.create_index("ix_partner_codes_default_storefront_id", "partner_codes", ["default_storefront_id"])
    op.create_index("ix_partner_codes_approval_status", "partner_codes", ["approval_status"])
    op.create_index("ix_partner_codes_expires_at", "partner_codes", ["expires_at"])
    op.create_index("ix_partner_codes_created_by_admin_user_id", "partner_codes", ["created_by_admin_user_id"])
    op.create_index("ix_partner_codes_updated_by_admin_user_id", "partner_codes", ["updated_by_admin_user_id"])
    op.create_foreign_key(
        "fk_partner_codes_policy_version_id_policy_versions",
        "partner_codes",
        "policy_versions",
        ["policy_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_partner_codes_default_storefront_id_storefronts",
        "partner_codes",
        "storefronts",
        ["default_storefront_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_partner_codes_created_by_admin_user_id_admin_users",
        "partner_codes",
        "admin_users",
        ["created_by_admin_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_partner_codes_updated_by_admin_user_id_admin_users",
        "partner_codes",
        "admin_users",
        ["updated_by_admin_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint("ck_partner_codes_markup_pct_nonnegative", "partner_codes", "markup_pct >= 0")
    op.create_check_constraint(
        "ck_partner_codes_attribution_window_positive",
        "partner_codes",
        "attribution_window_seconds > 0",
    )

    op.create_table(
        "partner_attribution_sessions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("transfer_token_hash", sa.String(length=128), nullable=True),
        sa.Column("partner_code_id", uuid_type, nullable=False),
        sa.Column("partner_account_id", uuid_type, nullable=True),
        sa.Column("auth_realm_id", uuid_type, nullable=True),
        sa.Column("storefront_id", uuid_type, nullable=True),
        sa.Column("status", sa.String(length=24), server_default="pending", nullable=False),
        sa.Column("owner_type", sa.String(length=30), server_default="affiliate", nullable=False),
        sa.Column("attribution_model", sa.String(length=40), server_default="last_eligible_touch", nullable=False),
        sa.Column("policy_version_id", uuid_type, nullable=True),
        sa.Column("commission_contract_id", uuid_type, nullable=True),
        sa.Column("source_host", sa.String(length=255), nullable=True),
        sa.Column("source_path", sa.String(length=500), nullable=True),
        sa.Column("destination_url", sa.String(length=1000), nullable=False),
        sa.Column("campaign_params", sa.JSON(), server_default=_json_default("{}"), nullable=False),
        sa.Column("evidence_payload", sa.JSON(), server_default=_json_default("{}"), nullable=False),
        sa.Column("policy_snapshot", sa.JSON(), server_default=_json_default("{}"), nullable=False),
        sa.Column("user_id", uuid_type, nullable=True),
        sa.Column("touchpoint_id", uuid_type, nullable=True),
        sa.Column("binding_id", uuid_type, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("transferred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["binding_id"], ["customer_commercial_bindings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_code_id"], ["partner_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["touchpoint_id"], ["attribution_touchpoints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_partner_attr_sessions_token_hash"),
        sa.UniqueConstraint("transfer_token_hash", name="uq_partner_attr_sessions_transfer_token_hash"),
    )
    for column in (
        "token_hash",
        "transfer_token_hash",
        "partner_code_id",
        "partner_account_id",
        "auth_realm_id",
        "storefront_id",
        "policy_version_id",
        "user_id",
        "touchpoint_id",
        "binding_id",
        "expires_at",
        "created_at",
    ):
        op.create_index(f"ix_partner_attr_sessions_{column}", "partner_attribution_sessions", [column])

    op.add_column("attribution_touchpoints", sa.Column("source_event_id", sa.String(length=120), nullable=True))
    op.add_column("attribution_touchpoints", sa.Column("idempotency_key", sa.String(length=160), nullable=True))
    op.add_column("attribution_touchpoints", sa.Column("partner_attribution_session_id", uuid_type, nullable=True))
    op.add_column("attribution_touchpoints", sa.Column("policy_version_id", uuid_type, nullable=True))
    op.create_foreign_key(
        "fk_attribution_touchpoints_partner_attr_session",
        "attribution_touchpoints",
        "partner_attribution_sessions",
        ["partner_attribution_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_attribution_touchpoints_policy_version",
        "attribution_touchpoints",
        "policy_versions",
        ["policy_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_attribution_touchpoints_source_event_id", "attribution_touchpoints", ["source_event_id"])
    op.create_index("ix_attribution_touchpoints_idempotency_key", "attribution_touchpoints", ["idempotency_key"])
    op.create_index(
        "ix_attribution_touchpoints_partner_attr_session_id",
        "attribution_touchpoints",
        ["partner_attribution_session_id"],
    )
    op.create_index("ix_attribution_touchpoints_policy_version_id", "attribution_touchpoints", ["policy_version_id"])

    op.add_column("customer_commercial_bindings", sa.Column("policy_version_id", uuid_type, nullable=True))
    op.add_column("customer_commercial_bindings", sa.Column("commission_contract_id", uuid_type, nullable=True))
    op.add_column("customer_commercial_bindings", sa.Column("attribution_session_id", uuid_type, nullable=True))
    op.add_column("customer_commercial_bindings", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "customer_commercial_bindings", sa.Column("version", sa.Integer(), server_default="1", nullable=False)
    )
    op.create_foreign_key(
        "fk_customer_commercial_bindings_policy_version",
        "customer_commercial_bindings",
        "policy_versions",
        ["policy_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_customer_commercial_bindings_partner_attr_session",
        "customer_commercial_bindings",
        "partner_attribution_sessions",
        ["attribution_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_customer_commercial_bindings_policy_version_id", "customer_commercial_bindings", ["policy_version_id"]
    )
    op.create_index(
        "ix_customer_commercial_bindings_commission_contract_id",
        "customer_commercial_bindings",
        ["commission_contract_id"],
    )
    op.create_index(
        "ix_customer_commercial_bindings_attribution_session_id",
        "customer_commercial_bindings",
        ["attribution_session_id"],
    )
    op.create_index("ix_customer_commercial_bindings_claimed_at", "customer_commercial_bindings", ["claimed_at"])

    op.add_column("order_attribution_results", sa.Column("attribution_session_id", uuid_type, nullable=True))
    op.add_column("order_attribution_results", sa.Column("policy_version_id", uuid_type, nullable=True))
    op.add_column("order_attribution_results", sa.Column("commission_contract_id", uuid_type, nullable=True))
    op.create_foreign_key(
        "fk_order_attribution_results_partner_attr_session",
        "order_attribution_results",
        "partner_attribution_sessions",
        ["attribution_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_order_attribution_results_policy_version",
        "order_attribution_results",
        "policy_versions",
        ["policy_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_order_attribution_results_attribution_session_id", "order_attribution_results", ["attribution_session_id"]
    )
    op.create_index(
        "ix_order_attribution_results_policy_version_id", "order_attribution_results", ["policy_version_id"]
    )
    op.create_index(
        "ix_order_attribution_results_commission_contract_id",
        "order_attribution_results",
        ["commission_contract_id"],
    )

    op.add_column("earning_events", sa.Column("source_event_id", sa.String(length=120), nullable=True))
    op.add_column("earning_events", sa.Column("source_event_key", sa.String(length=180), nullable=True))
    op.add_column("earning_events", sa.Column("policy_version_id", uuid_type, nullable=True))
    op.add_column("earning_events", sa.Column("commission_contract_id", uuid_type, nullable=True))
    op.add_column(
        "earning_events",
        sa.Column("calculation_snapshot", sa.JSON(), server_default=_json_default("{}"), nullable=False),
    )
    op.create_foreign_key(
        "fk_earning_events_policy_version",
        "earning_events",
        "policy_versions",
        ["policy_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_earning_events_source_event_id", "earning_events", ["source_event_id"])
    op.create_index("ix_earning_events_source_event_key", "earning_events", ["source_event_key"], unique=True)
    op.create_index("ix_earning_events_policy_version_id", "earning_events", ["policy_version_id"])
    op.create_index("ix_earning_events_commission_contract_id", "earning_events", ["commission_contract_id"])


def downgrade() -> None:
    op.drop_index("ix_earning_events_commission_contract_id", table_name="earning_events")
    op.drop_index("ix_earning_events_policy_version_id", table_name="earning_events")
    op.drop_index("ix_earning_events_source_event_key", table_name="earning_events")
    op.drop_index("ix_earning_events_source_event_id", table_name="earning_events")
    op.drop_constraint("fk_earning_events_policy_version", "earning_events", type_="foreignkey")
    op.drop_column("earning_events", "calculation_snapshot")
    op.drop_column("earning_events", "commission_contract_id")
    op.drop_column("earning_events", "policy_version_id")
    op.drop_column("earning_events", "source_event_key")
    op.drop_column("earning_events", "source_event_id")

    op.drop_index("ix_order_attribution_results_commission_contract_id", table_name="order_attribution_results")
    op.drop_index("ix_order_attribution_results_policy_version_id", table_name="order_attribution_results")
    op.drop_index("ix_order_attribution_results_attribution_session_id", table_name="order_attribution_results")
    op.drop_constraint("fk_order_attribution_results_policy_version", "order_attribution_results", type_="foreignkey")
    op.drop_constraint(
        "fk_order_attribution_results_partner_attr_session", "order_attribution_results", type_="foreignkey"
    )
    op.drop_column("order_attribution_results", "commission_contract_id")
    op.drop_column("order_attribution_results", "policy_version_id")
    op.drop_column("order_attribution_results", "attribution_session_id")

    op.drop_index("ix_customer_commercial_bindings_claimed_at", table_name="customer_commercial_bindings")
    op.drop_index("ix_customer_commercial_bindings_attribution_session_id", table_name="customer_commercial_bindings")
    op.drop_index("ix_customer_commercial_bindings_commission_contract_id", table_name="customer_commercial_bindings")
    op.drop_index("ix_customer_commercial_bindings_policy_version_id", table_name="customer_commercial_bindings")
    op.drop_constraint(
        "fk_customer_commercial_bindings_partner_attr_session", "customer_commercial_bindings", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_customer_commercial_bindings_policy_version", "customer_commercial_bindings", type_="foreignkey"
    )
    op.drop_column("customer_commercial_bindings", "version")
    op.drop_column("customer_commercial_bindings", "claimed_at")
    op.drop_column("customer_commercial_bindings", "attribution_session_id")
    op.drop_column("customer_commercial_bindings", "commission_contract_id")
    op.drop_column("customer_commercial_bindings", "policy_version_id")

    op.drop_index("ix_attribution_touchpoints_policy_version_id", table_name="attribution_touchpoints")
    op.drop_index("ix_attribution_touchpoints_partner_attr_session_id", table_name="attribution_touchpoints")
    op.drop_index("ix_attribution_touchpoints_idempotency_key", table_name="attribution_touchpoints")
    op.drop_index("ix_attribution_touchpoints_source_event_id", table_name="attribution_touchpoints")
    op.drop_constraint("fk_attribution_touchpoints_policy_version", "attribution_touchpoints", type_="foreignkey")
    op.drop_constraint("fk_attribution_touchpoints_partner_attr_session", "attribution_touchpoints", type_="foreignkey")
    op.drop_column("attribution_touchpoints", "policy_version_id")
    op.drop_column("attribution_touchpoints", "partner_attribution_session_id")
    op.drop_column("attribution_touchpoints", "idempotency_key")
    op.drop_column("attribution_touchpoints", "source_event_id")

    for column in (
        "created_at",
        "binding_id",
        "touchpoint_id",
        "user_id",
        "policy_version_id",
        "storefront_id",
        "auth_realm_id",
        "partner_account_id",
        "partner_code_id",
        "transfer_token_hash",
        "token_hash",
    ):
        op.drop_index(f"ix_partner_attr_sessions_{column}", table_name="partner_attribution_sessions")
    op.drop_table("partner_attribution_sessions")

    op.drop_constraint("ck_partner_codes_attribution_window_positive", "partner_codes", type_="check")
    op.drop_constraint("ck_partner_codes_markup_pct_nonnegative", "partner_codes", type_="check")
    op.drop_constraint("fk_partner_codes_updated_by_admin_user_id_admin_users", "partner_codes", type_="foreignkey")
    op.drop_constraint("fk_partner_codes_created_by_admin_user_id_admin_users", "partner_codes", type_="foreignkey")
    op.drop_constraint("fk_partner_codes_default_storefront_id_storefronts", "partner_codes", type_="foreignkey")
    op.drop_constraint("fk_partner_codes_policy_version_id_policy_versions", "partner_codes", type_="foreignkey")
    op.drop_index("ix_partner_codes_updated_by_admin_user_id", table_name="partner_codes")
    op.drop_index("ix_partner_codes_created_by_admin_user_id", table_name="partner_codes")
    op.drop_index("ix_partner_codes_expires_at", table_name="partner_codes")
    op.drop_index("ix_partner_codes_approval_status", table_name="partner_codes")
    op.drop_index("ix_partner_codes_default_storefront_id", table_name="partner_codes")
    op.drop_index("ix_partner_codes_policy_version_id", table_name="partner_codes")
    op.drop_index("ix_partner_codes_lane_key", table_name="partner_codes")
    op.drop_index("ix_partner_codes_owner_type", table_name="partner_codes")
    op.drop_index("ix_partner_codes_lifecycle_status", table_name="partner_codes")
    op.drop_index("ix_partner_codes_public_token_hash", table_name="partner_codes")
    op.drop_index("ix_partner_codes_code_normalized", table_name="partner_codes")

    for column in (
        "version",
        "updated_by_admin_user_id",
        "created_by_admin_user_id",
        "revoked_at",
        "paused_at",
        "expires_at",
        "active_from",
        "approval_status",
        "sub_id_schema",
        "allowed_geographies",
        "allowed_storefront_ids",
        "allowed_channels",
        "destination_path",
        "default_storefront_id",
        "policy_version_id",
        "commission_contract_id",
        "attribution_window_seconds",
        "attribution_model",
        "lane_key",
        "owner_type",
        "lifecycle_status",
        "code_kind",
        "public_token_hash",
        "code_normalized",
    ):
        op.drop_column("partner_codes", column)
