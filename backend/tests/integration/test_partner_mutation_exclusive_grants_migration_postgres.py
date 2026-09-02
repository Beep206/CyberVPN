from __future__ import annotations

import asyncio
import json
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

PREVIOUS_REVISION = "20260901_stream_group_lag"
CURRENT_REVISION = "20260901_partner_grant_exclusive"


async def _insert_grant(
    connection: asyncpg.Connection,
    *,
    workspace_id: uuid.UUID,
    resource_type: str,
    resource_uuid: uuid.UUID,
) -> uuid.UUID:
    """Insert a focused migration fixture without unrelated account setup."""

    grant_id = uuid.uuid4()
    # The isolated postgres user is the test superuser. Foreign-key triggers
    # are disabled only for this fixture insert; unique/check indexes remain
    # active and are the exact subject of this migration test.
    await connection.execute("SET session_replication_role = replica")
    try:
        await connection.execute(
            """
            INSERT INTO partner_remnawave_resource_grants (
                id, workspace_id, resource_type, resource_uuid,
                permission_keys, granted_by_admin_user_id, granted_at,
                revoked_by_admin_user_id, revoked_at, audit_reason
            ) VALUES ($1, $2, $3, $4, $5::json, $6, now(), NULL, NULL, $7)
            """,
            grant_id,
            workspace_id,
            resource_type,
            resource_uuid,
            json.dumps(["remnawave_read", "remnawave_write"]),
            uuid.uuid4(),
            "migration integration fixture",
        )
    finally:
        await connection.execute("SET session_replication_role = DEFAULT")
    return grant_id


@pytest.mark.asyncio
async def test_populated_exclusive_grants_upgrade_downgrade_conflict_and_reupgrade() -> None:
    database_name = f"cvpn_partner_mutation_grant_{uuid.uuid4().hex[:12]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    asyncpg_url = _asyncpg_url_for_database(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", PREVIOUS_REVISION)
        connection = await asyncpg.connect(asyncpg_url)
        try:
            first_workspace = uuid.uuid4()
            second_workspace = uuid.uuid4()
            profile_uuid = uuid.uuid4()
            await _insert_grant(
                connection,
                workspace_id=first_workspace,
                resource_type="profile",
                resource_uuid=profile_uuid,
            )
        finally:
            await connection.close()

        await asyncio.to_thread(_run_alembic, url, "upgrade", CURRENT_REVISION)
        connection = await asyncpg.connect(asyncpg_url)
        try:
            index_definition = await connection.fetchval(
                "SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_partner_remnawave_exclusive_active_resource'"
            )
            assert index_definition is not None
            assert "profile" in index_definition
            assert "integration" in index_definition
            with pytest.raises(asyncpg.UniqueViolationError):
                await _insert_grant(
                    connection,
                    workspace_id=second_workspace,
                    resource_type="profile",
                    resource_uuid=profile_uuid,
                )
        finally:
            await connection.close()

        await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION)
        connection = await asyncpg.connect(asyncpg_url)
        try:
            duplicate_grant_id = await _insert_grant(
                connection,
                workspace_id=second_workspace,
                resource_type="profile",
                resource_uuid=profile_uuid,
            )
        finally:
            await connection.close()

        blocked = await asyncio.to_thread(
            _run_alembic,
            url,
            "upgrade",
            CURRENT_REVISION,
            False,
        )
        assert blocked.returncode != 0
        assert "profile/integration grants must be reconciled" in blocked.stderr

        connection = await asyncpg.connect(asyncpg_url)
        try:
            assert await connection.fetchval("SELECT version_num FROM alembic_version") == PREVIOUS_REVISION
            await connection.execute(
                "UPDATE partner_remnawave_resource_grants SET revoked_at = now() WHERE id = $1",
                duplicate_grant_id,
            )
        finally:
            await connection.close()

        await asyncio.to_thread(_run_alembic, url, "upgrade", CURRENT_REVISION)
        await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION)
        await asyncio.to_thread(_run_alembic, url, "upgrade", CURRENT_REVISION)
    finally:
        await _drop_database(database_name)
