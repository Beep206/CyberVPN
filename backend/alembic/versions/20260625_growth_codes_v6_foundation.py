"""Growth Codes v6 foundation schema.

Revision ID: 20260625_growth_v6_foundation
Revises: 20260625_referral_claim_unique
Create Date: 2026-06-25
"""

from __future__ import annotations

import hashlib
import hmac
import os
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from typing import NamedTuple

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260625_growth_v6_foundation"
down_revision: str | Sequence[str] | None = "20260625_referral_claim_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class _LegacyCodeSource(NamedTuple):
    code_type: str
    legacy_source_type: str
    source_id: object | None
    normalized_code: str
    normalized_code_hash: str
    status: str
    created_at: object | None


_LEGACY_CODE_SOURCE_SPECS: tuple[tuple[str, str, str, str], ...] = (
    ("promo_codes", "code", "promo", "legacy_promo"),
    ("invite_codes", "code", "invite", "legacy_invite"),
    ("gift_codes", "code", "gift", "legacy_gift"),
    ("mobile_users", "referral_code", "referral", "legacy_referral"),
    ("partner_codes", "code", "partner", "legacy_partner"),
    ("partner_codes", "public_slug", "partner", "legacy_partner_slug"),
    ("partner_code_links", "public_slug", "partner", "legacy_partner_link"),
)


def upgrade() -> None:
    bind = op.get_bind()
    json_type = _json_type(bind)
    _assert_no_growth_code_namespace_collisions(bind)
    _assert_no_duplicate_promo_payment_usages(bind)
    _assert_invite_plan_ids_resolve(bind)

    op.create_table(
        "growth_campaigns",
        _uuid_col("id", nullable=False),
        sa.Column("campaign_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stacking_mode", sa.String(length=30), nullable=False, server_default="exclusive"),
        sa.Column("stacking_group", sa.String(length=80), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        _uuid_col("created_by_admin_id", nullable=False),
        _uuid_col("updated_by_admin_id", nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        _created_at_col(),
        _updated_at_col(),
        sa.CheckConstraint(
            "expires_at IS NULL OR starts_at IS NULL OR expires_at > starts_at",
            name="ck_growth_campaigns_valid_window",
        ),
        sa.CheckConstraint("priority >= 0", name="ck_growth_campaigns_priority_non_negative"),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["admin_users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_key", name="uq_growth_campaigns_campaign_key"),
    )
    _create_indexes(
        "growth_campaigns",
        ("campaign_key", "status", "created_by_admin_id", "updated_by_admin_id"),
    )
    op.create_index(
        "ix_growth_campaigns_status_schedule",
        "growth_campaigns",
        ["status", "starts_at", "expires_at"],
    )

    with op.batch_alter_table("growth_codes") as batch_op:
        batch_op.add_column(sa.Column("reserved_uses", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column("code_namespace", sa.String(length=40), nullable=False, server_default="customer_input")
        )
        batch_op.create_foreign_key(
            "fk_growth_codes_campaign_id_growth_campaigns",
            "growth_campaigns",
            ["campaign_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_check_constraint("ck_growth_codes_uses_count_non_negative", "uses_count >= 0")
        batch_op.create_check_constraint("ck_growth_codes_reserved_uses_non_negative", "reserved_uses >= 0")
        batch_op.create_check_constraint(
            "ck_growth_codes_uses_lte_max",
            "max_uses IS NULL OR uses_count <= max_uses",
        )
        batch_op.create_check_constraint(
            "ck_growth_codes_reserved_plus_uses_lte_max",
            "max_uses IS NULL OR uses_count + reserved_uses <= max_uses",
        )
        batch_op.create_unique_constraint("uq_growth_codes_namespace_hash", ["code_namespace", "code_hash"])
        batch_op.create_index("ix_growth_codes_last_used_at", ["last_used_at"])
        batch_op.create_index("ix_growth_codes_code_namespace", ["code_namespace"])
    op.create_index("ix_growth_codes_campaign_status", "growth_codes", ["campaign_id", "status"])

    with op.batch_alter_table("promo_code_policies") as batch_op:
        batch_op.add_column(sa.Column("currency_code", sa.String(length=12), nullable=True))
        batch_op.add_column(sa.Column("discount_scope", sa.String(length=30), nullable=False, server_default="order"))
        batch_op.add_column(_json_col("discountable_addon_codes", json_type, bind, default="[]"))
        batch_op.add_column(sa.Column("minimum_order_amount", sa.Numeric(20, 8), nullable=True))
        batch_op.add_column(
            sa.Column("allow_zero_amount_order", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("new_customer_only", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(
            sa.Column("first_completed_order_only", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("first_net_paid_order_only", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("require_no_active_access", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("commission_basis", sa.String(length=30), nullable=False, server_default="net_gateway_paid")
        )
        batch_op.add_column(
            sa.Column("include_wallet_in_commission_base", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_check_constraint(
            "ck_promo_code_policies_commission_basis",
            "commission_basis IN ('none', 'net_gateway_paid', 'net_customer_paid', 'base_price')",
        )
        batch_op.create_check_constraint(
            "ck_promo_code_policies_minimum_order_non_negative",
            "minimum_order_amount IS NULL OR minimum_order_amount >= 0",
        )

    op.create_table(
        "growth_code_benefits",
        _uuid_col("id", nullable=False),
        _uuid_col("growth_code_id", nullable=False),
        _uuid_col("policy_version_id", nullable=True),
        sa.Column("benefit_type", sa.String(length=40), nullable=False),
        sa.Column("trigger_type", sa.String(length=40), nullable=False),
        sa.Column("merge_mode", sa.String(length=30), nullable=False, server_default="append"),
        _json_col("config", json_type, bind),
        _json_col("eligibility", json_type, bind),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _created_at_col(),
        _updated_at_col(),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_indexes(
        "growth_code_benefits",
        ("growth_code_id", "policy_version_id", "benefit_type", "trigger_type"),
    )

    op.create_table(
        "growth_benefit_fulfillments",
        _uuid_col("id", nullable=False),
        _uuid_col("benefit_id", nullable=False),
        _uuid_col("growth_code_id", nullable=False),
        _uuid_col("user_id", nullable=False),
        _uuid_col("order_id", nullable=False),
        _uuid_col("payment_id", nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        _json_col("config_snapshot", json_type, bind),
        _json_col("result_payload", json_type, bind),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        _created_at_col(),
        _updated_at_col(),
        sa.CheckConstraint("attempt_count >= 0", name="ck_growth_benefit_fulfillments_attempt_count_non_negative"),
        sa.ForeignKeyConstraint(["benefit_id"], ["growth_code_benefits.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_growth_benefit_fulfillments_idempotency_key"),
    )
    _create_indexes(
        "growth_benefit_fulfillments",
        (
            "benefit_id",
            "growth_code_id",
            "user_id",
            "order_id",
            "payment_id",
            "idempotency_key",
            "status",
            "next_retry_at",
        ),
    )
    op.create_index(
        "ix_growth_fulfillments_status_retry",
        "growth_benefit_fulfillments",
        ["status", "next_retry_at"],
    )

    op.create_table(
        "invite_batches",
        _uuid_col("id", nullable=False),
        _uuid_col("owner_user_id", nullable=False),
        _uuid_col("campaign_id", nullable=True),
        _uuid_col("source_growth_code_id", nullable=True),
        _uuid_col("source_benefit_id", nullable=True),
        _uuid_col("source_order_id", nullable=True),
        _uuid_col("source_payment_id", nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("requested_count", sa.Integer(), nullable=False),
        sa.Column("issued_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("friend_days", sa.Integer(), nullable=False),
        sa.Column("expiry_mode", sa.String(length=20), nullable=False),
        sa.Column("expiry_days", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entitlement_mode", sa.String(length=30), nullable=False),
        sa.Column("entitlement_profile_key", sa.String(length=80), nullable=True),
        _uuid_col("plan_id", nullable=True),
        _json_col("entitlement_snapshot", json_type, bind),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        _uuid_col("revoked_by_admin_id", nullable=True),
        sa.Column("revoked_reason", sa.String(length=120), nullable=True),
        _created_at_col(),
        _updated_at_col(),
        sa.CheckConstraint("requested_count > 0", name="ck_invite_batches_requested_count_positive"),
        sa.CheckConstraint("issued_count >= 0", name="ck_invite_batches_issued_count_non_negative"),
        sa.CheckConstraint("issued_count <= requested_count", name="ck_invite_batches_issued_lte_requested"),
        sa.CheckConstraint("friend_days > 0", name="ck_invite_batches_friend_days_positive"),
        sa.CheckConstraint(
            "expiry_mode IN ('none', 'relative', 'absolute')",
            name="ck_invite_batches_expiry_mode",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["mobile_users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["campaign_id"], ["growth_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_growth_code_id"], ["growth_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_benefit_id"], ["growth_code_benefits.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["revoked_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_invite_batches_idempotency_key"),
    )
    _create_indexes(
        "invite_batches",
        (
            "owner_user_id",
            "campaign_id",
            "source_growth_code_id",
            "source_benefit_id",
            "source_order_id",
            "source_payment_id",
            "source_type",
            "plan_id",
            "status",
            "revoked_by_admin_id",
        ),
    )
    op.create_index("ix_invite_batches_owner_created", "invite_batches", ["owner_user_id", sa.text("created_at DESC")])

    with op.batch_alter_table("invite_codes") as batch_op:
        batch_op.add_column(_uuid_col("batch_id", nullable=True))
        batch_op.add_column(_uuid_col("source_growth_code_id", nullable=True))
        batch_op.add_column(_uuid_col("source_benefit_id", nullable=True))
        batch_op.add_column(sa.Column("status", sa.String(length=20), nullable=False, server_default="issued"))
        batch_op.add_column(sa.Column("code_hash", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("code_prefix", sa.String(length=12), nullable=True))
        batch_op.add_column(sa.Column("entitlement_mode", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("entitlement_profile_key", sa.String(length=80), nullable=True))
        batch_op.add_column(_json_col("entitlement_snapshot", json_type, bind))
        batch_op.add_column(sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(_uuid_col("revoked_by_admin_id", nullable=True))
        batch_op.add_column(sa.Column("revoked_reason", sa.String(length=120), nullable=True))
        batch_op.create_foreign_key(
            "fk_invite_codes_plan_id_subscription_plans",
            "subscription_plans",
            ["plan_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_codes_batch_id_invite_batches",
            "invite_batches",
            ["batch_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_codes_source_growth_code_id_growth_codes",
            "growth_codes",
            ["source_growth_code_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_codes_source_benefit_id_growth_code_benefits",
            "growth_code_benefits",
            ["source_benefit_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_codes_revoked_by_admin_id_admin_users",
            "admin_users",
            ["revoked_by_admin_id"],
            ["id"],
            ondelete="SET NULL",
        )
        for index_name, columns in (
            ("ix_invite_codes_batch_id", ["batch_id"]),
            ("ix_invite_codes_source_growth_code_id", ["source_growth_code_id"]),
            ("ix_invite_codes_source_benefit_id", ["source_benefit_id"]),
            ("ix_invite_codes_status", ["status"]),
            ("ix_invite_codes_code_hash", ["code_hash"]),
            ("ix_invite_codes_code_prefix", ["code_prefix"]),
        ):
            batch_op.create_index(index_name, columns)
    op.create_index("ix_invite_codes_batch_status", "invite_codes", ["batch_id", "status"])

    op.create_table(
        "growth_code_user_counters",
        _uuid_col("growth_code_id", nullable=False),
        _uuid_col("user_id", nullable=False),
        sa.Column("reserved_uses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_uses", sa.Integer(), nullable=False, server_default="0"),
        _created_at_col(),
        _updated_at_col(),
        sa.CheckConstraint("reserved_uses >= 0", name="ck_growth_code_user_counters_reserved_non_negative"),
        sa.CheckConstraint("consumed_uses >= 0", name="ck_growth_code_user_counters_consumed_non_negative"),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("growth_code_id", "user_id", name="pk_growth_code_user_counters"),
    )

    op.create_table(
        "growth_rule_catalog_versions",
        _uuid_col("id", nullable=False),
        sa.Column("catalog_version", sa.String(length=40), nullable=False),
        _json_col("fields_schema", json_type, bind),
        _json_col("operators_schema", json_type, bind),
        _json_col("actions_schema", json_type, bind),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        _created_at_col(),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("catalog_version", name="uq_growth_rule_catalog_versions_catalog_version"),
    )
    _create_indexes("growth_rule_catalog_versions", ("status",))

    op.create_table(
        "growth_rule_definitions",
        _uuid_col("id", nullable=False),
        _uuid_col("policy_version_id", nullable=False),
        _uuid_col("catalog_version_id", nullable=True),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        _json_col("ast_payload", json_type, bind),
        _json_col("compiled_plan_payload", json_type, bind),
        sa.Column("compiled_checksum", sa.String(length=128), nullable=False),
        sa.Column("complexity_score", sa.Integer(), nullable=False),
        sa.Column("node_count", sa.Integer(), nullable=False),
        sa.Column("max_depth", sa.Integer(), nullable=False),
        sa.Column("validation_status", sa.String(length=20), nullable=False),
        _json_col("validation_errors", json_type, bind),
        sa.Column("compiled_at", sa.DateTime(timezone=True), nullable=True),
        _created_at_col(),
        _updated_at_col(),
        sa.CheckConstraint("complexity_score >= 0", name="ck_growth_rule_definitions_complexity_non_negative"),
        sa.CheckConstraint("node_count >= 0", name="ck_growth_rule_definitions_node_count_non_negative"),
        sa.CheckConstraint("max_depth >= 0", name="ck_growth_rule_definitions_max_depth_non_negative"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["catalog_version_id"], ["growth_rule_catalog_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_version_id", name="uq_growth_rule_definitions_policy_version_id"),
    )
    _create_indexes("growth_rule_definitions", ("policy_version_id", "catalog_version_id", "validation_status"))

    op.create_table(
        "growth_private_catalog_policies",
        _uuid_col("id", nullable=False),
        _uuid_col("policy_version_id", nullable=False),
        _uuid_col("growth_code_id", nullable=False),
        sa.Column("unlock_mode", sa.String(length=30), nullable=False),
        _json_col("target_plan_ids", json_type, bind, default="[]"),
        _json_col("target_offer_ids", json_type, bind, default="[]"),
        _json_col("target_offer_keys", json_type, bind, default="[]"),
        _uuid_col("auto_select_target_id", nullable=True),
        _json_col("allowed_storefront_ids", json_type, bind, default="[]"),
        _json_col("allowed_channels", json_type, bind, default="[]"),
        sa.Column("grant_ttl_seconds", sa.Integer(), nullable=False),
        sa.Column("max_quote_conversions", sa.Integer(), nullable=True),
        sa.Column("consume_mode", sa.String(length=30), nullable=False),
        sa.Column("requires_auth", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("requires_risk_action_below", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _created_at_col(),
        _updated_at_col(),
        sa.CheckConstraint("grant_ttl_seconds > 0", name="ck_growth_private_catalog_policies_grant_ttl_positive"),
        sa.CheckConstraint(
            "max_quote_conversions IS NULL OR max_quote_conversions >= 0",
            name="ck_growth_private_catalog_policies_max_quote_conversions",
        ),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_indexes(
        "growth_private_catalog_policies",
        ("policy_version_id", "growth_code_id", "is_active"),
    )

    op.create_table(
        "private_catalog_access_grants",
        _uuid_col("id", nullable=False),
        _uuid_col("policy_id", nullable=False),
        _uuid_col("policy_version_id", nullable=False),
        _uuid_col("growth_code_id", nullable=False),
        sa.Column("code_set_hash", sa.String(length=128), nullable=False),
        sa.Column("grant_token_hash", sa.String(length=128), nullable=True),
        _uuid_col("user_id", nullable=True),
        sa.Column("anonymous_session_id", sa.String(length=120), nullable=True),
        _uuid_col("risk_subject_id", nullable=True),
        _uuid_col("auth_realm_id", nullable=False),
        _uuid_col("storefront_id", nullable=False),
        sa.Column("sale_channel", sa.String(length=30), nullable=False),
        _json_col("allowed_plan_ids", json_type, bind, default="[]"),
        _json_col("allowed_offer_ids", json_type, bind, default="[]"),
        _uuid_col("risk_decision_id", nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("max_quote_conversions", sa.Integer(), nullable=True),
        sa.Column("quote_conversions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        _uuid_col("attached_quote_session_id", nullable=True),
        _uuid_col("attached_checkout_session_id", nullable=True),
        _uuid_col("consumed_order_id", nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=120), nullable=True),
        _json_col("metadata", json_type, bind),
        _created_at_col(),
        _updated_at_col(),
        sa.CheckConstraint(
            "user_id IS NOT NULL OR anonymous_session_id IS NOT NULL",
            name="ck_private_catalog_access_grants_subject_present",
        ),
        sa.CheckConstraint(
            "quote_conversions_count >= 0",
            name="ck_private_catalog_access_grants_quote_conversions_non_negative",
        ),
        sa.CheckConstraint(
            "max_quote_conversions IS NULL OR quote_conversions_count <= max_quote_conversions",
            name="ck_private_catalog_access_grants_quote_conversions_lte_max",
        ),
        sa.ForeignKeyConstraint(["policy_id"], ["growth_private_catalog_policies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["risk_subject_id"], ["risk_subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["attached_quote_session_id"], ["quote_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["attached_checkout_session_id"], ["checkout_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["consumed_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grant_token_hash", name="uq_private_catalog_access_grants_grant_token_hash"),
    )
    _create_indexes(
        "private_catalog_access_grants",
        (
            "policy_id",
            "policy_version_id",
            "growth_code_id",
            "code_set_hash",
            "grant_token_hash",
            "user_id",
            "anonymous_session_id",
            "risk_subject_id",
            "auth_realm_id",
            "storefront_id",
            "sale_channel",
            "status",
            "expires_at",
            "attached_quote_session_id",
            "attached_checkout_session_id",
            "consumed_order_id",
        ),
    )

    op.create_table(
        "checkout_code_sets",
        _uuid_col("id", nullable=False),
        sa.Column("code_set_hash", sa.String(length=128), nullable=False),
        _uuid_col("user_id", nullable=True),
        sa.Column("anonymous_session_id", sa.String(length=120), nullable=True),
        _uuid_col("auth_realm_id", nullable=False),
        _uuid_col("storefront_id", nullable=True),
        sa.Column("sale_channel", sa.String(length=30), nullable=False),
        sa.Column("action_context", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("acceptance_mode", sa.String(length=24), nullable=False),
        _json_col("aggregate_result", json_type, bind),
        _json_col("risk_snapshot", json_type, bind),
        _uuid_col("private_access_grant_id", nullable=True),
        _uuid_col("quote_session_id", nullable=True),
        _uuid_col("checkout_session_id", nullable=True),
        _uuid_col("order_id", nullable=True),
        _uuid_col("payment_id", nullable=True),
        _created_at_col(),
        _updated_at_col(),
        sa.CheckConstraint(
            "user_id IS NOT NULL OR anonymous_session_id IS NOT NULL",
            name="ck_checkout_code_sets_subject_present",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["private_access_grant_id"], ["private_catalog_access_grants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["quote_session_id"], ["quote_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["checkout_session_id"], ["checkout_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_indexes(
        "checkout_code_sets",
        (
            "code_set_hash",
            "user_id",
            "anonymous_session_id",
            "auth_realm_id",
            "storefront_id",
            "sale_channel",
            "action_context",
            "status",
            "private_access_grant_id",
            "quote_session_id",
            "checkout_session_id",
            "order_id",
            "payment_id",
        ),
    )

    op.create_table(
        "checkout_code_applications",
        _uuid_col("id", nullable=False),
        _uuid_col("code_set_id", nullable=False),
        sa.Column("position_entered", sa.Integer(), nullable=False),
        sa.Column("canonical_order", sa.Integer(), nullable=False),
        _uuid_col("growth_code_id", nullable=True),
        sa.Column("legacy_code_type", sa.String(length=20), nullable=True),
        _uuid_col("legacy_code_id", nullable=True),
        sa.Column("masked_code", sa.String(length=32), nullable=False),
        _json_col("roles", json_type, bind),
        sa.Column("resolution_status", sa.String(length=24), nullable=False),
        sa.Column("reject_reason", sa.String(length=80), nullable=True),
        sa.Column("conflict_code", sa.String(length=80), nullable=True),
        _uuid_col("policy_version_id", nullable=True),
        _uuid_col("rule_definition_id", nullable=True),
        _uuid_col("risk_decision_id", nullable=True),
        _uuid_col("fx_conversion_id", nullable=True),
        _uuid_col("reservation_id", nullable=True),
        _json_col("discount_snapshot", json_type, bind),
        _json_col("benefits_snapshot", json_type, bind),
        _json_col("private_access_snapshot", json_type, bind),
        _json_col("evaluation_trace", json_type, bind),
        _created_at_col(),
        _updated_at_col(),
        sa.CheckConstraint("position_entered >= 0", name="ck_checkout_code_applications_position_non_negative"),
        sa.CheckConstraint("canonical_order >= 0", name="ck_checkout_code_applications_canonical_order_non_negative"),
        sa.ForeignKeyConstraint(["code_set_id"], ["checkout_code_sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rule_definition_id"], ["growth_rule_definitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reservation_id"], ["growth_code_reservations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_set_id", "growth_code_id", name="uq_checkout_code_applications_code_set_growth_code"),
    )
    _create_indexes(
        "checkout_code_applications",
        (
            "code_set_id",
            "growth_code_id",
            "legacy_code_id",
            "resolution_status",
            "reject_reason",
            "policy_version_id",
            "rule_definition_id",
            "risk_decision_id",
            "fx_conversion_id",
            "reservation_id",
        ),
    )

    op.create_table(
        "growth_code_reservation_groups",
        _uuid_col("id", nullable=False),
        _uuid_col("code_set_id", nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        _uuid_col("user_id", nullable=True),
        _uuid_col("quote_session_id", nullable=True),
        _uuid_col("checkout_session_id", nullable=True),
        _uuid_col("order_id", nullable=True),
        _uuid_col("payment_id", nullable=True),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_reason", sa.String(length=80), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        _created_at_col(),
        _updated_at_col(),
        sa.ForeignKeyConstraint(["code_set_id"], ["checkout_code_sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["quote_session_id"], ["quote_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["checkout_session_id"], ["checkout_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_growth_code_reservation_groups_idempotency_key"),
    )
    _create_indexes(
        "growth_code_reservation_groups",
        (
            "code_set_id",
            "status",
            "user_id",
            "quote_session_id",
            "checkout_session_id",
            "order_id",
            "payment_id",
            "reserved_at",
            "expires_at",
        ),
    )

    with op.batch_alter_table("growth_code_reservations") as batch_op:
        batch_op.add_column(_uuid_col("reservation_group_id", nullable=True))
        batch_op.add_column(sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(_uuid_col("consumed_payment_id", nullable=True))
        batch_op.create_foreign_key(
            "fk_growth_code_reservations_reservation_group_id",
            "growth_code_reservation_groups",
            ["reservation_group_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_growth_code_reservations_consumed_payment_id",
            "payments",
            ["consumed_payment_id"],
            ["id"],
            ondelete="SET NULL",
        )
        for index_name, columns in (
            ("ix_growth_code_reservations_reservation_group_id", ["reservation_group_id"]),
            ("ix_growth_code_reservations_committed_at", ["committed_at"]),
            ("ix_growth_code_reservations_consumed_at", ["consumed_at"]),
            ("ix_growth_code_reservations_consumed_payment_id", ["consumed_payment_id"]),
        ):
            batch_op.create_index(index_name, columns)
    op.create_index(
        "ix_growth_reservations_code_status_expiry",
        "growth_code_reservations",
        ["growth_code_id", "status", "expires_at"],
    )

    with op.batch_alter_table("growth_code_redemptions") as batch_op:
        batch_op.add_column(_uuid_col("payment_id", nullable=True))
        batch_op.add_column(_uuid_col("reservation_id", nullable=True))
        batch_op.add_column(sa.Column("usage_number", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_growth_code_redemptions_payment_id",
            "payments",
            ["payment_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_growth_code_redemptions_reservation_id",
            "growth_code_reservations",
            ["reservation_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_growth_code_redemptions_payment_id", ["payment_id"])
        batch_op.create_index("ix_growth_code_redemptions_reservation_id", ["reservation_id"])

    with op.batch_alter_table("promo_code_usages") as batch_op:
        batch_op.create_foreign_key(
            "fk_promo_code_usages_payment_id_payments",
            "payments",
            ["payment_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint("uq_promo_code_usages_promo_payment", ["promo_code_id", "payment_id"])

    op.create_table(
        "order_code_applications",
        _uuid_col("id", nullable=False),
        _uuid_col("order_id", nullable=False),
        _uuid_col("code_set_id", nullable=False),
        _uuid_col("growth_code_id", nullable=False),
        _uuid_col("policy_version_id", nullable=True),
        sa.Column("application_role", sa.String(length=30), nullable=False),
        sa.Column("application_status", sa.String(length=24), nullable=False),
        sa.Column("discount_amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("currency_code", sa.String(length=12), nullable=False),
        sa.Column("source_amount", sa.Numeric(20, 8), nullable=True),
        sa.Column("source_currency_code", sa.String(length=12), nullable=True),
        _uuid_col("fx_conversion_id", nullable=True),
        _uuid_col("reservation_id", nullable=True),
        _uuid_col("risk_decision_id", nullable=True),
        _json_col("application_snapshot", json_type, bind),
        _created_at_col(),
        sa.CheckConstraint("discount_amount >= 0", name="ck_order_code_applications_discount_non_negative"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["code_set_id"], ["checkout_code_sets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reservation_id"], ["growth_code_reservations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "growth_code_id", name="uq_order_code_applications_order_growth_code"),
    )
    _create_indexes(
        "order_code_applications",
        (
            "order_id",
            "code_set_id",
            "growth_code_id",
            "policy_version_id",
            "application_role",
            "application_status",
            "fx_conversion_id",
            "reservation_id",
            "risk_decision_id",
        ),
    )

    op.create_table(
        "risk_model_versions",
        _uuid_col("id", nullable=False),
        sa.Column("model_key", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("artifact_uri", sa.Text(), nullable=False),
        sa.Column("artifact_checksum", sa.String(length=128), nullable=False),
        sa.Column("feature_schema_version", sa.String(length=60), nullable=False),
        sa.Column("model_type", sa.String(length=40), nullable=False),
        sa.Column("training_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("training_window_end", sa.DateTime(timezone=True), nullable=True),
        _json_col("metrics", json_type, bind),
        _json_col("calibration", json_type, bind),
        sa.Column("deployment_mode", sa.String(length=20), nullable=False),
        sa.Column("approval_state", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        _uuid_col("created_by", nullable=True),
        _uuid_col("approved_by", nullable=True),
        _created_at_col(),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_key", "version", name="uq_risk_model_versions_model_key_version"),
    )
    _create_indexes(
        "risk_model_versions",
        ("model_key", "deployment_mode", "approval_state", "status", "created_by", "approved_by"),
    )

    op.create_table(
        "risk_feature_snapshots",
        _uuid_col("id", nullable=False),
        _uuid_col("risk_subject_id", nullable=False),
        sa.Column("feature_schema_version", sa.String(length=60), nullable=False),
        _json_col("features_payload", json_type, bind),
        sa.Column("feature_hash", sa.String(length=128), nullable=False),
        _json_col("source_freshness", json_type, bind),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        _created_at_col(),
        sa.ForeignKeyConstraint(["risk_subject_id"], ["risk_subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feature_hash", name="uq_risk_feature_snapshots_feature_hash"),
    )
    _create_indexes("risk_feature_snapshots", ("risk_subject_id", "feature_hash", "generated_at", "expires_at"))

    op.create_table(
        "growth_risk_decisions",
        _uuid_col("id", nullable=False),
        _uuid_col("risk_subject_id", nullable=False),
        _uuid_col("code_set_id", nullable=True),
        _uuid_col("growth_code_id", nullable=True),
        _uuid_col("private_grant_id", nullable=True),
        _uuid_col("quote_session_id", nullable=True),
        _uuid_col("order_id", nullable=True),
        sa.Column("action_context", sa.String(length=30), nullable=False),
        _uuid_col("rules_policy_version_id", nullable=False),
        _uuid_col("model_version_id", nullable=True),
        _uuid_col("feature_snapshot_id", nullable=True),
        sa.Column("rules_outcome", sa.String(length=20), nullable=False),
        sa.Column("ml_score", sa.Numeric(8, 6), nullable=True),
        sa.Column("risk_band", sa.String(length=20), nullable=False),
        sa.Column("final_action", sa.String(length=20), nullable=False),
        _json_col("reason_codes", json_type, bind, default="[]"),
        sa.Column("fallback_mode", sa.String(length=30), nullable=True),
        _json_col("decision_trace", json_type, bind),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        _created_at_col(),
        sa.CheckConstraint(
            "ml_score IS NULL OR (ml_score >= 0 AND ml_score <= 1)",
            name="ck_growth_risk_decisions_score",
        ),
        sa.ForeignKeyConstraint(["risk_subject_id"], ["risk_subjects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["code_set_id"], ["checkout_code_sets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["private_grant_id"], ["private_catalog_access_grants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["quote_session_id"], ["quote_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rules_policy_version_id"], ["policy_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["model_version_id"], ["risk_model_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["feature_snapshot_id"], ["risk_feature_snapshots.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_indexes(
        "growth_risk_decisions",
        (
            "risk_subject_id",
            "code_set_id",
            "growth_code_id",
            "private_grant_id",
            "quote_session_id",
            "order_id",
            "action_context",
            "rules_policy_version_id",
            "model_version_id",
            "feature_snapshot_id",
            "risk_band",
            "final_action",
            "decided_at",
        ),
    )

    op.create_table(
        "fx_rate_snapshots",
        _uuid_col("id", nullable=False),
        sa.Column("base_currency", sa.String(length=12), nullable=False),
        sa.Column("quote_currency", sa.String(length=12), nullable=False),
        sa.Column("rate", sa.Numeric(30, 14), nullable=False),
        sa.Column("inverse_rate", sa.Numeric(30, 14), nullable=True),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("provider_key", sa.String(length=80), nullable=False),
        sa.Column("provider_rate_id", sa.String(length=160), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        _json_col("metadata", json_type, bind),
        _created_at_col(),
        sa.CheckConstraint("rate > 0", name="ck_fx_rate_snapshots_rate_positive"),
        sa.CheckConstraint("inverse_rate IS NULL OR inverse_rate > 0", name="ck_fx_rate_snapshots_inverse_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "base_currency",
            "quote_currency",
            "source_type",
            "provider_key",
            "observed_at",
            name="uq_fx_rate_snapshots_pair_provider_observed",
        ),
    )
    _create_indexes(
        "fx_rate_snapshots",
        ("base_currency", "quote_currency", "provider_key", "observed_at", "valid_until", "status"),
    )

    op.create_table(
        "fx_discount_conversions",
        _uuid_col("id", nullable=False),
        _uuid_col("code_application_id", nullable=True),
        _uuid_col("growth_code_id", nullable=False),
        _uuid_col("policy_version_id", nullable=False),
        sa.Column("source_amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("source_currency", sa.String(length=12), nullable=False),
        sa.Column("target_currency", sa.String(length=12), nullable=False),
        sa.Column("conversion_mode", sa.String(length=30), nullable=False),
        _uuid_col("fx_rate_snapshot_id", nullable=True),
        sa.Column("configured_rate_version", sa.String(length=80), nullable=True),
        sa.Column("raw_converted_amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("rounded_amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("applied_amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("target_minor_units", sa.Integer(), nullable=False),
        sa.Column("rounding_mode", sa.String(length=30), nullable=False),
        _created_at_col(),
        sa.CheckConstraint("source_amount >= 0", name="ck_fx_discount_conversions_source_non_negative"),
        sa.CheckConstraint("raw_converted_amount >= 0", name="ck_fx_discount_conversions_raw_non_negative"),
        sa.CheckConstraint("rounded_amount >= 0", name="ck_fx_discount_conversions_rounded_non_negative"),
        sa.CheckConstraint("applied_amount >= 0", name="ck_fx_discount_conversions_applied_non_negative"),
        sa.CheckConstraint("target_minor_units >= 0", name="ck_fx_discount_conversions_minor_units_non_negative"),
        sa.ForeignKeyConstraint(["code_application_id"], ["checkout_code_applications.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["fx_rate_snapshot_id"], ["fx_rate_snapshots.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_indexes(
        "fx_discount_conversions",
        ("code_application_id", "growth_code_id", "policy_version_id", "fx_rate_snapshot_id"),
    )

    op.create_table(
        "growth_code_namespaces",
        sa.Column("normalized_code_hash", sa.String(length=128), nullable=False),
        _uuid_col("canonical_growth_code_id", nullable=True),
        sa.Column("code_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("legacy_source_type", sa.String(length=30), nullable=True),
        _uuid_col("legacy_source_id", nullable=True),
        _created_at_col(),
        sa.ForeignKeyConstraint(["canonical_growth_code_id"], ["growth_codes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("normalized_code_hash"),
    )
    _create_indexes(
        "growth_code_namespaces",
        ("canonical_growth_code_id", "code_type", "status", "legacy_source_type", "legacy_source_id"),
    )
    _backfill_growth_code_namespaces(bind)

    with op.batch_alter_table("quote_sessions") as batch_op:
        batch_op.add_column(_uuid_col("code_set_id", nullable=True))
        batch_op.add_column(_uuid_col("private_catalog_access_grant_id", nullable=True))
        batch_op.create_foreign_key(
            "fk_quote_sessions_code_set_id_checkout_code_sets",
            "checkout_code_sets",
            ["code_set_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_quote_sessions_private_catalog_access_grant_id",
            "private_catalog_access_grants",
            ["private_catalog_access_grant_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_quote_sessions_code_set_id", ["code_set_id"])
        batch_op.create_index("ix_quote_sessions_private_catalog_access_grant_id", ["private_catalog_access_grant_id"])

    with op.batch_alter_table("checkout_sessions") as batch_op:
        batch_op.add_column(_uuid_col("code_set_id", nullable=True))
        batch_op.add_column(_uuid_col("private_catalog_access_grant_id", nullable=True))
        batch_op.create_foreign_key(
            "fk_checkout_sessions_code_set_id_checkout_code_sets",
            "checkout_code_sets",
            ["code_set_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_checkout_sessions_private_catalog_access_grant_id",
            "private_catalog_access_grants",
            ["private_catalog_access_grant_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_checkout_sessions_code_set_id", ["code_set_id"])
        batch_op.create_index(
            "ix_checkout_sessions_private_catalog_access_grant_id",
            ["private_catalog_access_grant_id"],
        )

    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(_uuid_col("code_set_id", nullable=True))
        batch_op.add_column(_uuid_col("private_catalog_access_grant_id", nullable=True))
        batch_op.add_column(_json_col("risk_snapshot", json_type, bind))
        batch_op.add_column(_json_col("fx_snapshot", json_type, bind))
        batch_op.create_foreign_key(
            "fk_orders_code_set_id_checkout_code_sets",
            "checkout_code_sets",
            ["code_set_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_orders_private_catalog_access_grant_id",
            "private_catalog_access_grants",
            ["private_catalog_access_grant_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_orders_code_set_id", ["code_set_id"])
        batch_op.create_index("ix_orders_private_catalog_access_grant_id", ["private_catalog_access_grant_id"])

    with op.batch_alter_table("payments") as batch_op:
        batch_op.add_column(_uuid_col("code_set_id", nullable=True))
        batch_op.add_column(sa.Column("growth_snapshot", sa.JSON(), nullable=True))
        batch_op.create_foreign_key(
            "fk_payments_code_set_id_checkout_code_sets",
            "checkout_code_sets",
            ["code_set_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_payments_code_set_id", ["code_set_id"])

    with op.batch_alter_table("payment_attempts") as batch_op:
        batch_op.add_column(_uuid_col("code_set_id", nullable=True))
        batch_op.create_foreign_key(
            "fk_payment_attempts_code_set_id_checkout_code_sets",
            "checkout_code_sets",
            ["code_set_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_payment_attempts_code_set_id", ["code_set_id"])

    with op.batch_alter_table("subscription_plans") as batch_op:
        batch_op.add_column(
            sa.Column("catalog_access_class", sa.String(length=30), nullable=False, server_default="admin_only")
        )
        batch_op.create_check_constraint(
            "ck_subscription_plans_catalog_access_class",
            "catalog_access_class IN ('public', 'private_code_gated', 'admin_only', 'internal_test')",
        )
    bind.execute(
        sa.text(
            """
            UPDATE subscription_plans
            SET catalog_access_class = CASE
                WHEN catalog_visibility = 'public' THEN 'public'
                ELSE 'admin_only'
            END
            """
        )
    )

    op.create_table(
        "customer_onboarding_states",
        _uuid_col("id", nullable=False),
        _uuid_col("mobile_user_id", nullable=False),
        sa.Column("flow_key", sa.String(length=80), nullable=False),
        sa.Column("flow_version", sa.Integer(), nullable=False),
        sa.Column("source_channel", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("skippable", sa.Boolean(), nullable=False),
        _uuid_col("policy_version_id", nullable=True),
        sa.Column("first_eligible_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_shown_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_shown_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("display_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        _uuid_col("result_code_application_id", nullable=True),
        _json_col("result_payload", json_type, bind),
        _uuid_col("signup_finalization_id", nullable=True),
        sa.Column("referral_terminal_state", sa.String(length=30), nullable=True),
        _uuid_col("canonical_identity_link_id", nullable=True),
        sa.Column("auth_channel", sa.String(length=40), nullable=False),
        sa.Column("return_route_key", sa.String(length=60), nullable=True),
        _created_at_col(),
        _updated_at_col(),
        sa.CheckConstraint(
            "status IN ('pending','shown','submitted','completed','skipped','expired','failed_retryable')",
            name="ck_customer_onboarding_states_status",
        ),
        sa.CheckConstraint("display_count >= 0", name="ck_customer_onboarding_states_display_count_non_negative"),
        sa.ForeignKeyConstraint(["mobile_user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mobile_user_id",
            "flow_key",
            "flow_version",
            name="uq_customer_onboarding_states_user_flow_version",
        ),
    )
    _create_indexes(
        "customer_onboarding_states",
        (
            "mobile_user_id",
            "source_channel",
            "status",
            "policy_version_id",
            "expires_at",
            "result_code_application_id",
            "signup_finalization_id",
            "canonical_identity_link_id",
        ),
    )

    op.create_table(
        "customer_principal_links",
        _uuid_col("id", nullable=False),
        _uuid_col("canonical_mobile_user_id", nullable=False),
        sa.Column("principal_type", sa.String(length=40), nullable=False),
        sa.Column("principal_id", sa.String(length=160), nullable=False),
        _uuid_col("auth_realm_id", nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        _json_col("metadata", json_type, bind),
        sa.ForeignKeyConstraint(["canonical_mobile_user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_indexes(
        "customer_principal_links",
        ("canonical_mobile_user_id", "principal_type", "principal_id", "auth_realm_id", "status"),
    )
    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_customer_principal_links_active_realm",
            "customer_principal_links",
            ["principal_type", "principal_id", "auth_realm_id"],
            unique=True,
            postgresql_where=sa.text("status = 'active' AND auth_realm_id IS NOT NULL"),
        )
        op.create_index(
            "uq_customer_principal_links_active_global",
            "customer_principal_links",
            ["principal_type", "principal_id"],
            unique=True,
            postgresql_where=sa.text("status = 'active' AND auth_realm_id IS NULL"),
        )

    op.create_table(
        "customer_code_intents",
        _uuid_col("id", nullable=False),
        _uuid_col("mobile_user_id", nullable=False),
        _uuid_col("growth_code_id", nullable=False),
        _uuid_col("onboarding_state_id", nullable=True),
        sa.Column("intent_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        _uuid_col("policy_version_id", nullable=True),
        sa.Column("source_channel", sa.String(length=30), nullable=False),
        _uuid_col("private_access_grant_id", nullable=True),
        _uuid_col("consumed_by_quote_session_id", nullable=True),
        _uuid_col("consumed_by_order_id", nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        _json_col("metadata", json_type, bind),
        _created_at_col(),
        _updated_at_col(),
        sa.ForeignKeyConstraint(["mobile_user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["onboarding_state_id"], ["customer_onboarding_states.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["private_access_grant_id"], ["private_catalog_access_grants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["consumed_by_quote_session_id"], ["quote_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["consumed_by_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mobile_user_id", "idempotency_key", name="uq_customer_code_intents_user_idem"),
    )
    _create_indexes(
        "customer_code_intents",
        (
            "mobile_user_id",
            "growth_code_id",
            "onboarding_state_id",
            "intent_type",
            "status",
            "policy_version_id",
            "source_channel",
            "private_access_grant_id",
            "consumed_by_quote_session_id",
            "consumed_by_order_id",
            "expires_at",
        ),
    )

    op.create_table(
        "customer_onboarding_code_applications",
        _uuid_col("id", nullable=False),
        _uuid_col("onboarding_state_id", nullable=False),
        _uuid_col("mobile_user_id", nullable=False),
        _uuid_col("growth_code_id", nullable=True),
        sa.Column("resolved_code_type", sa.String(length=20), nullable=True),
        sa.Column("action_context", sa.String(length=30), nullable=False),
        sa.Column("result", sa.String(length=30), nullable=False),
        sa.Column("reject_reason", sa.String(length=80), nullable=True),
        _uuid_col("policy_version_id", nullable=True),
        _uuid_col("risk_decision_id", nullable=True),
        _uuid_col("redemption_id", nullable=True),
        _uuid_col("fulfillment_id", nullable=True),
        _uuid_col("code_intent_id", nullable=True),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("code_prefix", sa.String(length=12), nullable=False),
        _json_col("safe_result_snapshot", json_type, bind),
        _uuid_col("signup_finalization_id", nullable=True),
        sa.Column("referral_terminal_state", sa.String(length=30), nullable=True),
        _uuid_col("canonical_identity_link_id", nullable=True),
        sa.Column("auth_channel", sa.String(length=40), nullable=False),
        sa.Column("return_route_key", sa.String(length=60), nullable=True),
        _created_at_col(),
        sa.ForeignKeyConstraint(["onboarding_state_id"], ["customer_onboarding_states.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mobile_user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["redemption_id"], ["growth_code_redemptions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fulfillment_id"], ["growth_benefit_fulfillments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["code_intent_id"], ["customer_code_intents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mobile_user_id", "idempotency_key", name="uq_customer_onboarding_code_apps_user_idem"),
        sa.UniqueConstraint(
            "onboarding_state_id",
            "idempotency_key",
            name="uq_customer_onboarding_code_apps_state_idem",
        ),
    )
    _create_indexes(
        "customer_onboarding_code_applications",
        (
            "onboarding_state_id",
            "mobile_user_id",
            "growth_code_id",
            "resolved_code_type",
            "action_context",
            "result",
            "reject_reason",
            "policy_version_id",
            "risk_decision_id",
            "redemption_id",
            "fulfillment_id",
            "code_intent_id",
            "signup_finalization_id",
            "canonical_identity_link_id",
        ),
    )

    op.create_table(
        "registration_access_grants",
        _uuid_col("id", nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        _uuid_col("created_by_admin_user_id", nullable=True),
        sa.Column("role_key", sa.String(length=40), nullable=False),
        sa.Column("email_hint_hash", sa.String(length=128), nullable=True),
        _uuid_col("auth_realm_id", nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exchanged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exchange_session_hash", sa.String(length=128), nullable=True),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reservation_key", sa.String(length=120), nullable=True),
        sa.Column("registration_idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        _uuid_col("consumed_user_id", nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_reason", sa.String(length=80), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        _json_col("metadata", json_type, bind),
        sa.CheckConstraint(
            "status IN ('issued','exchanged','reserved','consumed','released','expired','revoked')",
            name="ck_registration_access_grants_status",
        ),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["consumed_user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_registration_access_grants_token_hash"),
        sa.UniqueConstraint("reservation_key", name="uq_registration_access_grants_reservation_key"),
    )
    _create_indexes(
        "registration_access_grants",
        (
            "token_hash",
            "status",
            "created_by_admin_user_id",
            "auth_realm_id",
            "expires_at",
            "exchange_session_hash",
            "registration_idempotency_key",
            "consumed_user_id",
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()

    _drop_existing_table_columns()

    for table_name in (
        "registration_access_grants",
        "customer_onboarding_code_applications",
        "customer_code_intents",
        "customer_principal_links",
        "customer_onboarding_states",
        "growth_code_namespaces",
        "fx_discount_conversions",
        "fx_rate_snapshots",
        "growth_risk_decisions",
        "risk_feature_snapshots",
        "risk_model_versions",
        "order_code_applications",
        "growth_code_reservation_groups",
        "checkout_code_applications",
        "checkout_code_sets",
        "private_catalog_access_grants",
        "growth_private_catalog_policies",
        "growth_rule_definitions",
        "growth_rule_catalog_versions",
        "growth_code_user_counters",
        "invite_batches",
        "growth_benefit_fulfillments",
        "growth_code_benefits",
    ):
        op.drop_table(table_name)

    with op.batch_alter_table("promo_code_policies") as batch_op:
        batch_op.drop_constraint("ck_promo_code_policies_minimum_order_non_negative", type_="check")
        batch_op.drop_constraint("ck_promo_code_policies_commission_basis", type_="check")
        for column_name in (
            "published_at",
            "is_current",
            "policy_version",
            "include_wallet_in_commission_base",
            "commission_basis",
            "require_no_active_access",
            "first_net_paid_order_only",
            "first_completed_order_only",
            "new_customer_only",
            "allow_zero_amount_order",
            "minimum_order_amount",
            "discountable_addon_codes",
            "discount_scope",
            "currency_code",
        ):
            batch_op.drop_column(column_name)

    with op.batch_alter_table("growth_codes") as batch_op:
        batch_op.drop_index("ix_growth_codes_code_namespace")
        batch_op.drop_index("ix_growth_codes_last_used_at")
        batch_op.drop_constraint("uq_growth_codes_namespace_hash", type_="unique")
        batch_op.drop_constraint("ck_growth_codes_reserved_plus_uses_lte_max", type_="check")
        batch_op.drop_constraint("ck_growth_codes_uses_lte_max", type_="check")
        batch_op.drop_constraint("ck_growth_codes_reserved_uses_non_negative", type_="check")
        batch_op.drop_constraint("ck_growth_codes_uses_count_non_negative", type_="check")
        batch_op.drop_constraint("fk_growth_codes_campaign_id_growth_campaigns", type_="foreignkey")
        batch_op.drop_column("code_namespace")
        batch_op.drop_column("last_used_at")
        batch_op.drop_column("reserved_uses")
    op.drop_index("ix_growth_codes_campaign_status", table_name="growth_codes")

    if _has_table(bind, "growth_campaigns"):
        op.drop_index("ix_growth_campaigns_status_schedule", table_name="growth_campaigns")
        op.drop_table("growth_campaigns")


def _drop_existing_table_columns() -> None:
    with op.batch_alter_table("payment_attempts") as batch_op:
        batch_op.drop_index("ix_payment_attempts_code_set_id")
        batch_op.drop_constraint("fk_payment_attempts_code_set_id_checkout_code_sets", type_="foreignkey")
        batch_op.drop_column("code_set_id")

    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_index("ix_payments_code_set_id")
        batch_op.drop_constraint("fk_payments_code_set_id_checkout_code_sets", type_="foreignkey")
        batch_op.drop_column("growth_snapshot")
        batch_op.drop_column("code_set_id")

    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_index("ix_orders_private_catalog_access_grant_id")
        batch_op.drop_index("ix_orders_code_set_id")
        batch_op.drop_constraint("fk_orders_private_catalog_access_grant_id", type_="foreignkey")
        batch_op.drop_constraint("fk_orders_code_set_id_checkout_code_sets", type_="foreignkey")
        batch_op.drop_column("fx_snapshot")
        batch_op.drop_column("risk_snapshot")
        batch_op.drop_column("private_catalog_access_grant_id")
        batch_op.drop_column("code_set_id")

    with op.batch_alter_table("checkout_sessions") as batch_op:
        batch_op.drop_index("ix_checkout_sessions_private_catalog_access_grant_id")
        batch_op.drop_index("ix_checkout_sessions_code_set_id")
        batch_op.drop_constraint("fk_checkout_sessions_private_catalog_access_grant_id", type_="foreignkey")
        batch_op.drop_constraint("fk_checkout_sessions_code_set_id_checkout_code_sets", type_="foreignkey")
        batch_op.drop_column("private_catalog_access_grant_id")
        batch_op.drop_column("code_set_id")

    with op.batch_alter_table("quote_sessions") as batch_op:
        batch_op.drop_index("ix_quote_sessions_private_catalog_access_grant_id")
        batch_op.drop_index("ix_quote_sessions_code_set_id")
        batch_op.drop_constraint("fk_quote_sessions_private_catalog_access_grant_id", type_="foreignkey")
        batch_op.drop_constraint("fk_quote_sessions_code_set_id_checkout_code_sets", type_="foreignkey")
        batch_op.drop_column("private_catalog_access_grant_id")
        batch_op.drop_column("code_set_id")

    with op.batch_alter_table("subscription_plans") as batch_op:
        batch_op.drop_constraint("ck_subscription_plans_catalog_access_class", type_="check")
        batch_op.drop_column("catalog_access_class")

    with op.batch_alter_table("promo_code_usages") as batch_op:
        batch_op.drop_constraint("uq_promo_code_usages_promo_payment", type_="unique")
        batch_op.drop_constraint("fk_promo_code_usages_payment_id_payments", type_="foreignkey")

    with op.batch_alter_table("growth_code_redemptions") as batch_op:
        batch_op.drop_index("ix_growth_code_redemptions_reservation_id")
        batch_op.drop_index("ix_growth_code_redemptions_payment_id")
        batch_op.drop_constraint("fk_growth_code_redemptions_reservation_id", type_="foreignkey")
        batch_op.drop_constraint("fk_growth_code_redemptions_payment_id", type_="foreignkey")
        batch_op.drop_column("usage_number")
        batch_op.drop_column("reservation_id")
        batch_op.drop_column("payment_id")

    with op.batch_alter_table("growth_code_reservations") as batch_op:
        batch_op.drop_index("ix_growth_code_reservations_consumed_payment_id")
        batch_op.drop_index("ix_growth_code_reservations_consumed_at")
        batch_op.drop_index("ix_growth_code_reservations_committed_at")
        batch_op.drop_index("ix_growth_code_reservations_reservation_group_id")
        batch_op.drop_constraint("fk_growth_code_reservations_consumed_payment_id", type_="foreignkey")
        batch_op.drop_constraint("fk_growth_code_reservations_reservation_group_id", type_="foreignkey")
        batch_op.drop_column("consumed_payment_id")
        batch_op.drop_column("consumed_at")
        batch_op.drop_column("committed_at")
        batch_op.drop_column("reservation_group_id")
    op.drop_index("ix_growth_reservations_code_status_expiry", table_name="growth_code_reservations")

    op.drop_index("ix_invite_codes_batch_status", table_name="invite_codes")
    with op.batch_alter_table("invite_codes") as batch_op:
        batch_op.drop_index("ix_invite_codes_code_prefix")
        batch_op.drop_index("ix_invite_codes_code_hash")
        batch_op.drop_index("ix_invite_codes_status")
        batch_op.drop_index("ix_invite_codes_source_benefit_id")
        batch_op.drop_index("ix_invite_codes_source_growth_code_id")
        batch_op.drop_index("ix_invite_codes_batch_id")
        batch_op.drop_constraint("fk_invite_codes_revoked_by_admin_id_admin_users", type_="foreignkey")
        batch_op.drop_constraint("fk_invite_codes_source_benefit_id_growth_code_benefits", type_="foreignkey")
        batch_op.drop_constraint("fk_invite_codes_source_growth_code_id_growth_codes", type_="foreignkey")
        batch_op.drop_constraint("fk_invite_codes_batch_id_invite_batches", type_="foreignkey")
        batch_op.drop_constraint("fk_invite_codes_plan_id_subscription_plans", type_="foreignkey")
        for column_name in (
            "revoked_reason",
            "revoked_by_admin_id",
            "revoked_at",
            "entitlement_snapshot",
            "entitlement_profile_key",
            "entitlement_mode",
            "code_prefix",
            "code_hash",
            "status",
            "source_benefit_id",
            "source_growth_code_id",
            "batch_id",
        ):
            batch_op.drop_column(column_name)


def _json_type(bind: sa.Connection) -> sa.types.TypeEngine:
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_default(bind: sa.Connection, value: str) -> sa.TextClause:
    if bind.dialect.name == "postgresql":
        return sa.text(f"'{value}'::jsonb")
    return sa.text(f"'{value}'")


def _json_col(
    name: str,
    json_type: sa.types.TypeEngine,
    bind: sa.Connection,
    *,
    nullable: bool = False,
    default: str = "{}",
) -> sa.Column:
    return sa.Column(name, json_type, nullable=nullable, server_default=_json_default(bind, default))


def _uuid_col(name: str, *, nullable: bool) -> sa.Column:
    return sa.Column(name, sa.Uuid(), nullable=nullable)


def _created_at_col() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def _updated_at_col() -> sa.Column:
    return sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def _create_indexes(table_name: str, column_names: Sequence[str]) -> None:
    for column_name in column_names:
        op.create_index(_index_name(table_name, column_name), table_name, [column_name])


def _index_name(table_name: str, column_name: str) -> str:
    index_name = f"ix_{table_name}_{column_name}"
    if len(index_name) <= 63:
        return index_name
    digest = hashlib.sha256(index_name.encode("utf-8")).hexdigest()[:8]
    return f"{index_name[:54]}_{digest}"


def _has_table(bind: sa.Connection, table_name: str) -> bool:
    return inspect(bind).has_table(table_name)


def _has_column(bind: sa.Connection, table_name: str, column_name: str) -> bool:
    if not _has_table(bind, table_name):
        return False
    return any(column["name"] == column_name for column in inspect(bind).get_columns(table_name))


def _assert_no_growth_code_namespace_collisions(bind: sa.Connection) -> None:
    namespace_collisions = _namespace_code_hash_collisions(bind)
    if namespace_collisions:
        details = []
        for code_hash, code_types in namespace_collisions[:5]:
            details.append(f"namespace hash={code_hash} sources={','.join(sorted(code_types))}")
        raise RuntimeError(
            "Cannot add Growth Codes v6 customer namespace while cross-type code collisions exist. "
            f"Collision report: {'; '.join(details)}"
        )


def _namespace_code_hash_collisions(bind: sa.Connection) -> list[tuple[str, set[str]]]:
    by_hash: dict[str, set[str]] = defaultdict(set)
    if _has_table(bind, "growth_codes"):
        rows = bind.execute(
            sa.text(
                """
                SELECT code_hash, code_type
                FROM growth_codes
                WHERE code_hash IS NOT NULL
                ORDER BY code_hash, code_type
                """
            )
        ).mappings()
        for row in rows:
            by_hash[str(row["code_hash"])].add(str(row["code_type"]))
    for source in _legacy_code_sources(bind):
        by_hash[source.normalized_code_hash].add(source.code_type)
    return sorted(
        ((code_hash, code_types) for code_hash, code_types in by_hash.items() if len(code_types) > 1),
        key=lambda item: item[0],
    )


def _assert_no_duplicate_promo_payment_usages(bind: sa.Connection) -> None:
    if not _has_table(bind, "promo_code_usages"):
        return
    duplicate = bind.execute(
        sa.text(
            """
            SELECT promo_code_id, payment_id, COUNT(*) AS usage_count
            FROM promo_code_usages
            GROUP BY promo_code_id, payment_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot add uq_promo_code_usages_promo_payment while duplicate promo/payment usage rows exist. "
            "Resolve duplicate promo_code_usages rows first."
        )


def _assert_invite_plan_ids_resolve(bind: sa.Connection) -> None:
    if not (_has_table(bind, "invite_codes") and _has_table(bind, "subscription_plans")):
        return
    orphan = bind.execute(
        sa.text(
            """
            SELECT plan_id
            FROM invite_codes
            WHERE plan_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM subscription_plans
                WHERE subscription_plans.id = invite_codes.plan_id
              )
            LIMIT 1
            """
        )
    ).first()
    if orphan is not None:
        raise RuntimeError(
            "Cannot add invite_codes.plan_id foreign key while orphan invite plan ids exist. "
            "Backfill or null invalid invite_codes.plan_id values first."
        )


def _backfill_growth_code_namespaces(bind: sa.Connection) -> None:
    _backfill_canonical_growth_code_namespaces(bind)
    _backfill_legacy_growth_code_namespaces(bind)


def _backfill_canonical_growth_code_namespaces(bind: sa.Connection) -> None:
    if not _has_table(bind, "growth_codes"):
        return
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                """
                INSERT INTO growth_code_namespaces (
                    normalized_code_hash,
                    canonical_growth_code_id,
                    code_type,
                    status,
                    created_at
                )
                SELECT code_hash, id, code_type, status, COALESCE(created_at, now())
                FROM growth_codes
                WHERE code_hash IS NOT NULL
                ORDER BY code_hash, code_type, id
                ON CONFLICT (normalized_code_hash) DO NOTHING
                """
            )
        )
        return

    bind.execute(
        sa.text(
            """
            INSERT OR IGNORE INTO growth_code_namespaces (
                normalized_code_hash,
                canonical_growth_code_id,
                code_type,
                status,
                created_at
            )
            SELECT code_hash, id, code_type, status, COALESCE(created_at, CURRENT_TIMESTAMP)
            FROM growth_codes
            WHERE code_hash IS NOT NULL
            ORDER BY code_hash, code_type, id
            """
        )
    )


def _backfill_legacy_growth_code_namespaces(bind: sa.Connection) -> None:
    legacy_sources = _legacy_code_sources(bind)
    if not legacy_sources:
        return

    rows = [
        {
            "normalized_code_hash": source.normalized_code_hash,
            "canonical_growth_code_id": None,
            "code_type": source.code_type,
            "status": source.status,
            "legacy_source_type": source.legacy_source_type,
            "legacy_source_id": source.source_id,
            "created_at": source.created_at,
        }
        for source in legacy_sources
    ]
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                """
                INSERT INTO growth_code_namespaces (
                    normalized_code_hash,
                    canonical_growth_code_id,
                    code_type,
                    status,
                    legacy_source_type,
                    legacy_source_id,
                    created_at
                )
                VALUES (
                    :normalized_code_hash,
                    :canonical_growth_code_id,
                    :code_type,
                    :status,
                    :legacy_source_type,
                    :legacy_source_id,
                    COALESCE(:created_at, now())
                )
                ON CONFLICT (normalized_code_hash) DO NOTHING
                """
            ),
            rows,
        )
        return

    bind.execute(
        sa.text(
            """
            INSERT OR IGNORE INTO growth_code_namespaces (
                normalized_code_hash,
                canonical_growth_code_id,
                code_type,
                status,
                legacy_source_type,
                legacy_source_id,
                created_at
            )
            VALUES (
                :normalized_code_hash,
                :canonical_growth_code_id,
                :code_type,
                :status,
                :legacy_source_type,
                :legacy_source_id,
                COALESCE(:created_at, CURRENT_TIMESTAMP)
            )
            """
        ),
        rows,
    )


def _legacy_code_sources(bind: sa.Connection) -> list[_LegacyCodeSource]:
    selects = _legacy_code_source_selects(bind)
    if not selects:
        return []

    rows = bind.execute(sa.union_all(*selects)).mappings()
    sources: list[_LegacyCodeSource] = []
    for row in rows:
        normalized_code = _normalize_legacy_code(row["raw_code"])
        if normalized_code is None:
            continue
        status = _namespace_status(row["source_status"])
        sources.append(
            _LegacyCodeSource(
                code_type=str(row["code_type"]),
                legacy_source_type=str(row["legacy_source_type"]),
                source_id=row["source_id"],
                normalized_code=normalized_code,
                normalized_code_hash=_runtime_growth_code_hash(normalized_code),
                status=status,
                created_at=row["created_at"],
            )
        )
    return sorted(
        sources,
        key=lambda source: (
            source.normalized_code_hash,
            source.code_type,
            source.legacy_source_type,
            str(source.source_id) if source.source_id is not None else "",
        ),
    )


def _legacy_code_source_selects(bind: sa.Connection) -> list[sa.sql.Select]:
    selects: list[sa.sql.Select] = []
    for table_name, code_column, code_type, legacy_source_type in _LEGACY_CODE_SOURCE_SPECS:
        if not _has_column(bind, table_name, code_column):
            continue
        table = sa.table(
            table_name,
            sa.column("id"),
            sa.column(code_column),
            sa.column("created_at"),
            sa.column("status"),
            sa.column("lifecycle_status"),
            sa.column("is_active"),
            sa.column("is_used"),
        )
        source_id_expr = table.c.id if _has_column(bind, table_name, "id") else sa.null()
        created_at_expr = table.c.created_at if _has_column(bind, table_name, "created_at") else sa.null()
        status_expr = _legacy_status_expr(bind, table_name, table)
        selects.append(
            sa.select(
                sa.literal(code_type).label("code_type"),
                sa.literal(legacy_source_type).label("legacy_source_type"),
                source_id_expr.label("source_id"),
                table.c[code_column].label("raw_code"),
                status_expr.label("source_status"),
                created_at_expr.label("created_at"),
            )
            .select_from(table)
            .where(table.c[code_column].is_not(None))
        )
    return selects


def _legacy_status_expr(bind: sa.Connection, table_name: str, table: sa.TableClause) -> sa.ColumnElement[object]:
    if _has_column(bind, table_name, "status"):
        return sa.cast(table.c.status, sa.Text())
    if _has_column(bind, table_name, "lifecycle_status"):
        return sa.cast(table.c.lifecycle_status, sa.Text())
    if _has_column(bind, table_name, "is_active"):
        return sa.case((table.c.is_active, sa.literal("active")), else_=sa.literal("inactive"))
    if _has_column(bind, table_name, "is_used"):
        return sa.case((table.c.is_used, sa.literal("redeemed")), else_=sa.literal("issued"))
    return sa.literal("legacy")


def _normalize_legacy_code(value: object) -> str | None:
    normalized = unicodedata.normalize("NFKC", str(value)).strip().upper()
    return normalized or None


def _namespace_status(value: object) -> str:
    status = str(value or "legacy").strip().lower()
    return (status or "legacy")[:20]


def _runtime_growth_code_hash(value: str) -> str:
    return hmac.new(_growth_code_hash_secret(), value.encode("utf-8"), hashlib.sha256).hexdigest()


def _growth_code_hash_secret() -> bytes:
    secret = (os.environ.get("GROWTH_CODE_HASH_SECRET") or os.environ.get("JWT_SECRET") or "").strip()
    if not secret:
        raise RuntimeError(
            "Growth Codes v6 migration requires GROWTH_CODE_HASH_SECRET or JWT_SECRET "
            "to backfill legacy namespace hashes with the runtime HMAC algorithm."
        )
    return secret.encode("utf-8")
