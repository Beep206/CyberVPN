from __future__ import annotations

import asyncio
import uuid

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

PREVIOUS_REVISION = "20260701_invite_source_len"
CURRENT_REVISION = "20260711_plan_code_len"


async def _plan_code_length(conn: asyncpg.Connection) -> int:
    value = await conn.fetchval(
        """
        select character_maximum_length
        from information_schema.columns
        where table_schema = current_schema()
          and table_name = 'subscription_plans'
          and column_name = 'plan_code'
        """
    )
    assert isinstance(value, int)
    return value


@pytest.mark.asyncio
async def test_subscription_plan_code_widening_preserves_data_and_downgrade_is_safe() -> None:
    database_name = f"cvpn_plan_code_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    plan_id = uuid.uuid4()
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", PREVIOUS_REVISION)
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await _plan_code_length(conn) == 20
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "upgrade", CURRENT_REVISION)
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await _plan_code_length(conn) == 40
            await conn.execute(
                """
                insert into subscription_plans (
                    id, name, plan_code, display_name, duration_days,
                    device_limit, price_usd
                ) values ($1, $2, $3, $4, 0, 5, 0)
                """,
                plan_id,
                "Task2 migration fixture",
                "premium_spb_de_exceptions",
                "Task2 migration fixture",
            )
            assert (
                await conn.fetchval("select plan_code from subscription_plans where id = $1", plan_id)
                == "premium_spb_de_exceptions"
            )
        finally:
            await conn.close()

        downgrade = await asyncio.to_thread(
            _run_alembic,
            url,
            "downgrade",
            PREVIOUS_REVISION,
            False,
        )
        assert downgrade.returncode != 0
        assert "Cannot shrink subscription_plans.plan_code" in downgrade.stderr

        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await conn.fetchval("select version_num from alembic_version") == CURRENT_REVISION
            assert await _plan_code_length(conn) == 40
            assert (
                await conn.fetchval("select plan_code from subscription_plans where id = $1", plan_id)
                == "premium_spb_de_exceptions"
            )
            await conn.execute("delete from subscription_plans where id = $1", plan_id)
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION)
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await _plan_code_length(conn) == 20
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "upgrade", CURRENT_REVISION)
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await _plan_code_length(conn) == 40
        finally:
            await conn.close()
    finally:
        await _drop_database(database_name)
