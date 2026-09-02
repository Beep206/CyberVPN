from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

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

PREVIOUS_REVISION = "20260626_onboard_idem"
REGISTRATION_ACCESS_IDEMPOTENCY_REVISION = "20260626_reg_access_idem"
CURRENT_HEAD_REVISION = "20260901_partner_grant_exclusive"


@pytest.mark.asyncio
async def test_postgres_registration_access_idempotency_migration_scrubs_raw_values_and_reupgrades() -> None:
    database_name = f"cvpn_reg_access_idem_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    raw_row_id = uuid.uuid4()
    hashed_row_id = uuid.uuid4()

    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", PREVIOUS_REVISION)
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            await _insert_registration_access_grant(
                conn,
                row_id=raw_row_id,
                token_hash="token-hash-raw",
                registration_idempotency_key="raw-registration-idem",
                metadata={
                    "exchange_idempotency_key": "raw-exchange-idem",
                    "note": "preserved",
                },
            )
            await _insert_registration_access_grant(
                conn,
                row_id=hashed_row_id,
                token_hash="token-hash-hashed",
                registration_idempotency_key="hmac:already-hashed-registration",
                metadata={
                    "exchange_idempotency_key_hash": "hmac:already-hashed-exchange",
                    "note": "already-safe",
                },
            )
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        expected_raw = _expected_scrubbed_state()
        await _assert_scrubbed_state(
            database_name,
            raw_row_id=raw_row_id,
            hashed_row_id=hashed_row_id,
            expected_raw=expected_raw,
            expected_revision=CURRENT_HEAD_REVISION,
        )

        await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION)
        await _assert_scrubbed_state(
            database_name,
            raw_row_id=raw_row_id,
            hashed_row_id=hashed_row_id,
            expected_raw=expected_raw,
            expected_revision=PREVIOUS_REVISION,
        )

        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        await _assert_scrubbed_state(
            database_name,
            raw_row_id=raw_row_id,
            hashed_row_id=hashed_row_id,
            expected_raw=expected_raw,
            expected_revision=CURRENT_HEAD_REVISION,
        )
    finally:
        await _drop_database(database_name)


async def _insert_registration_access_grant(
    conn: asyncpg.Connection,
    *,
    row_id: uuid.UUID,
    token_hash: str,
    registration_idempotency_key: str,
    metadata: dict[str, Any],
) -> None:
    now = datetime.now(UTC)
    await conn.execute(
        """
        insert into registration_access_grants (
            id,
            token_hash,
            status,
            role_key,
            issued_at,
            expires_at,
            exchanged_at,
            exchange_session_hash,
            reserved_at,
            reservation_key,
            registration_idempotency_key,
            metadata
        )
        values ($1, $2, 'reserved', 'customer', $3, $4, $3, $5, $3, $6, $7, $8::jsonb)
        """,
        row_id,
        token_hash,
        now,
        now + timedelta(hours=1),
        f"exchange-session-{token_hash}",
        f"reservation-{token_hash}",
        registration_idempotency_key,
        json.dumps(metadata),
    )


async def _assert_scrubbed_state(
    database_name: str,
    *,
    raw_row_id: uuid.UUID,
    hashed_row_id: uuid.UUID,
    expected_raw: dict[str, str],
    expected_revision: str,
) -> None:
    conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
    try:
        current_revision = await conn.fetchval("select version_num from alembic_version")
        assert current_revision == expected_revision

        raw_row = await _fetch_registration_access_grant(conn, raw_row_id)
        assert raw_row["registration_idempotency_key"] == expected_raw["registration_idempotency_key"]
        raw_metadata = _decode_metadata(raw_row["metadata"])
        assert raw_metadata["note"] == "preserved"
        assert raw_metadata["exchange_idempotency_key_present"] is True
        assert (
            raw_metadata["exchange_idempotency_key_legacy_sha256"]
            == expected_raw["exchange_idempotency_key_legacy_sha256"]
        )
        assert "exchange_idempotency_key" not in raw_metadata
        assert "raw-exchange-idem" not in json.dumps(raw_metadata, sort_keys=True)

        hashed_row = await _fetch_registration_access_grant(conn, hashed_row_id)
        assert hashed_row["registration_idempotency_key"] == "hmac:already-hashed-registration"
        hashed_metadata = _decode_metadata(hashed_row["metadata"])
        assert hashed_metadata == {
            "exchange_idempotency_key_hash": "hmac:already-hashed-exchange",
            "note": "already-safe",
        }
    finally:
        await conn.close()


async def _fetch_registration_access_grant(conn: asyncpg.Connection, row_id: uuid.UUID) -> asyncpg.Record:
    row = await conn.fetchrow(
        """
        select registration_idempotency_key, metadata
        from registration_access_grants
        where id = $1
        """,
        row_id,
    )
    assert row is not None
    return row


def _expected_scrubbed_state() -> dict[str, str]:
    return {
        "registration_idempotency_key": f"sha256:{_sha256('raw-registration-idem')}",
        "exchange_idempotency_key_legacy_sha256": _sha256("raw-exchange-idem"),
    }


def _decode_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        decoded = json.loads(value)
        assert isinstance(decoded, dict)
        return decoded
    raise AssertionError(f"Unexpected metadata value: {value!r}")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
