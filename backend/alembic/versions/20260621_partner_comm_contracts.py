"""Add immutable partner commission contracts.

Revision ID: 20260621_partner_comm_contracts
Revises: 20260621_partner_code_links
Create Date: 2026-06-21
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260621_partner_comm_contracts"
down_revision: str | Sequence[str] | None = "20260621_partner_code_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COMMISSION_CONTRACT_NAMESPACE = uuid.UUID("b8174d0e-5d20-458a-a03f-9f978d2c6f13")
_REFERENCE_TABLES = (
    "partner_codes",
    "partner_attribution_sessions",
    "customer_commercial_bindings",
    "order_attribution_results",
    "earning_events",
)
_REFERENCE_CONTRACT_ID_SQL = {
    "partner_codes": """
        SELECT DISTINCT commission_contract_id
        FROM partner_codes
        WHERE commission_contract_id IS NOT NULL
        """,
    "partner_attribution_sessions": """
        SELECT DISTINCT commission_contract_id
        FROM partner_attribution_sessions
        WHERE commission_contract_id IS NOT NULL
        """,
    "customer_commercial_bindings": """
        SELECT DISTINCT commission_contract_id
        FROM customer_commercial_bindings
        WHERE commission_contract_id IS NOT NULL
        """,
    "order_attribution_results": """
        SELECT DISTINCT commission_contract_id
        FROM order_attribution_results
        WHERE commission_contract_id IS NOT NULL
        """,
    "earning_events": """
        SELECT DISTINCT commission_contract_id
        FROM earning_events
        WHERE commission_contract_id IS NOT NULL
        """,
}
_REFERENCE_CODE_BACKFILL_SQL = {
    "partner_attribution_sessions": """
        UPDATE partner_attribution_sessions AS target
        SET commission_contract_id = code.commission_contract_id
        FROM partner_codes AS code
        WHERE target.commission_contract_id IS NULL
          AND target.partner_code_id = code.id
          AND code.commission_contract_id IS NOT NULL
        """,
    "customer_commercial_bindings": """
        UPDATE customer_commercial_bindings AS target
        SET commission_contract_id = code.commission_contract_id
        FROM partner_codes AS code
        WHERE target.commission_contract_id IS NULL
          AND target.partner_code_id = code.id
          AND code.commission_contract_id IS NOT NULL
        """,
    "order_attribution_results": """
        UPDATE order_attribution_results AS target
        SET commission_contract_id = code.commission_contract_id
        FROM partner_codes AS code
        WHERE target.commission_contract_id IS NULL
          AND target.partner_code_id = code.id
          AND code.commission_contract_id IS NOT NULL
        """,
    "earning_events": """
        UPDATE earning_events AS target
        SET commission_contract_id = code.commission_contract_id
        FROM partner_codes AS code
        WHERE target.commission_contract_id IS NULL
          AND target.partner_code_id = code.id
          AND code.commission_contract_id IS NOT NULL
        """,
}


def _uuid_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.Uuid()


def _json_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_default(payload: str) -> sa.TextClause:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.text(f"'{payload}'::jsonb")
    return sa.text(f"'{payload}'")


def upgrade() -> None:
    bind = op.get_bind()
    uuid_type = _uuid_type()
    json_type = _json_type()

    _widen_earning_event_money_columns()
    _add_earning_event_component_invariant()

    op.create_table(
        "partner_commission_contracts",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("partner_account_id", uuid_type, nullable=True),
        sa.Column("partner_user_id", uuid_type, nullable=True),
        sa.Column("partner_code_id", uuid_type, nullable=True),
        sa.Column("owner_type", sa.String(length=30), nullable=False, server_default="affiliate"),
        sa.Column("contract_status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("commission_model", sa.String(length=40), nullable=False, server_default="base_plus_markup"),
        sa.Column("commission_pct", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("markup_pct", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("markup_cap_amount", sa.Numeric(20, 8), nullable=True),
        sa.Column("payout_hold_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("currency_code", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("currency_policy", json_type, nullable=False, server_default=_json_default('{"minor_unit": 2}')),
        sa.Column("rounding_mode", sa.String(length=32), nullable=False, server_default="ROUND_HALF_UP"),
        sa.Column("renewal_policy", json_type, nullable=False, server_default=_json_default("{}")),
        sa.Column("refund_policy", json_type, nullable=False, server_default=_json_default("{}")),
        sa.Column("terms_snapshot", json_type, nullable=False, server_default=_json_default("{}")),
        sa.Column("source", sa.String(length=60), nullable=False, server_default="legacy_backfill"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["partner_account_id"], ["partner_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_user_id"], ["mobile_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_code_id"], ["partner_codes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("commission_pct >= 0", name="ck_partner_commission_contracts_commission_pct_nonnegative"),
        sa.CheckConstraint("markup_pct >= 0", name="ck_partner_commission_contracts_markup_pct_nonnegative"),
        sa.CheckConstraint("payout_hold_days >= 0", name="ck_partner_commission_contracts_hold_days_nonnegative"),
    )
    op.create_index(
        "ix_partner_commission_contracts_partner_account_id",
        "partner_commission_contracts",
        ["partner_account_id"],
    )
    op.create_index(
        "ix_partner_commission_contracts_partner_user_id",
        "partner_commission_contracts",
        ["partner_user_id"],
    )
    op.create_index(
        "ix_partner_commission_contracts_partner_code_id",
        "partner_commission_contracts",
        ["partner_code_id"],
    )
    op.create_index(
        "ix_partner_commission_contracts_contract_status",
        "partner_commission_contracts",
        ["contract_status"],
    )

    _backfill_contracts(bind)
    _backfill_references_from_partner_codes(bind)
    _backfill_order_and_earning_snapshots(bind)
    _add_reference_fks()


def downgrade() -> None:
    _assert_downgrade_safe()

    for table_name, constraint_name in (
        ("earning_events", "fk_earning_events_commission_contract_id"),
        ("order_attribution_results", "fk_order_attribution_results_commission_contract_id"),
        ("customer_commercial_bindings", "fk_customer_commercial_bindings_commission_contract_id"),
        ("partner_attribution_sessions", "fk_partner_attribution_sessions_commission_contract_id"),
        ("partner_codes", "fk_partner_codes_commission_contract_id"),
    ):
        op.drop_constraint(constraint_name, table_name, type_="foreignkey")

    op.drop_index("ix_partner_commission_contracts_contract_status", table_name="partner_commission_contracts")
    op.drop_index("ix_partner_commission_contracts_partner_code_id", table_name="partner_commission_contracts")
    op.drop_index("ix_partner_commission_contracts_partner_user_id", table_name="partner_commission_contracts")
    op.drop_index("ix_partner_commission_contracts_partner_account_id", table_name="partner_commission_contracts")
    op.drop_table("partner_commission_contracts")
    _drop_earning_event_component_invariant()
    _narrow_earning_event_money_columns()


def _assert_downgrade_safe() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    unsafe_reason = _unsafe_downgrade_reason(bind)
    if unsafe_reason is None:
        return

    raise RuntimeError(
        "Cannot downgrade 20260621_partner_comm_contracts after live partner commission contract writes: "
        f"{unsafe_reason}. This downgrade would discard immutable contract history or reduce recorded earning "
        "precision; export/reconcile the affected rows or restore from backup before rolling back."
    )


def _unsafe_downgrade_reason(bind: sa.Connection) -> str | None:
    has_contract_rotation = bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM partner_commission_contracts
                WHERE partner_code_id IS NOT NULL
                GROUP BY partner_code_id
                HAVING COUNT(*) > 1
            )
            """
        )
    ).scalar()
    if has_contract_rotation:
        return "multiple commission contracts exist for the same partner code"

    has_historical_references = bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM order_attribution_results AS result
                JOIN partner_commission_contracts AS contract
                  ON result.commission_contract_id = contract.id
                JOIN partner_codes AS code
                  ON contract.partner_code_id = code.id
                WHERE code.commission_contract_id IS DISTINCT FROM result.commission_contract_id

                UNION ALL

                SELECT 1
                FROM earning_events AS earning
                JOIN partner_commission_contracts AS contract
                  ON earning.commission_contract_id = contract.id
                JOIN partner_codes AS code
                  ON contract.partner_code_id = code.id
                WHERE code.commission_contract_id IS DISTINCT FROM earning.commission_contract_id
            )
            """
        )
    ).scalar()
    if has_historical_references:
        return "historical orders or earning events reference superseded commission contracts"

    has_high_precision_earnings = bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM earning_events
                WHERE commission_base_amount <> ROUND(commission_base_amount, 2)
                   OR markup_amount <> ROUND(markup_amount, 2)
                   OR commission_amount <> ROUND(commission_amount, 2)
                   OR total_amount <> ROUND(total_amount, 2)
                   OR commission_pct <> ROUND(commission_pct, 2)
            )
            """
        )
    ).scalar()
    if has_high_precision_earnings:
        return "earning events contain values that cannot be represented by the previous numeric precision"

    return None


def _widen_earning_event_money_columns() -> None:
    for column_name in ("commission_base_amount", "markup_amount", "commission_amount", "total_amount"):
        op.alter_column(
            "earning_events",
            column_name,
            existing_type=sa.Numeric(12, 2),
            type_=sa.Numeric(20, 8),
            existing_nullable=False,
        )
    op.alter_column(
        "earning_events",
        "commission_pct",
        existing_type=sa.Numeric(8, 2),
        type_=sa.Numeric(10, 4),
        existing_nullable=False,
    )


def _add_earning_event_component_invariant() -> None:
    op.add_column(
        "earning_events",
        sa.Column(
            "earning_component",
            sa.String(length=40),
            nullable=False,
            server_default="partner_cash",
        ),
    )
    op.create_index(
        "ix_earning_events_earning_component",
        "earning_events",
        ["earning_component"],
    )
    op.create_index(
        "uq_earning_events_payment_account_component",
        "earning_events",
        ["payment_id", "partner_account_id", "earning_component"],
        unique=True,
    )
    op.create_index(
        "uq_earning_events_payment_user_component",
        "earning_events",
        ["payment_id", "partner_user_id", "earning_component"],
        unique=True,
    )


def _drop_earning_event_component_invariant() -> None:
    op.drop_index("uq_earning_events_payment_user_component", table_name="earning_events")
    op.drop_index("uq_earning_events_payment_account_component", table_name="earning_events")
    op.drop_index("ix_earning_events_earning_component", table_name="earning_events")
    op.drop_column("earning_events", "earning_component")


def _narrow_earning_event_money_columns() -> None:
    for column_name in ("commission_base_amount", "markup_amount", "commission_amount", "total_amount"):
        op.alter_column(
            "earning_events",
            column_name,
            existing_type=sa.Numeric(20, 8),
            type_=sa.Numeric(12, 2),
            existing_nullable=False,
        )
    op.alter_column(
        "earning_events",
        "commission_pct",
        existing_type=sa.Numeric(10, 4),
        type_=sa.Numeric(8, 2),
        existing_nullable=False,
    )


def _backfill_contracts(bind: sa.Connection) -> None:
    default_commission_pct = _read_base_commission_pct(bind)
    default_affiliate_hold_days = _read_hold_days(bind, owner_type="affiliate")
    default_performance_hold_days = _read_hold_days(bind, owner_type="performance")
    now = datetime.now(UTC)

    partner_code_rows = bind.execute(
        sa.text(
            """
            SELECT id, partner_account_id, partner_user_id, owner_type, markup_pct,
                   commission_contract_id, version, created_at
            FROM partner_codes
            ORDER BY created_at, id
            """
        )
    ).mappings()
    for row in partner_code_rows:
        code_id = _uuid(row["id"])
        contract_id = _uuid(row["commission_contract_id"]) if row["commission_contract_id"] else _contract_id(code_id)
        owner_type = str(row["owner_type"] or "affiliate")
        hold_days = default_performance_hold_days if owner_type == "performance" else default_affiliate_hold_days
        _insert_contract(
            bind,
            contract_id=contract_id,
            partner_account_id=_optional_uuid(row["partner_account_id"]),
            partner_user_id=_optional_uuid(row["partner_user_id"]),
            partner_code_id=code_id,
            owner_type=owner_type,
            commission_pct=default_commission_pct,
            markup_pct=Decimal(str(row["markup_pct"] or 0)),
            payout_hold_days=hold_days,
            version=int(row["version"] or 1),
            source="legacy_partner_code_backfill",
            effective_from=row["created_at"] or now,
            snapshot_complete=True,
        )
        bind.execute(
            sa.text("UPDATE partner_codes SET commission_contract_id = :contract_id WHERE id = :code_id"),
            {"contract_id": str(contract_id), "code_id": str(code_id)},
        )

    known_ids = {
        _uuid(row["id"]) for row in bind.execute(sa.text("SELECT id FROM partner_commission_contracts")).mappings()
    }
    for sql in _REFERENCE_CONTRACT_ID_SQL.values():
        rows = bind.execute(sa.text(sql)).mappings()
        for row in rows:
            contract_id = _uuid(row["commission_contract_id"])
            if contract_id in known_ids:
                continue
            _insert_contract(
                bind,
                contract_id=contract_id,
                partner_account_id=None,
                partner_user_id=None,
                partner_code_id=None,
                owner_type="affiliate",
                commission_pct=Decimal("0"),
                markup_pct=Decimal("0"),
                payout_hold_days=default_affiliate_hold_days,
                version=1,
                source="legacy_soft_reference_backfill",
                effective_from=now,
                snapshot_complete=False,
                missing_terms=["partner_code_id", "partner_owner"],
            )
            known_ids.add(contract_id)


def _backfill_references_from_partner_codes(bind: sa.Connection) -> None:
    for sql in _REFERENCE_CODE_BACKFILL_SQL.values():
        bind.execute(sa.text(sql))


def _backfill_order_and_earning_snapshots(bind: sa.Connection) -> None:
    if bind.dialect.name != "postgresql":
        return
    bind.execute(
        sa.text(
            """
            WITH source AS (
                SELECT
                    target.id,
                    CASE
                        WHEN target.policy_snapshot::jsonb #>>
                                '{commercial_policy_snapshot,commission_contract_snapshot,snapshot_complete}' = 'true'
                            THEN target.policy_snapshot::jsonb #>
                                '{commercial_policy_snapshot,commission_contract_snapshot}'
                        ELSE contract.terms_snapshot
                            || jsonb_build_object(
                                'snapshot_complete', false,
                                'missing_terms', jsonb_build_array('historical_commission_snapshot'),
                                'snapshot_source', 'historical_inferred_backfill',
                                'inferred_from_current_config', true
                            )
                    END AS commission_contract_snapshot
                FROM order_attribution_results AS target
                JOIN partner_commission_contracts AS contract
                  ON target.commission_contract_id = contract.id
                WHERE target.owner_type <> 'none'
            )
            UPDATE order_attribution_results AS target
            SET policy_snapshot = jsonb_set(
                COALESCE(target.policy_snapshot::jsonb, '{}'::jsonb),
                '{commercial_policy_snapshot}',
                COALESCE(target.policy_snapshot::jsonb->'commercial_policy_snapshot', '{}'::jsonb)
                    || jsonb_build_object(
                        'commission_contract_snapshot',
                        source.commission_contract_snapshot
                    ),
                true
            )::json
            FROM source
            WHERE target.id = source.id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            WITH source AS (
                SELECT
                    target.id,
                    CASE
                        WHEN target.calculation_snapshot::jsonb #>>
                                '{commission_contract_snapshot,snapshot_complete}' = 'true'
                            THEN target.calculation_snapshot::jsonb #> '{commission_contract_snapshot}'
                        ELSE contract.terms_snapshot
                            || jsonb_build_object(
                                'snapshot_complete', false,
                                'missing_terms', jsonb_build_array('historical_commission_snapshot'),
                                'snapshot_source', 'historical_inferred_backfill',
                                'inferred_from_current_config', true
                            )
                    END AS commission_contract_snapshot
                FROM earning_events AS target
                JOIN partner_commission_contracts AS contract
                  ON target.commission_contract_id = contract.id
            )
            UPDATE earning_events AS target
            SET calculation_snapshot = jsonb_set(
                COALESCE(target.calculation_snapshot::jsonb, '{}'::jsonb),
                '{commission_contract_snapshot}',
                source.commission_contract_snapshot,
                true
            )::json
            FROM source
            WHERE target.id = source.id
            """
        )
    )


def _add_reference_fks() -> None:
    for table_name, constraint_name in (
        ("partner_codes", "fk_partner_codes_commission_contract_id"),
        ("partner_attribution_sessions", "fk_partner_attribution_sessions_commission_contract_id"),
        ("customer_commercial_bindings", "fk_customer_commercial_bindings_commission_contract_id"),
        ("order_attribution_results", "fk_order_attribution_results_commission_contract_id"),
        ("earning_events", "fk_earning_events_commission_contract_id"),
    ):
        op.create_foreign_key(
            constraint_name,
            table_name,
            "partner_commission_contracts",
            ["commission_contract_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def _insert_contract(
    bind: sa.Connection,
    *,
    contract_id: uuid.UUID,
    partner_account_id: uuid.UUID | None,
    partner_user_id: uuid.UUID | None,
    partner_code_id: uuid.UUID | None,
    owner_type: str,
    commission_pct: Decimal,
    markup_pct: Decimal,
    payout_hold_days: int,
    version: int,
    source: str,
    effective_from: datetime,
    snapshot_complete: bool,
    missing_terms: list[str] | None = None,
) -> None:
    snapshot = _contract_snapshot(
        contract_id=contract_id,
        partner_account_id=partner_account_id,
        partner_user_id=partner_user_id,
        partner_code_id=partner_code_id,
        owner_type=owner_type,
        commission_pct=commission_pct,
        markup_pct=markup_pct,
        payout_hold_days=payout_hold_days,
        version=version,
        source=source,
        effective_from=effective_from,
        snapshot_complete=snapshot_complete,
        missing_terms=missing_terms or [],
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO partner_commission_contracts (
                id, partner_account_id, partner_user_id, partner_code_id, owner_type,
                contract_status, commission_model, commission_pct, markup_pct,
                markup_cap_amount, payout_hold_days, currency_code, currency_policy,
                rounding_mode, renewal_policy, refund_policy, terms_snapshot, source,
                version, effective_from, created_at, updated_at
            )
            VALUES (
                :id, :partner_account_id, :partner_user_id, :partner_code_id, :owner_type,
                'active', 'base_plus_markup', :commission_pct, :markup_pct,
                NULL, :payout_hold_days, 'USD', :currency_policy,
                'ROUND_HALF_UP', :renewal_policy, :refund_policy, :terms_snapshot, :source,
                :version, :effective_from, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {
            "id": str(contract_id),
            "partner_account_id": str(partner_account_id) if partner_account_id else None,
            "partner_user_id": str(partner_user_id) if partner_user_id else None,
            "partner_code_id": str(partner_code_id) if partner_code_id else None,
            "owner_type": owner_type,
            "commission_pct": str(commission_pct),
            "markup_pct": str(markup_pct),
            "payout_hold_days": payout_hold_days,
            "currency_policy": _json_param({"minor_unit": 2}),
            "renewal_policy": _json_param({"eligible": True, "source": source}),
            "refund_policy": _json_param({"clawback": "manual_review", "source": source}),
            "terms_snapshot": _json_param(snapshot),
            "source": source,
            "version": version,
            "effective_from": effective_from,
        },
    )


def _contract_snapshot(
    *,
    contract_id: uuid.UUID,
    partner_account_id: uuid.UUID | None,
    partner_user_id: uuid.UUID | None,
    partner_code_id: uuid.UUID | None,
    owner_type: str,
    commission_pct: Decimal,
    markup_pct: Decimal,
    payout_hold_days: int,
    version: int,
    source: str,
    effective_from: datetime,
    snapshot_complete: bool,
    missing_terms: list[str],
) -> dict:
    return {
        "calculation_version": "partner_earning_v3",
        "commission_contract_id": str(contract_id),
        "commission_model": "base_plus_markup",
        "commission_pct": str(commission_pct),
        "markup_pct": str(markup_pct),
        "markup_cap_amount": None,
        "payout_hold_days": payout_hold_days,
        "currency_code": "USD",
        "currency_policy": {"minor_unit": 2},
        "rounding_mode": "ROUND_HALF_UP",
        "renewal_policy": {"eligible": True, "source": source},
        "refund_policy": {"clawback": "manual_review", "source": source},
        "contract_version": version,
        "contract_status": "active",
        "effective_from": _iso(effective_from),
        "effective_to": None,
        "partner_account_id": str(partner_account_id) if partner_account_id else None,
        "partner_user_id": str(partner_user_id) if partner_user_id else None,
        "partner_code_id": str(partner_code_id) if partner_code_id else None,
        "owner_type": owner_type,
        "snapshot_complete": snapshot_complete,
        "missing_terms": missing_terms,
        "snapshot_source": source,
    }


def _read_base_commission_pct(bind: sa.Connection) -> Decimal:
    value = _read_config(bind, "partner.tiers")
    tiers = value.get("tiers", [{"min_clients": 0, "commission_pct": 20}]) if isinstance(value, dict) else []
    commission = Decimal("20")
    for tier in sorted(tiers or [], key=lambda item: int(item.get("min_clients", 0) or 0)):
        if int(tier.get("min_clients", 0) or 0) <= 0:
            commission = Decimal(str(tier.get("commission_pct", 0) or 0))
    return commission


def _read_hold_days(bind: sa.Connection, *, owner_type: str) -> int:
    key = "performance.payout_hold_days" if owner_type == "performance" else "affiliate.payout_hold_days"
    default_days = 45 if owner_type == "performance" else 30
    value = _read_config(bind, key)
    if isinstance(value, dict):
        try:
            return int(value.get("days", default_days))
        except (TypeError, ValueError):
            return default_days
    return default_days


def _read_config(bind: sa.Connection, key: str) -> dict | None:
    row = bind.execute(sa.text("SELECT value FROM system_config WHERE key = :key"), {"key": key}).first()
    if row is None:
        return None
    value = row[0]
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return None
        return loaded if isinstance(loaded, dict) else None
    return None


def _contract_id(partner_code_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(_COMMISSION_CONTRACT_NAMESPACE, f"partner_code:{partner_code_id}:commission-contract:v1")


def _uuid(value: object) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _optional_uuid(value: object) -> uuid.UUID | None:
    return None if value is None else _uuid(value)


def _json_param(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()
