from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import asyncpg
import pytest

from tests.integration.test_partner_commission_contracts_migration_postgres import (
    _asyncpg_url_for_database,
    _create_database,
    _database_url,
    _drop_database,
    _run_alembic,
)

pytestmark = [pytest.mark.integration]

PREVIOUS_REVISION = "20260626_reg_access_idem"
GROWTH_V62_DB_REVISION = "20260627_growth_v62_db"
CURRENT_HEAD_REVISION = "20260901_partner_grant_exclusive"

NEW_TABLES = {
    "fx_provider_configs",
    "fx_provider_refresh_runs",
    "customer_connection_sessions",
}
FX_RATE_SNAPSHOT_COLUMNS = {
    "provider_config_id",
    "provider_priority",
    "approval_state",
    "approved_by_admin_id",
    "approved_at",
    "rejection_reason",
    "checksum",
    "raw_provider_payload_hash",
}
FX_RATE_SNAPSHOT_INDEXES = {
    "ix_fx_rate_snapshots_provider_config_id",
    "ix_fx_rate_snapshots_approval_state",
    "ix_fx_rate_snapshots_checksum",
    "ix_fx_rate_snapshots_approved_by_admin_id",
}
FX_RATE_SNAPSHOT_CONSTRAINTS = {
    "ck_fx_rate_snapshots_provider_priority_non_negative",
    "ck_fx_rate_snapshots_approval_state",
    "fk_fx_rate_snapshots_provider_config_id_fx_provider_configs",
    "fk_fx_rate_snapshots_approved_by_admin_id_admin_users",
}


@pytest.mark.asyncio
async def test_growth_v62_db_migration_clean_upgrade_downgrade_reupgrade() -> None:
    database_name = f"cvpn_v62_db_clean_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await conn.fetchval("select version_num from alembic_version") == CURRENT_HEAD_REVISION
            await _assert_v62_schema_present(conn)
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION)
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await conn.fetchval("select version_num from alembic_version") == PREVIOUS_REVISION
            for table_name in NEW_TABLES:
                assert await _table_exists(conn, table_name) is False
            assert FX_RATE_SNAPSHOT_COLUMNS.isdisjoint(await _column_names(conn, "fx_rate_snapshots"))
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await conn.fetchval("select version_num from alembic_version") == CURRENT_HEAD_REVISION
            await _assert_v62_schema_present(conn)
        finally:
            await conn.close()
    finally:
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_growth_v62_db_migration_backfills_existing_fx_and_enforces_idempotency() -> None:
    database_name = f"cvpn_v62_db_pop_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    fixture_now = datetime(2026, 6, 27, 12, 0, tzinfo=UTC)
    active_id = uuid.UUID("11111111-1111-4111-8111-111111111111")
    pending_id = uuid.UUID("22222222-2222-4222-8222-222222222222")
    disabled_id = uuid.UUID("33333333-3333-4333-8333-333333333333")
    expected_checksums = {
        active_id: "b3a8b0ae8e973fce6af21ba7ab7dd0f31abd338964ce7401b408af28cd36ec0f",
        pending_id: "07e47f0b7c1130e80596017100ceb86fdd0a679401a93be29fc11e429ce42f1e",
        disabled_id: "72782a3ab23ec1436110528d8d1810f7a56b6ddb77418d863bc1e64715aafc1f",
    }
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", PREVIOUS_REVISION)
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            await _insert_fx_snapshot(
                conn,
                snapshot_id=active_id,
                base_currency="EUR",
                quote_currency="USD",
                provider_key="ecb",
                observed_at=fixture_now - timedelta(minutes=30),
                status="active",
                metadata={
                    "provider_priority": 7,
                    "raw_provider_payload_hash": "sha256:provider-payload",
                },
            )
            await _insert_fx_snapshot(
                conn,
                snapshot_id=pending_id,
                base_currency="GBP",
                quote_currency="USD",
                provider_key="manual",
                observed_at=fixture_now - timedelta(minutes=20),
                status="pending_approval",
                metadata={},
            )
            await _insert_fx_snapshot(
                conn,
                snapshot_id=disabled_id,
                base_currency="USD",
                quote_currency="RUB",
                provider_key="disabled-provider",
                observed_at=fixture_now - timedelta(minutes=10),
                status="disabled",
                metadata={"provider_priority": "not-an-int"},
            )
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            rows = {
                row["id"]: row
                for row in await conn.fetch(
                    """
                    select id,
                           provider_priority,
                           approval_state,
                           checksum,
                           raw_provider_payload_hash
                    from fx_rate_snapshots
                    where id = any($1::uuid[])
                    """,
                    [active_id, pending_id, disabled_id],
                )
            }
            assert rows[active_id]["provider_priority"] == 7
            assert rows[active_id]["approval_state"] == "approved"
            assert rows[active_id]["raw_provider_payload_hash"] == "sha256:provider-payload"
            assert rows[pending_id]["provider_priority"] == 100
            assert rows[pending_id]["approval_state"] == "pending"
            assert rows[disabled_id]["provider_priority"] == 100
            assert rows[disabled_id]["approval_state"] == "approved"
            assert {item: rows[item]["checksum"] for item in expected_checksums} == expected_checksums

            await _assert_provider_config_constraints(conn)
            await _assert_refresh_run_constraints(conn)
            await _assert_connection_session_constraints(conn)
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION)
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            rows_after_reupgrade = {
                row["id"]: row["approval_state"]
                for row in await conn.fetch(
                    """
                    select id, approval_state
                    from fx_rate_snapshots
                    where id = any($1::uuid[])
                    """,
                    [active_id, pending_id, disabled_id],
                )
            }
            assert rows_after_reupgrade == {
                active_id: "approved",
                pending_id: "pending",
                disabled_id: "approved",
            }
            await _assert_v62_schema_present(conn)
        finally:
            await conn.close()
    finally:
        await _drop_database(database_name)


async def _assert_v62_schema_present(conn: asyncpg.Connection) -> None:
    for table_name in NEW_TABLES:
        assert await _table_exists(conn, table_name) is True
    assert FX_RATE_SNAPSHOT_COLUMNS.issubset(await _column_names(conn, "fx_rate_snapshots"))
    assert FX_RATE_SNAPSHOT_INDEXES.issubset(await _index_names(conn, "fx_rate_snapshots"))
    assert FX_RATE_SNAPSHOT_CONSTRAINTS.issubset(await _constraint_names(conn, "fx_rate_snapshots"))
    assert {
        "uq_fx_provider_configs_provider_key",
        "ck_fx_provider_configs_priority_non_negative",
        "ck_fx_provider_configs_stale_after_positive",
        "ck_fx_provider_configs_rate_ttl_positive",
    }.issubset(await _constraint_names(conn, "fx_provider_configs"))
    assert {
        "uq_fx_provider_refresh_runs_run_key",
        "ck_fx_provider_refresh_runs_status",
        "ck_fx_provider_refresh_runs_trigger_type",
    }.issubset(await _constraint_names(conn, "fx_provider_refresh_runs"))
    assert {
        "uq_customer_connection_sessions_user_config_hash",
        "uq_customer_connection_sessions_session_key_hash",
        "ck_customer_connection_sessions_source_surface",
        "ck_customer_connection_sessions_ack_surface",
        "ck_customer_connection_sessions_status",
        "ck_customer_connection_sessions_platform",
    }.issubset(await _constraint_names(conn, "customer_connection_sessions"))


async def _insert_fx_snapshot(
    conn: asyncpg.Connection,
    *,
    snapshot_id: uuid.UUID,
    base_currency: str,
    quote_currency: str,
    provider_key: str,
    observed_at: datetime,
    status: str,
    metadata: dict[str, object],
) -> None:
    await conn.execute(
        """
        insert into fx_rate_snapshots (
            id,
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
            metadata,
            created_at
        )
        values (
            $1, $2, $3, $4, $5, 'provider', $6, $7, $8, $8, $9, $10, $11::jsonb, $8
        )
        """,
        snapshot_id,
        base_currency,
        quote_currency,
        Decimal("1.1000"),
        Decimal("0.90909090909091"),
        provider_key,
        f"{provider_key}:{snapshot_id}",
        observed_at,
        observed_at + timedelta(hours=1),
        status,
        json.dumps(metadata),
    )


async def _assert_provider_config_constraints(conn: asyncpg.Connection) -> None:
    provider_id = uuid.uuid4()
    await conn.execute(
        """
        insert into fx_provider_configs (
            id,
            provider_key,
            priority,
            enabled,
            supported_pairs,
            stale_after_seconds,
            rate_ttl_seconds,
            requires_admin_approval
        )
        values (
            $1, 'ecb', 10, true, '[{"source":"EUR","target":"USD"}]'::jsonb, 3600, 7200, true
        )
        """,
        provider_id,
    )
    with pytest.raises(asyncpg.UniqueViolationError):
        await conn.execute(
            """
            insert into fx_provider_configs (
                id,
                provider_key,
                priority,
                enabled,
                supported_pairs,
                stale_after_seconds,
                rate_ttl_seconds,
                requires_admin_approval
            )
            values ($1, 'ecb', 20, true, '[]'::jsonb, 3600, 3600, true)
            """,
            uuid.uuid4(),
        )
    with pytest.raises(asyncpg.CheckViolationError):
        await conn.execute(
            """
            insert into fx_provider_configs (
                id,
                provider_key,
                priority,
                enabled,
                supported_pairs,
                stale_after_seconds,
                rate_ttl_seconds,
                requires_admin_approval
            )
            values ($1, 'bad-priority', -1, true, '[]'::jsonb, 3600, 3600, true)
            """,
            uuid.uuid4(),
        )


async def _assert_refresh_run_constraints(conn: asyncpg.Connection) -> None:
    started_at = datetime(2026, 6, 27, 0, 0, tzinfo=UTC)
    await conn.execute(
        """
        insert into fx_provider_refresh_runs (
            id,
            provider_key,
            run_key,
            status,
            trigger_type,
            started_at
        )
        values ($1, 'ecb', 'fx-refresh:ecb:2026-06-27T00', 'succeeded', 'scheduled', $2)
        """,
        uuid.uuid4(),
        started_at,
    )
    with pytest.raises(asyncpg.UniqueViolationError):
        await conn.execute(
            """
            insert into fx_provider_refresh_runs (
                id,
                provider_key,
                run_key,
                status,
                trigger_type,
                started_at
            )
            values ($1, 'ecb', 'fx-refresh:ecb:2026-06-27T00', 'succeeded', 'scheduled', $2)
            """,
            uuid.uuid4(),
            started_at,
        )
    with pytest.raises(asyncpg.CheckViolationError):
        await conn.execute(
            """
            insert into fx_provider_refresh_runs (
                id,
                provider_key,
                run_key,
                status,
                trigger_type,
                started_at
            )
            values ($1, 'ecb', 'fx-refresh:bad-status', 'done', 'scheduled', $2)
            """,
            uuid.uuid4(),
            started_at,
        )


async def _assert_connection_session_constraints(conn: asyncpg.Connection) -> None:
    user_id = uuid.uuid4()
    created_at = datetime(2026, 6, 27, 0, 0, tzinfo=UTC)
    expires_at = datetime(2026, 6, 27, 1, 0, tzinfo=UTC)
    await conn.execute(
        """
        insert into mobile_users (
            id,
            public_uid,
            email,
            password_hash,
            notification_prefs,
            totp_enabled,
            is_active,
            status,
            created_at,
            updated_at
        )
        values ($1, 99000001, 'v62-db-session@example.test', 'hash', '{}'::json, false, true, 'active', $2, $2)
        """,
        user_id,
        created_at,
    )
    await conn.execute(
        """
        insert into customer_connection_sessions (
            id,
            mobile_user_id,
            source_surface,
            status,
            subscription_config_hash,
            session_key_hash,
            selected_platform,
            expires_at
        )
        values ($1, $2, 'web', 'available', 'sha256:config-a', 'sha256:session-a', 'ios', $3)
        """,
        uuid.uuid4(),
        user_id,
        expires_at,
    )
    with pytest.raises(asyncpg.UniqueViolationError):
        await conn.execute(
            """
            insert into customer_connection_sessions (
                id,
                mobile_user_id,
                source_surface,
                status,
                subscription_config_hash,
                session_key_hash,
                selected_platform,
                expires_at
            )
            values (
                $1, $2, 'miniapp', 'available', 'sha256:config-a',
                'sha256:session-b', 'android', $3
            )
            """,
            uuid.uuid4(),
            user_id,
            expires_at,
        )
    with pytest.raises(asyncpg.UniqueViolationError):
        await conn.execute(
            """
            insert into customer_connection_sessions (
                id,
                mobile_user_id,
                source_surface,
                status,
                subscription_config_hash,
                session_key_hash,
                selected_platform,
                expires_at
            )
            values (
                $1, $2, 'telegram_bot', 'available', 'sha256:config-b',
                'sha256:session-a', 'linux', $3
            )
            """,
            uuid.uuid4(),
            user_id,
            expires_at,
        )
    with pytest.raises(asyncpg.CheckViolationError):
        await conn.execute(
            """
            insert into customer_connection_sessions (
                id,
                mobile_user_id,
                source_surface,
                status,
                subscription_config_hash,
                selected_platform,
                expires_at
            )
            values ($1, $2, 'telegram_bot', 'available', 'sha256:config-c', 'beos', $3)
            """,
            uuid.uuid4(),
            user_id,
            expires_at,
        )


async def _table_exists(conn: asyncpg.Connection, table_name: str) -> bool:
    return (
        await conn.fetchval(
            "select to_regclass($1)",
            table_name,
        )
        is not None
    )


async def _column_names(conn: asyncpg.Connection, table_name: str) -> set[str]:
    rows = await conn.fetch(
        """
        select column_name
        from information_schema.columns
        where table_schema = 'public'
          and table_name = $1
        """,
        table_name,
    )
    return {row["column_name"] for row in rows}


async def _index_names(conn: asyncpg.Connection, table_name: str) -> set[str]:
    rows = await conn.fetch(
        """
        select indexname
        from pg_indexes
        where schemaname = 'public'
          and tablename = $1
        """,
        table_name,
    )
    return {row["indexname"] for row in rows}


async def _constraint_names(conn: asyncpg.Connection, table_name: str) -> set[str]:
    rows = await conn.fetch(
        """
        select conname
        from pg_constraint
        where conrelid = $1::regclass
        """,
        table_name,
    )
    return {row["conname"] for row in rows}
