"""Add flexible invite campaign system v7.

Revision ID: 20260628_invite_v7
Revises: 20260627_growth_v62_db
Create Date: 2026-06-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260628_invite_v7"
down_revision: str | Sequence[str] | None = "20260627_growth_v62_db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    json_type = _json_type(bind)
    json_empty_object = _json_default(bind, "{}")
    json_empty_array = _json_default(bind, "[]")

    op.create_table(
        "invite_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("owner_mode", sa.String(length=30), nullable=False, server_default="selected_user"),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allowed_surfaces", json_type, nullable=False, server_default=json_empty_array),
        sa.Column("allowed_geos", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("risk_policy", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("export_policy", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("notification_policy", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("caps", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("metadata", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('draft','scheduled','active','paused','archived')",
            name="ck_invite_campaigns_status",
        ),
        sa.CheckConstraint(
            "owner_mode IN "
            "('system','selected_user','uploaded_user_list','admin_pool','customer_owned','partner_owned')",
            name="ck_invite_campaigns_owner_mode",
        ),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["admin_users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_key", name="uq_invite_campaigns_campaign_key"),
    )
    _create_indexes(
        "invite_campaigns",
        (
            "campaign_key",
            "status",
            "owner_mode",
            "current_version_id",
            "starts_at",
            "expires_at",
            "created_by_admin_id",
            "updated_by_admin_id",
        ),
    )

    op.create_table(
        "invite_campaign_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("grant_mode", sa.String(length=30), nullable=False, server_default="legacy_invite_access"),
        sa.Column("grant_plan_id", sa.Uuid(), nullable=True),
        sa.Column("grant_duration_days", sa.Integer(), nullable=True),
        sa.Column("grant_snapshot", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("child_invite_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("child_invite_free_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("child_invite_expiry_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("child_grant_plan_id", sa.Uuid(), nullable=True),
        sa.Column("child_grant_duration_days", sa.Integer(), nullable=True),
        sa.Column("child_grant_snapshot", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("max_generation_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("block_self_redemption", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("require_no_active_access", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("allowed_surfaces", json_type, nullable=False, server_default=json_empty_array),
        sa.Column("risk_policy", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("redemption_policy", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("child_policy", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("issue_policy", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("export_policy", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("notification_policy", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("approved_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("published_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('draft','submitted','approved','published','rolled_back')",
            name="ck_invite_campaign_versions_status",
        ),
        sa.CheckConstraint(
            "grant_mode IN ('legacy_invite_access','plan_snapshot','custom_snapshot')",
            name="ck_invite_campaign_versions_grant_mode",
        ),
        sa.CheckConstraint("version >= 1", name="ck_invite_campaign_versions_version_positive"),
        sa.CheckConstraint("child_invite_count >= 0", name="ck_invite_campaign_versions_child_count_non_negative"),
        sa.CheckConstraint("max_generation_depth >= 0", name="ck_invite_campaign_versions_max_depth_non_negative"),
        sa.ForeignKeyConstraint(["campaign_id"], ["invite_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["grant_plan_id"], ["subscription_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["child_grant_plan_id"], ["subscription_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["admin_users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["published_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "version", name="uq_invite_campaign_versions_campaign_version"),
    )
    _create_indexes(
        "invite_campaign_versions",
        (
            "campaign_id",
            "status",
            "grant_mode",
            "grant_plan_id",
            "child_grant_plan_id",
            "checksum",
            "created_by_admin_id",
        ),
    )
    op.create_foreign_key(
        "fk_invite_campaigns_current_version_id",
        "invite_campaigns",
        "invite_campaign_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    with op.batch_alter_table("invite_codes") as batch_op:
        batch_op.alter_column("owner_user_id", existing_type=sa.Uuid(), nullable=True)
        batch_op.add_column(sa.Column("campaign_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("campaign_version_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("root_invite_code_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("parent_invite_code_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("generation_depth", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(
            sa.Column("grant_mode", sa.String(length=30), nullable=False, server_default="legacy_invite_access")
        )
        batch_op.add_column(sa.Column("grant_plan_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("grant_duration_days", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("grant_snapshot", json_type, nullable=False, server_default=json_empty_object))
        batch_op.add_column(sa.Column("child_grant_plan_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("child_grant_duration_days", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("child_policy", json_type, nullable=False, server_default=json_empty_object))
        batch_op.add_column(sa.Column("risk_policy", json_type, nullable=False, server_default=json_empty_object))
        batch_op.add_column(sa.Column("redemption_policy", json_type, nullable=False, server_default=json_empty_object))
        batch_op.add_column(sa.Column("issue_policy", json_type, nullable=False, server_default=json_empty_object))
        batch_op.create_foreign_key(
            "fk_invite_codes_campaign_id_invite_campaigns",
            "invite_campaigns",
            ["campaign_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_codes_campaign_version_id_invite_campaign_versions",
            "invite_campaign_versions",
            ["campaign_version_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_codes_root_invite_code_id_invite_codes",
            "invite_codes",
            ["root_invite_code_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_codes_parent_invite_code_id_invite_codes",
            "invite_codes",
            ["parent_invite_code_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_codes_grant_plan_id_subscription_plans",
            "subscription_plans",
            ["grant_plan_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_codes_child_grant_plan_id_subscription_plans",
            "subscription_plans",
            ["child_grant_plan_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_invite_codes_campaign_id", ["campaign_id"])
        batch_op.create_index("ix_invite_codes_campaign_version_id", ["campaign_version_id"])
        batch_op.create_index("ix_invite_codes_root_invite_code_id", ["root_invite_code_id"])
        batch_op.create_index("ix_invite_codes_parent_invite_code_id", ["parent_invite_code_id"])
        batch_op.create_index("ix_invite_codes_generation_depth", ["generation_depth"])
        batch_op.create_index("ix_invite_codes_grant_plan_id", ["grant_plan_id"])
        batch_op.create_index("ix_invite_codes_child_grant_plan_id", ["child_grant_plan_id"])
        batch_op.create_check_constraint(
            "ck_invite_codes_grant_mode",
            "grant_mode IN ('legacy_invite_access','plan_snapshot','custom_snapshot')",
        )
        batch_op.create_check_constraint(
            "ck_invite_codes_generation_depth_non_negative",
            "generation_depth >= 0",
        )

    with op.batch_alter_table("invite_batches") as batch_op:
        batch_op.alter_column("owner_user_id", existing_type=sa.Uuid(), nullable=True)
        batch_op.add_column(sa.Column("invite_campaign_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("invite_campaign_version_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("root_invite_code_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("parent_invite_code_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("root_owner_user_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("generation_depth", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("batch_kind", sa.String(length=40), nullable=False, server_default="legacy"))
        batch_op.add_column(
            sa.Column("grant_mode", sa.String(length=30), nullable=False, server_default="legacy_invite_access")
        )
        batch_op.add_column(sa.Column("grant_plan_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("grant_duration_days", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("grant_snapshot", json_type, nullable=False, server_default=json_empty_object))
        batch_op.add_column(sa.Column("child_grant_plan_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("child_grant_duration_days", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("child_policy", json_type, nullable=False, server_default=json_empty_object))
        batch_op.add_column(sa.Column("risk_policy", json_type, nullable=False, server_default=json_empty_object))
        batch_op.add_column(sa.Column("redemption_policy", json_type, nullable=False, server_default=json_empty_object))
        batch_op.add_column(sa.Column("issue_policy", json_type, nullable=False, server_default=json_empty_object))
        batch_op.create_foreign_key(
            "fk_invite_batches_invite_campaign_id_invite_campaigns",
            "invite_campaigns",
            ["invite_campaign_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_batches_invite_campaign_version_id",
            "invite_campaign_versions",
            ["invite_campaign_version_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_batches_root_invite_code_id_invite_codes",
            "invite_codes",
            ["root_invite_code_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_batches_parent_invite_code_id_invite_codes",
            "invite_codes",
            ["parent_invite_code_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_batches_root_owner_user_id_mobile_users",
            "mobile_users",
            ["root_owner_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_batches_grant_plan_id_subscription_plans",
            "subscription_plans",
            ["grant_plan_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_invite_batches_child_grant_plan_id_subscription_plans",
            "subscription_plans",
            ["child_grant_plan_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_invite_batches_invite_campaign_id", ["invite_campaign_id"])
        batch_op.create_index("ix_invite_batches_invite_campaign_version_id", ["invite_campaign_version_id"])
        batch_op.create_index("ix_invite_batches_root_invite_code_id", ["root_invite_code_id"])
        batch_op.create_index("ix_invite_batches_parent_invite_code_id", ["parent_invite_code_id"])
        batch_op.create_index("ix_invite_batches_root_owner_user_id", ["root_owner_user_id"])
        batch_op.create_index("ix_invite_batches_generation_depth", ["generation_depth"])
        batch_op.create_index("ix_invite_batches_batch_kind", ["batch_kind"])
        batch_op.create_index("ix_invite_batches_grant_plan_id", ["grant_plan_id"])
        batch_op.create_index("ix_invite_batches_child_grant_plan_id", ["child_grant_plan_id"])
        batch_op.create_check_constraint(
            "ck_invite_batches_generation_depth_non_negative",
            "generation_depth >= 0",
        )
        batch_op.create_check_constraint(
            "ck_invite_batches_grant_mode",
            "grant_mode IN ('legacy_invite_access','plan_snapshot','custom_snapshot')",
        )

    op.create_table(
        "invite_redemptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invite_code_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_version_id", sa.Uuid(), nullable=True),
        sa.Column("root_invite_code_id", sa.Uuid(), nullable=True),
        sa.Column("parent_invite_code_id", sa.Uuid(), nullable=True),
        sa.Column("inviter_user_id", sa.Uuid(), nullable=True),
        sa.Column("invitee_user_id", sa.Uuid(), nullable=False),
        sa.Column("generation_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_surface", sa.String(length=30), nullable=False, server_default="web"),
        sa.Column("entitlement_grant_id", sa.Uuid(), nullable=True),
        sa.Column("granted_plan_id", sa.Uuid(), nullable=True),
        sa.Column("granted_plan_code", sa.String(length=80), nullable=True),
        sa.Column("granted_duration_days", sa.Integer(), nullable=True),
        sa.Column("child_batch_id", sa.Uuid(), nullable=True),
        sa.Column("child_issued_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(length=220), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="redeemed"),
        sa.Column("blocked_reason", sa.String(length=160), nullable=True),
        sa.Column("risk_decision", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("grant_snapshot", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("service_snapshot", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("metadata", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('redeemed','blocked','reversed')",
            name="ck_invite_redemptions_status",
        ),
        sa.ForeignKeyConstraint(["invite_code_id"], ["invite_codes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["campaign_id"], ["invite_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["campaign_version_id"], ["invite_campaign_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["root_invite_code_id"], ["invite_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_invite_code_id"], ["invite_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inviter_user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invitee_user_id"], ["mobile_users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["entitlement_grant_id"], ["entitlement_grants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["granted_plan_id"], ["subscription_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["child_batch_id"], ["invite_batches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_invite_redemptions_idempotency_key"),
    )
    _create_indexes(
        "invite_redemptions",
        (
            "invite_code_id",
            "campaign_id",
            "campaign_version_id",
            "root_invite_code_id",
            "parent_invite_code_id",
            "inviter_user_id",
            "invitee_user_id",
            "entitlement_grant_id",
            "granted_plan_id",
            "granted_plan_code",
            "child_batch_id",
            "idempotency_key",
            "redeemed_at",
        ),
    )
    op.create_index(
        "uq_invite_redemptions_redeemed_invite_code_id",
        "invite_redemptions",
        ["invite_code_id"],
        unique=True,
        postgresql_where=sa.text("status = 'redeemed'"),
        sqlite_where=sa.text("status = 'redeemed'"),
    )

    with op.batch_alter_table("invite_codes") as batch_op:
        batch_op.add_column(sa.Column("source_redemption_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_invite_codes_source_redemption_id_invite_redemptions",
            "invite_redemptions",
            ["source_redemption_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_invite_codes_source_redemption_id", ["source_redemption_id"])

    with op.batch_alter_table("invite_batches") as batch_op:
        batch_op.add_column(sa.Column("source_redemption_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_invite_batches_source_redemption_id_invite_redemptions",
            "invite_redemptions",
            ["source_redemption_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_invite_batches_source_redemption_id", ["source_redemption_id"])

    op.create_table(
        "invite_tree_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("root_invite_code_id", sa.Uuid(), nullable=False),
        sa.Column("parent_invite_code_id", sa.Uuid(), nullable=True),
        sa.Column("redeemed_invite_code_id", sa.Uuid(), nullable=False),
        sa.Column("redemption_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_version_id", sa.Uuid(), nullable=True),
        sa.Column("child_batch_id", sa.Uuid(), nullable=True),
        sa.Column("granted_plan_id", sa.Uuid(), nullable=True),
        sa.Column("granted_plan_code", sa.String(length=80), nullable=True),
        sa.Column("inviter_user_id", sa.Uuid(), nullable=True),
        sa.Column("invitee_user_id", sa.Uuid(), nullable=False),
        sa.Column("generation_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('active','blocked','reversed')",
            name="ck_invite_tree_edges_status",
        ),
        sa.ForeignKeyConstraint(["root_invite_code_id"], ["invite_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_invite_code_id"], ["invite_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["redeemed_invite_code_id"], ["invite_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["redemption_id"], ["invite_redemptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["invite_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["campaign_version_id"], ["invite_campaign_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["child_batch_id"], ["invite_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["granted_plan_id"], ["subscription_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inviter_user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invitee_user_id"], ["mobile_users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("redemption_id", name="uq_invite_tree_edges_redemption_id"),
    )
    _create_indexes(
        "invite_tree_edges",
        (
            "root_invite_code_id",
            "parent_invite_code_id",
            "redeemed_invite_code_id",
            "campaign_id",
            "child_batch_id",
            "granted_plan_id",
            "inviter_user_id",
            "invitee_user_id",
        ),
    )

    op.create_table(
        "invite_tree_closure",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("root_invite_code_id", sa.Uuid(), nullable=False),
        sa.Column("ancestor_invite_code_id", sa.Uuid(), nullable=False),
        sa.Column("descendant_invite_code_id", sa.Uuid(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("depth >= 0", name="ck_invite_tree_closure_depth_non_negative"),
        sa.ForeignKeyConstraint(["root_invite_code_id"], ["invite_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ancestor_invite_code_id"], ["invite_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["descendant_invite_code_id"], ["invite_codes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "root_invite_code_id",
            "ancestor_invite_code_id",
            "descendant_invite_code_id",
            name="uq_invite_tree_closure_path",
        ),
    )
    _create_indexes(
        "invite_tree_closure",
        ("root_invite_code_id", "ancestor_invite_code_id", "descendant_invite_code_id"),
    )

    op.create_table(
        "invite_campaign_daily_rollups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_version_id", sa.Uuid(), nullable=True),
        sa.Column("rollup_date", sa.Date(), nullable=False),
        sa.Column("plan_code", sa.String(length=80), nullable=False, server_default="unknown"),
        sa.Column("source_surface", sa.String(length=30), nullable=False, server_default="all"),
        sa.Column("generation_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("issued_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("redeemed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expired_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revoked_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_vpn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("child_issued_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stats", json_type, nullable=False, server_default=json_empty_object),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["campaign_id"], ["invite_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_version_id"], ["invite_campaign_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "rollup_date",
            "plan_code",
            "source_surface",
            "generation_depth",
            name="uq_invite_campaign_daily_rollups_scope",
        ),
    )
    _create_indexes(
        "invite_campaign_daily_rollups",
        ("campaign_id", "campaign_version_id", "rollup_date"),
    )

    _backfill_legacy_invite_lineage(bind)


def downgrade() -> None:
    op.drop_table("invite_campaign_daily_rollups")
    op.drop_table("invite_tree_closure")
    op.drop_table("invite_tree_edges")

    with op.batch_alter_table("invite_batches") as batch_op:
        batch_op.drop_index("ix_invite_batches_source_redemption_id")
        batch_op.drop_constraint("fk_invite_batches_source_redemption_id_invite_redemptions", type_="foreignkey")
        batch_op.drop_column("source_redemption_id")

    with op.batch_alter_table("invite_codes") as batch_op:
        batch_op.drop_index("ix_invite_codes_source_redemption_id")
        batch_op.drop_constraint("fk_invite_codes_source_redemption_id_invite_redemptions", type_="foreignkey")
        batch_op.drop_column("source_redemption_id")

    op.drop_table("invite_redemptions")

    with op.batch_alter_table("invite_batches") as batch_op:
        for index_name in (
            "ix_invite_batches_child_grant_plan_id",
            "ix_invite_batches_grant_plan_id",
            "ix_invite_batches_batch_kind",
            "ix_invite_batches_generation_depth",
            "ix_invite_batches_root_owner_user_id",
            "ix_invite_batches_parent_invite_code_id",
            "ix_invite_batches_root_invite_code_id",
            "ix_invite_batches_invite_campaign_version_id",
            "ix_invite_batches_invite_campaign_id",
        ):
            batch_op.drop_index(index_name)
        batch_op.drop_constraint("ck_invite_batches_grant_mode", type_="check")
        batch_op.drop_constraint("ck_invite_batches_generation_depth_non_negative", type_="check")
        for constraint_name in (
            "fk_invite_batches_grant_plan_id_subscription_plans",
            "fk_invite_batches_child_grant_plan_id_subscription_plans",
            "fk_invite_batches_root_owner_user_id_mobile_users",
            "fk_invite_batches_parent_invite_code_id_invite_codes",
            "fk_invite_batches_root_invite_code_id_invite_codes",
            "fk_invite_batches_invite_campaign_version_id",
            "fk_invite_batches_invite_campaign_id_invite_campaigns",
        ):
            batch_op.drop_constraint(constraint_name, type_="foreignkey")
        for column_name in (
            "issue_policy",
            "redemption_policy",
            "risk_policy",
            "child_policy",
            "grant_snapshot",
            "grant_duration_days",
            "grant_plan_id",
            "child_grant_duration_days",
            "child_grant_plan_id",
            "grant_mode",
            "batch_kind",
            "generation_depth",
            "root_owner_user_id",
            "parent_invite_code_id",
            "root_invite_code_id",
            "invite_campaign_version_id",
            "invite_campaign_id",
        ):
            batch_op.drop_column(column_name)

    with op.batch_alter_table("invite_codes") as batch_op:
        for index_name in (
            "ix_invite_codes_child_grant_plan_id",
            "ix_invite_codes_grant_plan_id",
            "ix_invite_codes_generation_depth",
            "ix_invite_codes_parent_invite_code_id",
            "ix_invite_codes_root_invite_code_id",
            "ix_invite_codes_campaign_version_id",
            "ix_invite_codes_campaign_id",
        ):
            batch_op.drop_index(index_name)
        batch_op.drop_constraint("ck_invite_codes_generation_depth_non_negative", type_="check")
        batch_op.drop_constraint("ck_invite_codes_grant_mode", type_="check")
        for constraint_name in (
            "fk_invite_codes_grant_plan_id_subscription_plans",
            "fk_invite_codes_child_grant_plan_id_subscription_plans",
            "fk_invite_codes_parent_invite_code_id_invite_codes",
            "fk_invite_codes_root_invite_code_id_invite_codes",
            "fk_invite_codes_campaign_version_id_invite_campaign_versions",
            "fk_invite_codes_campaign_id_invite_campaigns",
        ):
            batch_op.drop_constraint(constraint_name, type_="foreignkey")
        for column_name in (
            "issue_policy",
            "redemption_policy",
            "risk_policy",
            "child_policy",
            "grant_snapshot",
            "grant_duration_days",
            "grant_plan_id",
            "child_grant_duration_days",
            "child_grant_plan_id",
            "grant_mode",
            "generation_depth",
            "parent_invite_code_id",
            "root_invite_code_id",
            "campaign_version_id",
            "campaign_id",
        ):
            batch_op.drop_column(column_name)

    op.drop_constraint("fk_invite_campaigns_current_version_id", "invite_campaigns", type_="foreignkey")
    op.drop_table("invite_campaign_versions")
    op.drop_table("invite_campaigns")


def _backfill_legacy_invite_lineage(bind: sa.Connection) -> None:
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                """
                UPDATE invite_codes
                   SET root_invite_code_id = id,
                       generation_depth = 0,
                       grant_mode = COALESCE(NULLIF(entitlement_mode, ''), 'legacy_invite_access'),
                       grant_plan_id = plan_id,
                       grant_duration_days = free_days,
                       grant_snapshot = COALESCE(NULLIF(entitlement_snapshot::text, '{}')::jsonb, '{}'::jsonb)
                 WHERE root_invite_code_id IS NULL
                """
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE invite_batches
                   SET batch_kind = CASE
                         WHEN source_type = 'growth_benefit' THEN 'growth_benefit'
                         WHEN source_type = 'admin_grant' THEN 'admin_grant'
                         ELSE 'legacy'
                       END,
                       root_owner_user_id = owner_user_id,
                       generation_depth = 0,
                       grant_mode = COALESCE(NULLIF(entitlement_mode, ''), 'legacy_invite_access'),
                       grant_plan_id = plan_id,
                       grant_duration_days = friend_days,
                       grant_snapshot = COALESCE(NULLIF(entitlement_snapshot::text, '{}')::jsonb, '{}'::jsonb)
                """
            )
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO invite_redemptions (
                    id,
                    invite_code_id,
                    root_invite_code_id,
                    parent_invite_code_id,
                    inviter_user_id,
                    invitee_user_id,
                    generation_depth,
                    source_surface,
                    idempotency_key,
                    status,
                    grant_snapshot,
                    redeemed_at,
                    created_at,
                    updated_at
                )
                SELECT gen_random_uuid(),
                       id,
                       COALESCE(root_invite_code_id, id),
                       parent_invite_code_id,
                       owner_user_id,
                       used_by_user_id,
                       generation_depth,
                       'legacy_backfill',
                       'legacy-invite:' || id::text || ':redeemer:' || used_by_user_id::text,
                       'redeemed',
                       COALESCE(NULLIF(entitlement_snapshot::text, '{}')::jsonb, '{}'::jsonb),
                       used_at,
                       COALESCE(used_at, created_at, now()),
                       now()
                  FROM invite_codes
                 WHERE is_used = true
                   AND used_by_user_id IS NOT NULL
                ON CONFLICT (idempotency_key) DO NOTHING
                """
            )
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO invite_tree_edges (
                    id,
                    root_invite_code_id,
                    parent_invite_code_id,
                    redeemed_invite_code_id,
                    redemption_id,
                    inviter_user_id,
                    invitee_user_id,
                    generation_depth,
                    status,
                    created_at,
                    updated_at
                )
                SELECT gen_random_uuid(),
                       COALESCE(r.root_invite_code_id, r.invite_code_id),
                       r.parent_invite_code_id,
                       r.invite_code_id,
                       r.id,
                       r.inviter_user_id,
                       r.invitee_user_id,
                       r.generation_depth,
                       'active',
                       COALESCE(r.redeemed_at, r.created_at, now()),
                       now()
                  FROM invite_redemptions r
                 WHERE r.status = 'redeemed'
                   AND r.inviter_user_id IS NOT NULL
                ON CONFLICT (redemption_id) DO NOTHING
                """
            )
        )
        bind.execute(
            sa.text(
                """
                WITH RECURSIVE paths AS (
                    SELECT COALESCE(root_invite_code_id, id) AS root_invite_code_id,
                           id AS ancestor_invite_code_id,
                           id AS descendant_invite_code_id,
                           0 AS depth
                      FROM invite_codes
                    UNION ALL
                    SELECT paths.root_invite_code_id,
                           paths.ancestor_invite_code_id,
                           child.id AS descendant_invite_code_id,
                           paths.depth + 1 AS depth
                      FROM paths
                      JOIN invite_codes child
                        ON child.parent_invite_code_id = paths.descendant_invite_code_id
                       AND COALESCE(child.root_invite_code_id, child.id) = paths.root_invite_code_id
                     WHERE paths.depth < 32
                )
                INSERT INTO invite_tree_closure (
                    id,
                    root_invite_code_id,
                    ancestor_invite_code_id,
                    descendant_invite_code_id,
                    depth,
                    created_at
                )
                SELECT gen_random_uuid(),
                       root_invite_code_id,
                       ancestor_invite_code_id,
                       descendant_invite_code_id,
                       depth,
                       now()
                  FROM paths
                ON CONFLICT (root_invite_code_id, ancestor_invite_code_id, descendant_invite_code_id) DO NOTHING
                """
            )
        )
        return

    bind.execute(
        sa.text(
            """
            UPDATE invite_codes
               SET root_invite_code_id = id,
                   generation_depth = 0,
                   grant_mode = COALESCE(NULLIF(entitlement_mode, ''), 'legacy_invite_access'),
                   grant_plan_id = plan_id,
                   grant_duration_days = free_days
             WHERE root_invite_code_id IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE invite_batches
               SET batch_kind = COALESCE(NULLIF(source_type, ''), 'legacy'),
                   root_owner_user_id = owner_user_id,
                   generation_depth = 0,
                   grant_mode = COALESCE(NULLIF(entitlement_mode, ''), 'legacy_invite_access'),
                   grant_plan_id = plan_id,
                   grant_duration_days = friend_days
            """
        )
    )


def _create_indexes(table_name: str, column_names: Sequence[str]) -> None:
    for column_name in column_names:
        op.create_index(f"ix_{table_name}_{column_name}", table_name, [column_name])


def _json_type(bind: sa.Connection) -> sa.types.TypeEngine:
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB()
    return sa.JSON()


def _json_default(bind: sa.Connection, value: str) -> sa.TextClause | str:
    if bind.dialect.name == "postgresql":
        return sa.text(f"'{value}'::jsonb")
    return value
