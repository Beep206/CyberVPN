from __future__ import annotations

import asyncio
import io
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.remnawave.connections_gateway import RemnawaveConnectionDropCommand
from src.presentation.api.v1.remnawave_connections import routes
from src.presentation.api.v1.remnawave_connections.drop_receipts import (
    RemnawaveConnectionDropReceiptRegistry,
)
from src.presentation.api.v1.remnawave_connections.job_registry import RemnawaveConnectionJobAudience
from tests.integration.test_partner_commission_contracts_migration_postgres import (
    _asyncpg_url_for_database,
    _create_database,
    _database_url,
    _drop_database,
    _run_alembic,
)

pytestmark = [pytest.mark.integration]

PREVIOUS_REVISION = "20260830_webhook_hmac_cleanup"
CURRENT_REVISION = "20260831_drop_receipts"
_HMAC_SECRET = b"connection-drop-migration-secret-0001"
_TERMINAL_KEY = "migration-terminal-key-0001"
_UNKNOWN_KEY = "migration-unknown-key-0001"
_TERMINAL_SCOPE = "customer:migration-terminal"
_UNKNOWN_SCOPE = "customer:migration-unknown"


@dataclass(frozen=True, slots=True)
class _IsolatedPostgresDatabase:
    name: str
    sqlalchemy_url: str
    asyncpg_url: str


@pytest_asyncio.fixture
async def isolated_postgres_database() -> AsyncIterator[_IsolatedPostgresDatabase]:
    database_name = f"cvpn_drop_receipt_mig_{uuid.uuid4().hex[:12]}"
    await _create_database(database_name)
    try:
        yield _IsolatedPostgresDatabase(
            name=database_name,
            sqlalchemy_url=_database_url(database_name),
            asyncpg_url=_asyncpg_url_for_database(database_name),
        )
    finally:
        await _drop_database(database_name)


async def _binary_receipt_snapshot(connection: asyncpg.Connection) -> bytes:
    """Return PostgreSQL binary COPY output for an exact ordered row snapshot."""

    output = io.BytesIO()
    await connection.copy_from_query(
        "SELECT * FROM remnawave_connection_drop_receipts ORDER BY receipt_id",
        output=output,
        format="binary",
    )
    return output.getvalue()


async def _assert_legacy_grant_contract(connection: asyncpg.Connection) -> None:
    assert (
        await connection.fetchval("SELECT to_regclass('public.uq_partner_remnawave_exclusive_active_resource')") is None
    )
    constraint = await connection.fetchval(
        """
        SELECT pg_get_constraintdef(oid, true)
        FROM pg_constraint
        WHERE conrelid = 'public.partner_remnawave_resource_grants'::regclass
          AND conname = 'ck_partner_remnawave_resource_type'
        """
    )
    assert constraint is not None
    assert "service_identity" not in constraint


async def _assert_current_grant_contract(connection: asyncpg.Connection) -> None:
    assert (
        await connection.fetchval("SELECT to_regclass('public.uq_partner_remnawave_exclusive_active_resource')")
        is not None
    )
    constraint = await connection.fetchval(
        """
        SELECT pg_get_constraintdef(oid, true)
        FROM pg_constraint
        WHERE conrelid = 'public.partner_remnawave_resource_grants'::regclass
          AND conname = 'ck_partner_remnawave_resource_type'
        """
    )
    assert constraint is not None
    assert "service_identity" in constraint


@pytest.mark.asyncio
async def test_receipts_survive_expand_only_downgrade_reupgrade_and_replay_without_provider_call(
    isolated_postgres_database: _IsolatedPostgresDatabase,
) -> None:
    database = isolated_postgres_database
    await asyncio.to_thread(_run_alembic, database.sqlalchemy_url, "upgrade", CURRENT_REVISION)

    terminal_actor_id = uuid.uuid4()
    unknown_actor_id = uuid.uuid4()
    command = RemnawaveConnectionDropCommand.model_validate(
        {
            "dropBy": {"by": "userIds", "userIds": [42]},
            "targetNodes": {"target": "allNodes"},
        }
    )

    engine = create_async_engine(database.sqlalchemy_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    terminal_gateway = AsyncMock()
    try:
        async with sessions() as db:
            terminal = await routes._execute_connection_drop(
                audience=RemnawaveConnectionJobAudience.CUSTOMER,
                actor_id=terminal_actor_id,
                scope=_TERMINAL_SCOPE,
                client_idempotency_key=_TERMINAL_KEY,
                command=command,
                gateway=terminal_gateway,
                receipts=RemnawaveConnectionDropReceiptRegistry(
                    db,
                    hmac_secret=_HMAC_SECRET,
                    terminal_ttl_seconds=86_400,
                ),
            )
        terminal_gateway.drop_once.assert_awaited_once()
        assert terminal.state == "accepted"
        assert terminal.expires_at is not None

        async with sessions() as db:
            unknown = await RemnawaveConnectionDropReceiptRegistry(
                db,
                hmac_secret=_HMAC_SECRET,
                terminal_ttl_seconds=86_400,
            ).reserve(
                audience=RemnawaveConnectionJobAudience.CUSTOMER,
                actor_id=unknown_actor_id,
                workspace_id=None,
                scope=_UNKNOWN_SCOPE,
                client_idempotency_key=_UNKNOWN_KEY,
                payload=command.canonical_payload(),
            )
        assert unknown.is_new is True
        assert unknown.record.state.value == "outcome_unknown"
        assert unknown.record.expires_at is None
    finally:
        await engine.dispose()

    connection = await asyncpg.connect(database.asyncpg_url)
    try:
        rows = await connection.fetch(
            """
            SELECT receipt_id, state, expires_at, reconciled_at,
                   reconciled_by_admin_id, reconciliation_reason,
                   reconciliation_reference
            FROM remnawave_connection_drop_receipts
            ORDER BY receipt_id
            """
        )
        assert len(rows) == 2
        rows_by_id = {row["receipt_id"]: row for row in rows}
        terminal_row = rows_by_id[terminal.receipt_id]
        unknown_row = rows_by_id[unknown.record.receipt_id]
        assert terminal_row["state"] == "accepted"
        assert terminal_row["expires_at"] is not None
        assert terminal_row["expires_at"] > datetime.now(UTC)
        assert unknown_row["state"] == "outcome_unknown"
        assert unknown_row["expires_at"] is None
        for row in (terminal_row, unknown_row):
            assert row["reconciled_at"] is None
            assert row["reconciled_by_admin_id"] is None
            assert row["reconciliation_reason"] is None
            assert row["reconciliation_reference"] is None
        before_downgrade = await _binary_receipt_snapshot(connection)
        await _assert_current_grant_contract(connection)
    finally:
        await connection.close()

    await asyncio.to_thread(_run_alembic, database.sqlalchemy_url, "downgrade", PREVIOUS_REVISION)
    connection = await asyncpg.connect(database.asyncpg_url)
    try:
        assert await connection.fetchval("SELECT version_num FROM alembic_version") == PREVIOUS_REVISION
        assert await connection.fetchval("SELECT to_regclass('public.remnawave_connection_drop_receipts')") is not None
        assert await _binary_receipt_snapshot(connection) == before_downgrade
        await _assert_legacy_grant_contract(connection)
    finally:
        await connection.close()

    await asyncio.to_thread(_run_alembic, database.sqlalchemy_url, "upgrade", CURRENT_REVISION)
    connection = await asyncpg.connect(database.asyncpg_url)
    try:
        assert await connection.fetchval("SELECT version_num FROM alembic_version") == CURRENT_REVISION
        assert await _binary_receipt_snapshot(connection) == before_downgrade
        await _assert_current_grant_contract(connection)
    finally:
        await connection.close()

    replay_engine = create_async_engine(database.sqlalchemy_url, pool_pre_ping=True)
    replay_sessions = async_sessionmaker(replay_engine, class_=AsyncSession, expire_on_commit=False)
    replay_gateway = AsyncMock()
    try:
        async with replay_sessions() as db:
            terminal_replay = await routes._execute_connection_drop(
                audience=RemnawaveConnectionJobAudience.CUSTOMER,
                actor_id=terminal_actor_id,
                scope=_TERMINAL_SCOPE,
                client_idempotency_key=_TERMINAL_KEY,
                command=command,
                gateway=replay_gateway,
                receipts=RemnawaveConnectionDropReceiptRegistry(
                    db,
                    hmac_secret=_HMAC_SECRET,
                    terminal_ttl_seconds=86_400,
                ),
            )
        async with replay_sessions() as db:
            unknown_replay = await routes._execute_connection_drop(
                audience=RemnawaveConnectionJobAudience.CUSTOMER,
                actor_id=unknown_actor_id,
                scope=_UNKNOWN_SCOPE,
                client_idempotency_key=_UNKNOWN_KEY,
                command=command,
                gateway=replay_gateway,
                receipts=RemnawaveConnectionDropReceiptRegistry(
                    db,
                    hmac_secret=_HMAC_SECRET,
                    terminal_ttl_seconds=86_400,
                ),
            )

        assert terminal_replay.receipt_id == terminal.receipt_id
        assert terminal_replay.state == "accepted"
        assert unknown_replay.receipt_id == unknown.record.receipt_id
        assert unknown_replay.state == "outcome_unknown"
        assert unknown_replay.requires_reconciliation is True
        replay_gateway.drop_once.assert_not_awaited()
    finally:
        await replay_engine.dispose()


@pytest.mark.asyncio
async def test_incompatible_shadow_receipt_table_fails_closed_before_grant_ddl(
    isolated_postgres_database: _IsolatedPostgresDatabase,
) -> None:
    database = isolated_postgres_database
    await asyncio.to_thread(_run_alembic, database.sqlalchemy_url, "upgrade", PREVIOUS_REVISION)

    sentinel_id = uuid.uuid4()
    connection = await asyncpg.connect(database.asyncpg_url)
    try:
        await connection.execute(
            """
            CREATE TABLE remnawave_connection_drop_receipts (
                id uuid PRIMARY KEY,
                marker text NOT NULL
            )
            """
        )
        await connection.execute(
            "INSERT INTO remnawave_connection_drop_receipts (id, marker) VALUES ($1, $2)",
            sentinel_id,
            "shadow-table-sentinel",
        )
        await _assert_legacy_grant_contract(connection)
    finally:
        await connection.close()

    failed = await asyncio.to_thread(
        _run_alembic,
        database.sqlalchemy_url,
        "upgrade",
        CURRENT_REVISION,
        False,
    )
    assert failed.returncode != 0
    assert "Retained Remnawave connection-drop receipt table has an incompatible exact schema" in (
        failed.stdout + failed.stderr
    )

    connection = await asyncpg.connect(database.asyncpg_url)
    try:
        assert await connection.fetchval("SELECT version_num FROM alembic_version") == PREVIOUS_REVISION
        assert (
            await connection.fetchval(
                "SELECT marker FROM remnawave_connection_drop_receipts WHERE id = $1",
                sentinel_id,
            )
            == "shadow-table-sentinel"
        )
        await _assert_legacy_grant_contract(connection)
    finally:
        await connection.close()
