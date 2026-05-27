"""MSUB-08 subscription-scoped service identities."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260527_msub08_service_identity"
down_revision = "20260522_s1_plan_traffic_bigint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_identities",
        sa.Column(
            "identity_scope",
            sa.String(length=40),
            nullable=False,
            server_default="account",
        ),
    )
    op.add_column(
        "service_identities",
        sa.Column("subscription_key", sa.String(length=220), nullable=True),
    )
    op.create_index(
        "ix_service_identities_identity_scope",
        "service_identities",
        ["identity_scope"],
    )
    op.create_index(
        "ix_service_identities_subscription_key",
        "service_identities",
        ["subscription_key"],
    )

    op.drop_constraint(
        "uq_service_identities_customer_realm_provider",
        "service_identities",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_service_identities_scope_subscription",
        "service_identities",
        [
            "customer_account_id",
            "auth_realm_id",
            "provider_name",
            "identity_scope",
            "subscription_key",
        ],
    )
    op.create_index(
        "uq_service_identities_account_scope_provider",
        "service_identities",
        ["customer_account_id", "auth_realm_id", "provider_name"],
        unique=True,
        postgresql_where=sa.text("identity_scope = 'account'"),
    )


def downgrade() -> None:
    op.drop_index("uq_service_identities_account_scope_provider", table_name="service_identities")
    op.drop_constraint(
        "uq_service_identities_scope_subscription",
        "service_identities",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_service_identities_customer_realm_provider",
        "service_identities",
        ["customer_account_id", "auth_realm_id", "provider_name"],
    )
    op.drop_index("ix_service_identities_subscription_key", table_name="service_identities")
    op.drop_index("ix_service_identities_identity_scope", table_name="service_identities")
    op.drop_column("service_identities", "subscription_key")
    op.drop_column("service_identities", "identity_scope")
