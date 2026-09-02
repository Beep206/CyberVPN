from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

import asyncpg
import pytest
import pytest_asyncio

from tests.integration.test_partner_commission_contracts_migration_postgres import (
    _asyncpg_url_for_database,
    _create_database,
    _database_url,
    _drop_database,
    _run_alembic,
)

pytestmark = [pytest.mark.integration]

PREVIOUS_REVISION = "20260831_gift_redemption_safety"
CURRENT_REVISION = "20260901_stream_group_lag"


@dataclass(frozen=True, slots=True)
class _IsolatedPostgresDatabase:
    name: str
    sqlalchemy_url: str
    asyncpg_url: str


@pytest_asyncio.fixture
async def isolated_postgres_database() -> AsyncIterator[_IsolatedPostgresDatabase]:
    database_name = f"cvpn_stream_lag_mig_{uuid.uuid4().hex[:12]}"
    await _create_database(database_name)
    try:
        yield _IsolatedPostgresDatabase(
            name=database_name,
            sqlalchemy_url=_database_url(database_name),
            asyncpg_url=_asyncpg_url_for_database(database_name),
        )
    finally:
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_populated_checkpoint_survives_downgrade_reupgrade_with_nonnegative_lag_guard(
    isolated_postgres_database: _IsolatedPostgresDatabase,
) -> None:
    database = isolated_postgres_database
    await asyncio.to_thread(_run_alembic, database.sqlalchemy_url, "upgrade", PREVIOUS_REVISION)
    checkpoint_id = uuid.uuid4()
    connection = await asyncpg.connect(database.asyncpg_url)
    try:
        await connection.execute(
            """
            INSERT INTO remnawave_stream_checkpoints (
                id, stream_name, observed_group_pending_count,
                stream_exists, group_exists, updated_at
            ) VALUES ($1, 'subscription_requests', 0, true, true, now())
            """,
            checkpoint_id,
        )
    finally:
        await connection.close()

    await asyncio.to_thread(_run_alembic, database.sqlalchemy_url, "upgrade", CURRENT_REVISION)
    connection = await asyncpg.connect(database.asyncpg_url)
    try:
        assert await connection.fetchval("SELECT version_num FROM alembic_version") == CURRENT_REVISION
        assert (
            await connection.fetchval(
                "SELECT observed_group_lag FROM remnawave_stream_checkpoints WHERE id = $1",
                checkpoint_id,
            )
            is None
        )
        await connection.execute(
            "UPDATE remnawave_stream_checkpoints SET observed_group_lag = 7 WHERE id = $1",
            checkpoint_id,
        )
        with pytest.raises(asyncpg.CheckViolationError):
            await connection.execute(
                "UPDATE remnawave_stream_checkpoints SET observed_group_lag = -1 WHERE id = $1",
                checkpoint_id,
            )
        assert (
            await connection.fetchval(
                "SELECT observed_group_lag FROM remnawave_stream_checkpoints WHERE id = $1",
                checkpoint_id,
            )
            == 7
        )
    finally:
        await connection.close()

    await asyncio.to_thread(_run_alembic, database.sqlalchemy_url, "downgrade", PREVIOUS_REVISION)
    connection = await asyncpg.connect(database.asyncpg_url)
    try:
        assert await connection.fetchval("SELECT version_num FROM alembic_version") == PREVIOUS_REVISION
        assert (
            await connection.fetchval(
                """
                SELECT count(*)
                FROM information_schema.columns
                WHERE table_name = 'remnawave_stream_checkpoints'
                  AND column_name = 'observed_group_lag'
                """
            )
            == 0
        )
        assert (
            await connection.fetchval(
                "SELECT count(*) FROM remnawave_stream_checkpoints WHERE id = $1",
                checkpoint_id,
            )
            == 1
        )
    finally:
        await connection.close()

    await asyncio.to_thread(_run_alembic, database.sqlalchemy_url, "upgrade", CURRENT_REVISION)
    connection = await asyncpg.connect(database.asyncpg_url)
    try:
        assert await connection.fetchval("SELECT version_num FROM alembic_version") == CURRENT_REVISION
        assert (
            await connection.fetchval(
                "SELECT observed_group_lag FROM remnawave_stream_checkpoints WHERE id = $1",
                checkpoint_id,
            )
            is None
        )
    finally:
        await connection.close()
