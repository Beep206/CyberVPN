"""Add attribution touchpoints for Phase 3.

Revision ID: 20260418_phase3_attribution_touchpoints
Revises: 20260418_phase2_commissionability_scaffolding
Create Date: 2026-04-18 19:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260418_phase3_attribution_touchpoints"
down_revision: str | None = "20260418_phase2_commissionability_scaffolding"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attribution_touchpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("touchpoint_type", sa.String(length=40), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("auth_realm_id", sa.Uuid(), nullable=True),
        sa.Column("storefront_id", sa.Uuid(), nullable=True),
        sa.Column("quote_session_id", sa.Uuid(), nullable=True),
        sa.Column("checkout_session_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("partner_code_id", sa.Uuid(), nullable=True),
        sa.Column("sale_channel", sa.String(length=30), nullable=True),
        sa.Column("source_host", sa.String(length=255), nullable=True),
        sa.Column("source_path", sa.String(length=500), nullable=True),
        sa.Column("campaign_params", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("evidence_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["auth_realm_id"], ["auth_realms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["checkout_session_id"], ["checkout_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_code_id"], ["partner_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["quote_session_id"], ["quote_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["storefront_id"], ["storefronts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attribution_touchpoints_touchpoint_type"), "attribution_touchpoints", ["touchpoint_type"])
    op.create_index(op.f("ix_attribution_touchpoints_user_id"), "attribution_touchpoints", ["user_id"])
    op.create_index(op.f("ix_attribution_touchpoints_auth_realm_id"), "attribution_touchpoints", ["auth_realm_id"])
    op.create_index(op.f("ix_attribution_touchpoints_storefront_id"), "attribution_touchpoints", ["storefront_id"])
    op.create_index(
        op.f("ix_attribution_touchpoints_quote_session_id"),
        "attribution_touchpoints",
        ["quote_session_id"],
    )
    op.create_index(
        op.f("ix_attribution_touchpoints_checkout_session_id"),
        "attribution_touchpoints",
        ["checkout_session_id"],
    )
    op.create_index(op.f("ix_attribution_touchpoints_order_id"), "attribution_touchpoints", ["order_id"])
    op.create_index(
        op.f("ix_attribution_touchpoints_partner_code_id"),
        "attribution_touchpoints",
        ["partner_code_id"],
    )
    op.create_index(op.f("ix_attribution_touchpoints_sale_channel"), "attribution_touchpoints", ["sale_channel"])
    op.create_index(op.f("ix_attribution_touchpoints_occurred_at"), "attribution_touchpoints", ["occurred_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_attribution_touchpoints_occurred_at"), table_name="attribution_touchpoints")
    op.drop_index(op.f("ix_attribution_touchpoints_sale_channel"), table_name="attribution_touchpoints")
    op.drop_index(op.f("ix_attribution_touchpoints_partner_code_id"), table_name="attribution_touchpoints")
    op.drop_index(op.f("ix_attribution_touchpoints_order_id"), table_name="attribution_touchpoints")
    op.drop_index(op.f("ix_attribution_touchpoints_checkout_session_id"), table_name="attribution_touchpoints")
    op.drop_index(op.f("ix_attribution_touchpoints_quote_session_id"), table_name="attribution_touchpoints")
    op.drop_index(op.f("ix_attribution_touchpoints_storefront_id"), table_name="attribution_touchpoints")
    op.drop_index(op.f("ix_attribution_touchpoints_auth_realm_id"), table_name="attribution_touchpoints")
    op.drop_index(op.f("ix_attribution_touchpoints_user_id"), table_name="attribution_touchpoints")
    op.drop_index(op.f("ix_attribution_touchpoints_touchpoint_type"), table_name="attribution_touchpoints")
    op.drop_table("attribution_touchpoints")
