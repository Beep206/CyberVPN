"""Canonical customer growth code registry, tracking, and lifecycle backbone."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260421_p12_growth_codes"
down_revision = "20260420_p11_partner_notif_reads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "growth_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("code_prefix", sa.String(length=12), nullable=False),
        sa.Column("code_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("issuer_type", sa.String(length=40), nullable=False),
        sa.Column("issuer_admin_id", sa.Uuid(), nullable=True),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("owner_partner_account_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("storefront_id", sa.Uuid(), nullable=True),
        sa.Column("auth_realm_id", sa.Uuid(), nullable=True),
        sa.Column("policy_version_id", sa.Uuid(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("uses_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("revoked_reason", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["issuer_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_partner_account_id"], ["partner_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["revoked_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash", "code_type", name="uq_growth_codes_hash_type"),
    )
    for index_name, columns in (
        ("ix_growth_codes_code_hash", ["code_hash"]),
        ("ix_growth_codes_code_prefix", ["code_prefix"]),
        ("ix_growth_codes_code_type", ["code_type"]),
        ("ix_growth_codes_status", ["status"]),
        ("ix_growth_codes_issuer_type", ["issuer_type"]),
        ("ix_growth_codes_issuer_admin_id", ["issuer_admin_id"]),
        ("ix_growth_codes_owner_user_id", ["owner_user_id"]),
        ("ix_growth_codes_owner_partner_account_id", ["owner_partner_account_id"]),
        ("ix_growth_codes_campaign_id", ["campaign_id"]),
        ("ix_growth_codes_batch_id", ["batch_id"]),
        ("ix_growth_codes_storefront_id", ["storefront_id"]),
        ("ix_growth_codes_auth_realm_id", ["auth_realm_id"]),
        ("ix_growth_codes_policy_version_id", ["policy_version_id"]),
        ("ix_growth_codes_starts_at", ["starts_at"]),
        ("ix_growth_codes_expires_at", ["expires_at"]),
        ("ix_growth_codes_revoked_at", ["revoked_at"]),
        ("ix_growth_codes_revoked_by_admin_id", ["revoked_by_admin_id"]),
    ):
        op.create_index(index_name, "growth_codes", columns)

    op.create_table(
        "growth_code_issuances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("growth_code_id", sa.Uuid(), nullable=False),
        sa.Column("issuance_type", sa.String(length=40), nullable=False),
        sa.Column("issued_to_user_id", sa.Uuid(), nullable=True),
        sa.Column("issued_to_partner_account_id", sa.Uuid(), nullable=True),
        sa.Column("issued_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("source_order_id", sa.Uuid(), nullable=True),
        sa.Column("source_payment_id", sa.Uuid(), nullable=True),
        sa.Column("source_plan_sku", sa.String(length=120), nullable=True),
        sa.Column("raw_code_encrypted", sa.Text(), nullable=True),
        sa.Column("source_bundle_snapshot", sa.JSON(), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issued_to_user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["issued_to_partner_account_id"], ["partner_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["issued_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for index_name, columns in (
        ("ix_growth_code_issuances_growth_code_id", ["growth_code_id"]),
        ("ix_growth_code_issuances_issuance_type", ["issuance_type"]),
        ("ix_growth_code_issuances_issued_to_user_id", ["issued_to_user_id"]),
        ("ix_growth_code_issuances_issued_to_partner_account_id", ["issued_to_partner_account_id"]),
        ("ix_growth_code_issuances_issued_by_admin_id", ["issued_by_admin_id"]),
        ("ix_growth_code_issuances_source_order_id", ["source_order_id"]),
        ("ix_growth_code_issuances_source_payment_id", ["source_payment_id"]),
    ):
        op.create_index(index_name, "growth_code_issuances", columns)

    op.create_table(
        "growth_code_touchpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("growth_code_id", sa.Uuid(), nullable=False),
        sa.Column("code_type", sa.String(length=20), nullable=False),
        sa.Column("anonymous_session_id", sa.String(length=120), nullable=True),
        sa.Column("registered_user_id", sa.Uuid(), nullable=True),
        sa.Column("risk_subject_id", sa.Uuid(), nullable=True),
        sa.Column("storefront_id", sa.Uuid(), nullable=True),
        sa.Column("auth_realm_id", sa.Uuid(), nullable=True),
        sa.Column("surface", sa.String(length=40), nullable=True),
        sa.Column("channel", sa.String(length=30), nullable=True),
        sa.Column("utm_source", sa.String(length=120), nullable=True),
        sa.Column("utm_medium", sa.String(length=120), nullable=True),
        sa.Column("utm_campaign", sa.String(length=120), nullable=True),
        sa.Column("click_id", sa.String(length=160), nullable=True),
        sa.Column("sub_id", sa.String(length=160), nullable=True),
        sa.Column("ip_hash", sa.String(length=128), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("converted_to_signup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_to_order_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["registered_user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["risk_subject_id"], ["risk_subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["converted_to_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for index_name, columns in (
        ("ix_growth_code_touchpoints_growth_code_id", ["growth_code_id"]),
        ("ix_growth_code_touchpoints_code_type", ["code_type"]),
        ("ix_growth_code_touchpoints_anonymous_session_id", ["anonymous_session_id"]),
        ("ix_growth_code_touchpoints_registered_user_id", ["registered_user_id"]),
        ("ix_growth_code_touchpoints_risk_subject_id", ["risk_subject_id"]),
        ("ix_growth_code_touchpoints_storefront_id", ["storefront_id"]),
        ("ix_growth_code_touchpoints_auth_realm_id", ["auth_realm_id"]),
        ("ix_growth_code_touchpoints_surface", ["surface"]),
        ("ix_growth_code_touchpoints_channel", ["channel"]),
        ("ix_growth_code_touchpoints_converted_to_signup_at", ["converted_to_signup_at"]),
        ("ix_growth_code_touchpoints_converted_to_order_id", ["converted_to_order_id"]),
    ):
        op.create_index(index_name, "growth_code_touchpoints", columns)

    op.create_table(
        "growth_signup_attributions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("growth_code_id", sa.Uuid(), nullable=False),
        sa.Column("code_type", sa.String(length=20), nullable=False),
        sa.Column("touchpoint_id", sa.Uuid(), nullable=False),
        sa.Column("attribution_source", sa.String(length=40), nullable=False),
        sa.Column("storefront_id", sa.Uuid(), nullable=True),
        sa.Column("auth_realm_id", sa.Uuid(), nullable=True),
        sa.Column("risk_subject_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["touchpoint_id"], ["growth_code_touchpoints.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["risk_subject_id"], ["risk_subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_growth_signup_attributions_user_id"),
    )
    for index_name, columns in (
        ("ix_growth_signup_attributions_user_id", ["user_id"]),
        ("ix_growth_signup_attributions_growth_code_id", ["growth_code_id"]),
        ("ix_growth_signup_attributions_code_type", ["code_type"]),
        ("ix_growth_signup_attributions_touchpoint_id", ["touchpoint_id"]),
        ("ix_growth_signup_attributions_attribution_source", ["attribution_source"]),
        ("ix_growth_signup_attributions_storefront_id", ["storefront_id"]),
        ("ix_growth_signup_attributions_auth_realm_id", ["auth_realm_id"]),
        ("ix_growth_signup_attributions_risk_subject_id", ["risk_subject_id"]),
    ):
        op.create_index(index_name, "growth_signup_attributions", columns)

    for table_name, extra_columns in (
        (
            "invite_code_policies",
            [
                sa.Column("friend_days", sa.Integer(), nullable=False),
                sa.Column("entitlement_profile_key", sa.String(length=80), nullable=True),
                sa.Column("conversion_reward_policy_id", sa.Uuid(), nullable=True),
                sa.Column("self_redemption_block", sa.Boolean(), nullable=False, server_default=sa.true()),
                sa.Column("risk_ruleset_id", sa.Uuid(), nullable=True),
            ],
        ),
        (
            "referral_program_policies",
            [
                sa.Column("program_key", sa.String(length=80), nullable=True),
                sa.Column("friend_discount_type", sa.String(length=20), nullable=True),
                sa.Column("friend_discount_value", sa.Numeric(12, 2), nullable=True),
                sa.Column("eligible_durations", sa.JSON(), nullable=False),
                sa.Column("eligible_plan_families", sa.JSON(), nullable=False),
                sa.Column("reward_type", sa.String(length=40), nullable=True),
                sa.Column("reward_value", sa.Numeric(12, 2), nullable=True),
                sa.Column("hold_days", sa.Integer(), nullable=True),
                sa.Column("monthly_cap", sa.Numeric(12, 2), nullable=True),
                sa.Column("lifetime_cap", sa.Numeric(12, 2), nullable=True),
                sa.Column("anti_abuse_policy_id", sa.Uuid(), nullable=True),
            ],
        ),
        (
            "promo_code_policies",
            [
                sa.Column("discount_type", sa.String(length=20), nullable=False),
                sa.Column("discount_value", sa.Numeric(12, 2), nullable=False),
                sa.Column("max_discount_amount", sa.Numeric(12, 2), nullable=True),
                sa.Column("eligible_plan_ids", sa.JSON(), nullable=False),
                sa.Column("eligible_plan_families", sa.JSON(), nullable=False),
                sa.Column("eligible_durations", sa.JSON(), nullable=False),
                sa.Column("eligible_addons", sa.JSON(), nullable=False),
                sa.Column("allowed_checkout_modes", sa.JSON(), nullable=False),
                sa.Column("allowed_channels", sa.JSON(), nullable=False),
                sa.Column("allowed_geos", sa.JSON(), nullable=False),
                sa.Column("min_net_paid_amount", sa.Numeric(12, 2), nullable=True),
                sa.Column("usage_cap_per_user", sa.Integer(), nullable=True),
                sa.Column("global_usage_cap", sa.Integer(), nullable=True),
            ],
        ),
        (
            "gift_code_policies",
            [
                sa.Column("grant_type", sa.String(length=40), nullable=False),
                sa.Column("plan_family", sa.String(length=40), nullable=True),
                sa.Column("duration_days", sa.Integer(), nullable=True),
                sa.Column("entitlement_snapshot", sa.JSON(), nullable=False),
                sa.Column("redemption_mode", sa.String(length=40), nullable=True),
                sa.Column("transferable", sa.Boolean(), nullable=False, server_default=sa.false()),
                sa.Column("batch_id", sa.Uuid(), nullable=True),
            ],
        ),
    ):
        op.create_table(
            table_name,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("growth_code_id", sa.Uuid(), nullable=True if table_name == "referral_program_policies" else False),
            *extra_columns,
            sa.Column("policy_snapshot", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("growth_code_id"),
        )

    op.create_foreign_key(
        "fk_invite_code_policies_conversion_reward_policy_id",
        "invite_code_policies",
        "policy_versions",
        ["conversion_reward_policy_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_invite_code_policies_growth_code_id", "invite_code_policies", ["growth_code_id"])
    op.create_index(
        "ix_invite_code_policies_conversion_reward_policy_id",
        "invite_code_policies",
        ["conversion_reward_policy_id"],
    )
    op.create_index("ix_invite_code_policies_risk_ruleset_id", "invite_code_policies", ["risk_ruleset_id"])

    op.create_foreign_key(
        "fk_referral_program_policies_anti_abuse_policy_id",
        "referral_program_policies",
        "policy_versions",
        ["anti_abuse_policy_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_referral_program_policies_program_key",
        "referral_program_policies",
        ["program_key"],
    )
    op.create_index("ix_referral_program_policies_growth_code_id", "referral_program_policies", ["growth_code_id"])
    op.create_index("ix_referral_program_policies_program_key", "referral_program_policies", ["program_key"])
    op.create_index(
        "ix_referral_program_policies_anti_abuse_policy_id",
        "referral_program_policies",
        ["anti_abuse_policy_id"],
    )

    op.create_index("ix_promo_code_policies_growth_code_id", "promo_code_policies", ["growth_code_id"])
    op.create_index("ix_gift_code_policies_growth_code_id", "gift_code_policies", ["growth_code_id"])
    op.create_index("ix_gift_code_policies_batch_id", "gift_code_policies", ["batch_id"])

    op.create_table(
        "growth_code_resolution_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("growth_code_id", sa.Uuid(), nullable=True),
        sa.Column("raw_code_hash", sa.String(length=128), nullable=False),
        sa.Column("code_type", sa.String(length=20), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("anonymous_session_id", sa.String(length=120), nullable=True),
        sa.Column("checkout_session_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("surface", sa.String(length=40), nullable=False, server_default="api"),
        sa.Column("action_context", sa.String(length=20), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("reject_reason", sa.String(length=80), nullable=True),
        sa.Column("conflict_code", sa.String(length=80), nullable=True),
        sa.Column("policy_version_id", sa.Uuid(), nullable=True),
        sa.Column("risk_decision_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for index_name, columns in (
        ("ix_growth_code_resolution_events_growth_code_id", ["growth_code_id"]),
        ("ix_growth_code_resolution_events_raw_code_hash", ["raw_code_hash"]),
        ("ix_growth_code_resolution_events_code_type", ["code_type"]),
        ("ix_growth_code_resolution_events_user_id", ["user_id"]),
        ("ix_growth_code_resolution_events_anonymous_session_id", ["anonymous_session_id"]),
        ("ix_growth_code_resolution_events_checkout_session_id", ["checkout_session_id"]),
        ("ix_growth_code_resolution_events_order_id", ["order_id"]),
        ("ix_growth_code_resolution_events_surface", ["surface"]),
        ("ix_growth_code_resolution_events_action_context", ["action_context"]),
        ("ix_growth_code_resolution_events_result", ["result"]),
        ("ix_growth_code_resolution_events_reject_reason", ["reject_reason"]),
        ("ix_growth_code_resolution_events_policy_version_id", ["policy_version_id"]),
        ("ix_growth_code_resolution_events_risk_decision_id", ["risk_decision_id"]),
        ("ix_growth_code_resolution_events_created_at", ["created_at"]),
    ):
        op.create_index(index_name, "growth_code_resolution_events", columns)

    op.create_table(
        "growth_code_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("growth_code_id", sa.Uuid(), nullable=False),
        sa.Column("checkout_session_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="reserved"),
        sa.Column("consumed_order_id", sa.Uuid(), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_reason", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["consumed_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for index_name, columns in (
        ("ix_growth_code_reservations_growth_code_id", ["growth_code_id"]),
        ("ix_growth_code_reservations_checkout_session_id", ["checkout_session_id"]),
        ("ix_growth_code_reservations_user_id", ["user_id"]),
        ("ix_growth_code_reservations_reserved_at", ["reserved_at"]),
        ("ix_growth_code_reservations_expires_at", ["expires_at"]),
        ("ix_growth_code_reservations_status", ["status"]),
        ("ix_growth_code_reservations_consumed_order_id", ["consumed_order_id"]),
        ("ix_growth_code_reservations_released_at", ["released_at"]),
    ):
        op.create_index(index_name, "growth_code_reservations", columns)

    op.create_table(
        "growth_code_redemptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("growth_code_id", sa.Uuid(), nullable=False),
        sa.Column("code_type", sa.String(length=20), nullable=False),
        sa.Column("redeemer_user_id", sa.Uuid(), nullable=True),
        sa.Column("beneficiary_user_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("entitlement_grant_id", sa.Uuid(), nullable=True),
        sa.Column("wallet_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("reward_allocation_id", sa.Uuid(), nullable=True),
        sa.Column("policy_version_id", sa.Uuid(), nullable=True),
        sa.Column("risk_decision_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="redeemed"),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversal_reason", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["growth_code_id"], ["growth_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["redeemer_user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["beneficiary_user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["entitlement_grant_id"], ["entitlement_grants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["wallet_transaction_id"], ["wallet_transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for index_name, columns in (
        ("ix_growth_code_redemptions_growth_code_id", ["growth_code_id"]),
        ("ix_growth_code_redemptions_code_type", ["code_type"]),
        ("ix_growth_code_redemptions_redeemer_user_id", ["redeemer_user_id"]),
        ("ix_growth_code_redemptions_beneficiary_user_id", ["beneficiary_user_id"]),
        ("ix_growth_code_redemptions_order_id", ["order_id"]),
        ("ix_growth_code_redemptions_entitlement_grant_id", ["entitlement_grant_id"]),
        ("ix_growth_code_redemptions_wallet_transaction_id", ["wallet_transaction_id"]),
        ("ix_growth_code_redemptions_reward_allocation_id", ["reward_allocation_id"]),
        ("ix_growth_code_redemptions_policy_version_id", ["policy_version_id"]),
        ("ix_growth_code_redemptions_risk_decision_id", ["risk_decision_id"]),
        ("ix_growth_code_redemptions_status", ["status"]),
        ("ix_growth_code_redemptions_redeemed_at", ["redeemed_at"]),
        ("ix_growth_code_redemptions_reversed_at", ["reversed_at"]),
    ):
        op.create_index(index_name, "growth_code_redemptions", columns)

    with op.batch_alter_table("growth_reward_allocations") as batch_op:
        batch_op.add_column(sa.Column("source_code_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("source_redemption_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("policy_version_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("hold_until", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("available_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("reversal_reason", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("wallet_transaction_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_growth_reward_allocations_source_code_id",
            "growth_codes",
            ["source_code_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_growth_reward_allocations_source_redemption_id",
            "growth_code_redemptions",
            ["source_redemption_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_growth_reward_allocations_policy_version_id",
            "policy_versions",
            ["policy_version_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_growth_reward_allocations_wallet_transaction_id",
            "wallet_transactions",
            ["wallet_transaction_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint(
            "uq_growth_reward_allocations_source_redemption_id",
            ["source_redemption_id"],
        )
    for index_name, columns in (
        ("ix_growth_reward_allocations_source_code_id", ["source_code_id"]),
        ("ix_growth_reward_allocations_source_redemption_id", ["source_redemption_id"]),
        ("ix_growth_reward_allocations_policy_version_id", ["policy_version_id"]),
        ("ix_growth_reward_allocations_hold_until", ["hold_until"]),
        ("ix_growth_reward_allocations_available_at", ["available_at"]),
        ("ix_growth_reward_allocations_wallet_transaction_id", ["wallet_transaction_id"]),
    ):
        op.create_index(index_name, "growth_reward_allocations", columns)


def downgrade() -> None:
    for index_name in (
        "ix_growth_reward_allocations_wallet_transaction_id",
        "ix_growth_reward_allocations_available_at",
        "ix_growth_reward_allocations_hold_until",
        "ix_growth_reward_allocations_policy_version_id",
        "ix_growth_reward_allocations_source_redemption_id",
        "ix_growth_reward_allocations_source_code_id",
    ):
        op.drop_index(index_name, table_name="growth_reward_allocations")
    with op.batch_alter_table("growth_reward_allocations") as batch_op:
        batch_op.drop_constraint("uq_growth_reward_allocations_source_redemption_id", type_="unique")
        batch_op.drop_constraint("fk_growth_reward_allocations_wallet_transaction_id", type_="foreignkey")
        batch_op.drop_constraint("fk_growth_reward_allocations_policy_version_id", type_="foreignkey")
        batch_op.drop_constraint("fk_growth_reward_allocations_source_redemption_id", type_="foreignkey")
        batch_op.drop_constraint("fk_growth_reward_allocations_source_code_id", type_="foreignkey")
        batch_op.drop_column("wallet_transaction_id")
        batch_op.drop_column("reversal_reason")
        batch_op.drop_column("available_at")
        batch_op.drop_column("hold_until")
        batch_op.drop_column("policy_version_id")
        batch_op.drop_column("source_redemption_id")
        batch_op.drop_column("source_code_id")

    for table_name, indexes in (
        (
            "growth_code_redemptions",
            [
                "ix_growth_code_redemptions_reversed_at",
                "ix_growth_code_redemptions_redeemed_at",
                "ix_growth_code_redemptions_status",
                "ix_growth_code_redemptions_risk_decision_id",
                "ix_growth_code_redemptions_policy_version_id",
                "ix_growth_code_redemptions_reward_allocation_id",
                "ix_growth_code_redemptions_wallet_transaction_id",
                "ix_growth_code_redemptions_entitlement_grant_id",
                "ix_growth_code_redemptions_order_id",
                "ix_growth_code_redemptions_beneficiary_user_id",
                "ix_growth_code_redemptions_redeemer_user_id",
                "ix_growth_code_redemptions_code_type",
                "ix_growth_code_redemptions_growth_code_id",
            ],
        ),
        (
            "growth_code_reservations",
            [
                "ix_growth_code_reservations_released_at",
                "ix_growth_code_reservations_consumed_order_id",
                "ix_growth_code_reservations_status",
                "ix_growth_code_reservations_expires_at",
                "ix_growth_code_reservations_reserved_at",
                "ix_growth_code_reservations_user_id",
                "ix_growth_code_reservations_checkout_session_id",
                "ix_growth_code_reservations_growth_code_id",
            ],
        ),
        (
            "growth_code_resolution_events",
            [
                "ix_growth_code_resolution_events_created_at",
                "ix_growth_code_resolution_events_risk_decision_id",
                "ix_growth_code_resolution_events_policy_version_id",
                "ix_growth_code_resolution_events_reject_reason",
                "ix_growth_code_resolution_events_result",
                "ix_growth_code_resolution_events_action_context",
                "ix_growth_code_resolution_events_surface",
                "ix_growth_code_resolution_events_order_id",
                "ix_growth_code_resolution_events_checkout_session_id",
                "ix_growth_code_resolution_events_anonymous_session_id",
                "ix_growth_code_resolution_events_user_id",
                "ix_growth_code_resolution_events_code_type",
                "ix_growth_code_resolution_events_raw_code_hash",
                "ix_growth_code_resolution_events_growth_code_id",
            ],
        ),
        (
            "gift_code_policies",
            [
                "ix_gift_code_policies_batch_id",
                "ix_gift_code_policies_growth_code_id",
            ],
        ),
        (
            "promo_code_policies",
            [
                "ix_promo_code_policies_growth_code_id",
            ],
        ),
        (
            "referral_program_policies",
            [
                "ix_referral_program_policies_anti_abuse_policy_id",
                "ix_referral_program_policies_program_key",
                "ix_referral_program_policies_growth_code_id",
            ],
        ),
        (
            "invite_code_policies",
            [
                "ix_invite_code_policies_risk_ruleset_id",
                "ix_invite_code_policies_conversion_reward_policy_id",
                "ix_invite_code_policies_growth_code_id",
            ],
        ),
        (
            "growth_signup_attributions",
            [
                "ix_growth_signup_attributions_risk_subject_id",
                "ix_growth_signup_attributions_auth_realm_id",
                "ix_growth_signup_attributions_storefront_id",
                "ix_growth_signup_attributions_attribution_source",
                "ix_growth_signup_attributions_touchpoint_id",
                "ix_growth_signup_attributions_code_type",
                "ix_growth_signup_attributions_growth_code_id",
                "ix_growth_signup_attributions_user_id",
            ],
        ),
        (
            "growth_code_touchpoints",
            [
                "ix_growth_code_touchpoints_converted_to_order_id",
                "ix_growth_code_touchpoints_converted_to_signup_at",
                "ix_growth_code_touchpoints_channel",
                "ix_growth_code_touchpoints_surface",
                "ix_growth_code_touchpoints_auth_realm_id",
                "ix_growth_code_touchpoints_storefront_id",
                "ix_growth_code_touchpoints_risk_subject_id",
                "ix_growth_code_touchpoints_registered_user_id",
                "ix_growth_code_touchpoints_anonymous_session_id",
                "ix_growth_code_touchpoints_code_type",
                "ix_growth_code_touchpoints_growth_code_id",
            ],
        ),
        (
            "growth_code_issuances",
            [
                "ix_growth_code_issuances_source_payment_id",
                "ix_growth_code_issuances_source_order_id",
                "ix_growth_code_issuances_issued_by_admin_id",
                "ix_growth_code_issuances_issued_to_partner_account_id",
                "ix_growth_code_issuances_issued_to_user_id",
                "ix_growth_code_issuances_issuance_type",
                "ix_growth_code_issuances_growth_code_id",
            ],
        ),
        (
            "growth_codes",
            [
                "ix_growth_codes_revoked_by_admin_id",
                "ix_growth_codes_revoked_at",
                "ix_growth_codes_expires_at",
                "ix_growth_codes_starts_at",
                "ix_growth_codes_policy_version_id",
                "ix_growth_codes_auth_realm_id",
                "ix_growth_codes_storefront_id",
                "ix_growth_codes_batch_id",
                "ix_growth_codes_campaign_id",
                "ix_growth_codes_owner_partner_account_id",
                "ix_growth_codes_owner_user_id",
                "ix_growth_codes_issuer_admin_id",
                "ix_growth_codes_issuer_type",
                "ix_growth_codes_status",
                "ix_growth_codes_code_type",
                "ix_growth_codes_code_prefix",
                "ix_growth_codes_code_hash",
            ],
        ),
    ):
        for index_name in indexes:
            op.drop_index(index_name, table_name=table_name)
        op.drop_table(table_name)
