"""Introduce canonical pricing catalog, add-ons, and mobile-user trial fields.

Revision ID: 20260416_pricing_catalog
Revises: 20260411_totp_secret
Create Date: 2026-04-16 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260416_pricing_catalog"
down_revision: str | None = "20260411_totp_secret"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("subscription_plans", sa.Column("plan_code", sa.String(length=20), nullable=True))
    op.add_column("subscription_plans", sa.Column("display_name", sa.String(length=100), nullable=False, server_default=""))
    op.add_column(
        "subscription_plans",
        sa.Column("catalog_visibility", sa.String(length=20), nullable=False, server_default="hidden"),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("sale_channels", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("traffic_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("connection_modes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("server_pool", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("support_sla", sa.String(length=20), nullable=False, server_default="standard"),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("dedicated_ip", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("invite_bundle", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("trial_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(op.f("ix_subscription_plans_plan_code"), "subscription_plans", ["plan_code"], unique=False)

    op.execute(
        """
        UPDATE subscription_plans
        SET display_name = COALESCE(NULLIF(display_name, ''), name),
            catalog_visibility = 'hidden',
            sale_channels = '["admin"]'::jsonb
        """
    )

    op.create_table(
        "plan_addons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("duration_mode", sa.String(length=30), nullable=False, server_default="inherits_subscription"),
        sa.Column("is_stackable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("quantity_step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("price_usd", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("price_rub", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_quantity_by_plan", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("delta_entitlements", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("requires_location", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sale_channels", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plan_addons_code"), "plan_addons", ["code"], unique=True)

    op.create_table(
        "subscription_addons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_addon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("location_code", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_addon_id"], ["plan_addons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["mobile_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subscription_addons_payment_id"), "subscription_addons", ["payment_id"], unique=False)
    op.create_index(op.f("ix_subscription_addons_plan_addon_id"), "subscription_addons", ["plan_addon_id"], unique=False)
    op.create_index(op.f("ix_subscription_addons_user_id"), "subscription_addons", ["user_id"], unique=False)

    op.add_column("payments", sa.Column("addons_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column(
        "payments",
        sa.Column("entitlements_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.add_column("mobile_users", sa.Column("trial_activated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("mobile_users", sa.Column("trial_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("mobile_users", "trial_expires_at")
    op.drop_column("mobile_users", "trial_activated_at")

    op.drop_column("payments", "entitlements_snapshot")
    op.drop_column("payments", "addons_snapshot")

    op.drop_index(op.f("ix_subscription_addons_user_id"), table_name="subscription_addons")
    op.drop_index(op.f("ix_subscription_addons_plan_addon_id"), table_name="subscription_addons")
    op.drop_index(op.f("ix_subscription_addons_payment_id"), table_name="subscription_addons")
    op.drop_table("subscription_addons")

    op.drop_index(op.f("ix_plan_addons_code"), table_name="plan_addons")
    op.drop_table("plan_addons")

    op.drop_index(op.f("ix_subscription_plans_plan_code"), table_name="subscription_plans")
    op.drop_column("subscription_plans", "trial_eligible")
    op.drop_column("subscription_plans", "invite_bundle")
    op.drop_column("subscription_plans", "dedicated_ip")
    op.drop_column("subscription_plans", "support_sla")
    op.drop_column("subscription_plans", "server_pool")
    op.drop_column("subscription_plans", "connection_modes")
    op.drop_column("subscription_plans", "traffic_policy")
    op.drop_column("subscription_plans", "sale_channels")
    op.drop_column("subscription_plans", "catalog_visibility")
    op.drop_column("subscription_plans", "display_name")
    op.drop_column("subscription_plans", "plan_code")
