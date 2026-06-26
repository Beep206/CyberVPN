"""Growth Codes v6 migration preflight contract tests."""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import Engine


def _load_migration():
    migration_path = (
        Path(__file__).resolve().parents[2] / "alembic" / "versions" / "20260625_growth_codes_v6_foundation.py"
    )
    spec = importlib.util.spec_from_file_location("growth_codes_v6_foundation_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_hash(raw_code: str) -> str:
    secret = (os.environ.get("GROWTH_CODE_HASH_SECRET") or os.environ["JWT_SECRET"]).encode("utf-8")
    return hmac.new(secret, raw_code.strip().upper().encode("utf-8"), hashlib.sha256).hexdigest()


@contextmanager
def _sqlite_engine() -> Iterator[Engine]:
    engine = sa.create_engine("sqlite:///:memory:")
    try:
        yield engine
    finally:
        engine.dispose()


def _create_growth_code_namespace_table(conn: sa.Connection) -> None:
    conn.execute(
        sa.text(
            """
            CREATE TABLE growth_code_namespaces (
                normalized_code_hash TEXT PRIMARY KEY,
                canonical_growth_code_id TEXT NULL,
                code_type TEXT NOT NULL,
                status TEXT NOT NULL,
                legacy_source_type TEXT NULL,
                legacy_source_id TEXT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
    )


def test_growth_codes_v6_migration_blocks_canonical_cross_type_hash_collision() -> None:
    migration = _load_migration()
    with _sqlite_engine() as engine, engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE growth_codes (
                    id TEXT PRIMARY KEY,
                    code_hash TEXT NOT NULL,
                    code_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NULL
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO growth_codes (id, code_hash, code_type, status)
                VALUES
                    ('code-1', 'same-hash', 'promo', 'active'),
                    ('code-2', 'same-hash', 'invite', 'active')
                """
            )
        )

        with pytest.raises(RuntimeError, match="cross-type code collisions"):
            migration._assert_no_growth_code_namespace_collisions(conn)


def test_growth_codes_v6_legacy_collision_report_does_not_leak_raw_codes() -> None:
    migration = _load_migration()
    with _sqlite_engine() as engine, engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE promo_codes (id TEXT PRIMARY KEY, code TEXT NOT NULL)"))
        conn.execute(sa.text("CREATE TABLE invite_codes (id TEXT PRIMARY KEY, code TEXT NOT NULL)"))
        conn.execute(sa.text("CREATE TABLE gift_codes (id TEXT PRIMARY KEY, code TEXT NOT NULL)"))
        conn.execute(sa.text("CREATE TABLE mobile_users (id TEXT PRIMARY KEY, referral_code TEXT NULL)"))
        conn.execute(sa.text("CREATE TABLE partner_codes (id TEXT PRIMARY KEY, code TEXT NOT NULL)"))
        conn.execute(sa.text("INSERT INTO promo_codes (id, code) VALUES ('promo-1', 'SecretCode')"))
        conn.execute(sa.text("INSERT INTO invite_codes (id, code) VALUES ('invite-1', ' secretcode ')"))
        conn.execute(sa.text("INSERT INTO gift_codes (id, code) VALUES ('gift-1', 'SECRETCODE')"))
        conn.execute(sa.text("INSERT INTO mobile_users (id, referral_code) VALUES ('user-1', 'secretcode')"))
        conn.execute(sa.text("INSERT INTO partner_codes (id, code) VALUES ('partner-1', ' SecretCode ')"))

        expected_hash = _runtime_hash("SECRETCODE")
        with pytest.raises(RuntimeError) as exc_info:
            migration._assert_no_growth_code_namespace_collisions(conn)

        message = str(exc_info.value)
        assert "SECRETCODE" not in message
        assert "SecretCode" not in message
        assert expected_hash in message
        assert "sources=gift,invite,partner,promo,referral" in message


def test_growth_codes_v6_migration_blocks_canonical_legacy_hash_collision() -> None:
    migration = _load_migration()
    with _sqlite_engine() as engine, engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE growth_codes (
                    id TEXT PRIMARY KEY,
                    code_hash TEXT NOT NULL,
                    code_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NULL
                )
                """
            )
        )
        conn.execute(sa.text("CREATE TABLE invite_codes (id TEXT PRIMARY KEY, code TEXT NOT NULL)"))
        expected_hash = _runtime_hash("CrossType")
        conn.execute(
            sa.text(
                """
                INSERT INTO growth_codes (id, code_hash, code_type, status)
                VALUES ('code-1', :code_hash, 'promo', 'active')
                """
            ),
            {"code_hash": expected_hash},
        )
        conn.execute(sa.text("INSERT INTO invite_codes (id, code) VALUES ('invite-1', ' crosstype ')"))

        with pytest.raises(RuntimeError) as exc_info:
            migration._assert_no_growth_code_namespace_collisions(conn)

        message = str(exc_info.value)
        assert "CrossType" not in message
        assert "crosstype" not in message
        assert expected_hash in message
        assert "sources=invite,promo" in message


def test_growth_codes_v6_migration_blocks_duplicate_promo_payment_usages() -> None:
    migration = _load_migration()
    with _sqlite_engine() as engine, engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE promo_code_usages (
                    id TEXT PRIMARY KEY,
                    promo_code_id TEXT NOT NULL,
                    payment_id TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO promo_code_usages (id, promo_code_id, payment_id)
                VALUES
                    ('usage-1', 'promo-1', 'payment-1'),
                    ('usage-2', 'promo-1', 'payment-1')
                """
            )
        )

        with pytest.raises(RuntimeError, match="duplicate promo/payment usage rows"):
            migration._assert_no_duplicate_promo_payment_usages(conn)

        conn.execute(sa.text("DELETE FROM promo_code_usages WHERE id = 'usage-2'"))
        migration._assert_no_duplicate_promo_payment_usages(conn)


def test_growth_codes_v6_migration_blocks_orphan_invite_plan_ids() -> None:
    migration = _load_migration()
    with _sqlite_engine() as engine, engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE subscription_plans (id TEXT PRIMARY KEY)"))
        conn.execute(sa.text("CREATE TABLE invite_codes (id TEXT PRIMARY KEY, plan_id TEXT NULL)"))
        conn.execute(sa.text("INSERT INTO invite_codes (id, plan_id) VALUES ('invite-1', 'missing-plan')"))

        with pytest.raises(RuntimeError, match="orphan invite plan ids"):
            migration._assert_invite_plan_ids_resolve(conn)

        conn.execute(sa.text("INSERT INTO subscription_plans (id) VALUES ('missing-plan')"))
        migration._assert_invite_plan_ids_resolve(conn)


def test_growth_codes_v6_namespace_backfill_is_idempotent() -> None:
    migration = _load_migration()
    with _sqlite_engine() as engine, engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE growth_codes (
                    id TEXT PRIMARY KEY,
                    code_hash TEXT NOT NULL,
                    code_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NULL
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE TABLE growth_code_namespaces (
                    normalized_code_hash TEXT PRIMARY KEY,
                    canonical_growth_code_id TEXT NULL,
                    code_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO growth_codes (id, code_hash, code_type, status, created_at)
                VALUES ('code-1', 'hash-1', 'promo', 'active', '2026-06-25T00:00:00Z')
                """
            )
        )

        migration._backfill_growth_code_namespaces(conn)
        migration._backfill_growth_code_namespaces(conn)

        rows = conn.execute(sa.text("SELECT * FROM growth_code_namespaces")).mappings().all()
        assert rows == [
            {
                "normalized_code_hash": "hash-1",
                "canonical_growth_code_id": "code-1",
                "code_type": "promo",
                "status": "active",
                "created_at": "2026-06-25T00:00:00Z",
            }
        ]


def test_growth_codes_v6_namespace_backfill_populates_legacy_sources_idempotently() -> None:
    migration = _load_migration()
    with _sqlite_engine() as engine, engine.begin() as conn:
        _create_growth_code_namespace_table(conn)
        conn.execute(
            sa.text(
                """
                CREATE TABLE promo_codes (
                    id TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    is_active INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE TABLE invite_codes (
                    id TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE TABLE gift_codes (
                    id TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE TABLE mobile_users (
                    id TEXT PRIMARY KEY,
                    referral_code TEXT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE TABLE partner_codes (
                    id TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    lifecycle_status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO promo_codes (id, code, is_active, created_at)
                VALUES ('promo-1', ' PromoOne ', 0, '2026-06-25T00:00:01Z')
                """
            )
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO invite_codes (id, code, status, created_at)
                VALUES ('invite-1', 'InviteOne', 'issued', '2026-06-25T00:00:02Z')
                """
            )
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO gift_codes (id, code, status, created_at)
                VALUES ('gift-1', 'GiftOne', 'active', '2026-06-25T00:00:03Z')
                """
            )
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO mobile_users (id, referral_code, created_at)
                VALUES ('user-1', 'ReferOne', '2026-06-25T00:00:04Z')
                """
            )
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO partner_codes (id, code, lifecycle_status, created_at)
                VALUES ('partner-1', 'PartnerOne', 'paused', '2026-06-25T00:00:05Z')
                """
            )
        )

        migration._backfill_growth_code_namespaces(conn)
        migration._backfill_growth_code_namespaces(conn)

        rows = (
            conn.execute(
                sa.text(
                    """
                    SELECT
                        normalized_code_hash,
                        canonical_growth_code_id,
                        code_type,
                        status,
                        legacy_source_type,
                        legacy_source_id,
                        created_at
                    FROM growth_code_namespaces
                    ORDER BY legacy_source_type
                    """
                )
            )
            .mappings()
            .all()
        )
        assert rows == [
            {
                "normalized_code_hash": _runtime_hash("GiftOne"),
                "canonical_growth_code_id": None,
                "code_type": "gift",
                "status": "active",
                "legacy_source_type": "legacy_gift",
                "legacy_source_id": "gift-1",
                "created_at": "2026-06-25T00:00:03Z",
            },
            {
                "normalized_code_hash": _runtime_hash("InviteOne"),
                "canonical_growth_code_id": None,
                "code_type": "invite",
                "status": "issued",
                "legacy_source_type": "legacy_invite",
                "legacy_source_id": "invite-1",
                "created_at": "2026-06-25T00:00:02Z",
            },
            {
                "normalized_code_hash": _runtime_hash("PartnerOne"),
                "canonical_growth_code_id": None,
                "code_type": "partner",
                "status": "paused",
                "legacy_source_type": "legacy_partner",
                "legacy_source_id": "partner-1",
                "created_at": "2026-06-25T00:00:05Z",
            },
            {
                "normalized_code_hash": _runtime_hash(" PromoOne "),
                "canonical_growth_code_id": None,
                "code_type": "promo",
                "status": "inactive",
                "legacy_source_type": "legacy_promo",
                "legacy_source_id": "promo-1",
                "created_at": "2026-06-25T00:00:01Z",
            },
            {
                "normalized_code_hash": _runtime_hash("ReferOne"),
                "canonical_growth_code_id": None,
                "code_type": "referral",
                "status": "legacy",
                "legacy_source_type": "legacy_referral",
                "legacy_source_id": "user-1",
                "created_at": "2026-06-25T00:00:04Z",
            },
        ]


def test_growth_codes_v6_namespace_backfill_repopulates_after_downgrade_drop() -> None:
    migration = _load_migration()
    with _sqlite_engine() as engine, engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE promo_codes (
                    id TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    is_active INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO promo_codes (id, code, is_active, created_at)
                VALUES ('promo-1', 'ReUpgrade', 1, '2026-06-25T00:00:01Z')
                """
            )
        )

        _create_growth_code_namespace_table(conn)
        migration._backfill_growth_code_namespaces(conn)
        first_rows = conn.execute(sa.text("SELECT * FROM growth_code_namespaces")).mappings().all()

        conn.execute(sa.text("DROP TABLE growth_code_namespaces"))
        _create_growth_code_namespace_table(conn)
        migration._backfill_growth_code_namespaces(conn)
        second_rows = conn.execute(sa.text("SELECT * FROM growth_code_namespaces")).mappings().all()

        assert first_rows == second_rows
        assert second_rows == [
            {
                "normalized_code_hash": _runtime_hash("ReUpgrade"),
                "canonical_growth_code_id": None,
                "code_type": "promo",
                "status": "active",
                "legacy_source_type": "legacy_promo",
                "legacy_source_id": "promo-1",
                "created_at": "2026-06-25T00:00:01Z",
            }
        ]
