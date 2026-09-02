from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.settings import settings
from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveConnectionDropReceiptModel
from src.infrastructure.remnawave.connections_gateway import RemnawaveConnectionDropCommand
from src.presentation.api.v1.remnawave_connections import routes
from src.presentation.api.v1.remnawave_connections.drop_receipts import (
    RemnawaveConnectionDropReceiptCapacityError,
    RemnawaveConnectionDropReceiptConflictError,
    RemnawaveConnectionDropReceiptRegistry,
    RemnawaveConnectionDropReceiptUnavailableError,
    RemnawaveConnectionDropState,
)
from src.presentation.api.v1.remnawave_connections.job_registry import RemnawaveConnectionJobAudience

_HMAC_SECRET = b"connections-drop-domain-secret-00000001"
_CLIENT_KEY = "postgres-drop-key-0001"


def _session_factory():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return engine, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.mark.integration
async def test_concurrent_drop_reservation_has_one_database_winner_and_restart_replays() -> None:
    actor_id = uuid4()
    payload = {
        "dropBy": {"by": "ipAddresses", "ipAddresses": ["203.0.113.77"]},
        "targetNodes": {"target": "allNodes"},
    }
    engine, sessions = _session_factory()
    try:
        async with sessions() as first_db, sessions() as second_db:
            reservations = await asyncio.gather(
                RemnawaveConnectionDropReceiptRegistry(first_db, hmac_secret=_HMAC_SECRET).reserve(
                    audience=RemnawaveConnectionJobAudience.ADMIN,
                    actor_id=actor_id,
                    workspace_id=None,
                    scope="admin:global",
                    client_idempotency_key=_CLIENT_KEY,
                    payload=payload,
                ),
                RemnawaveConnectionDropReceiptRegistry(second_db, hmac_secret=_HMAC_SECRET).reserve(
                    audience=RemnawaveConnectionJobAudience.ADMIN,
                    actor_id=actor_id,
                    workspace_id=None,
                    scope="admin:global",
                    client_idempotency_key=_CLIENT_KEY,
                    payload=payload,
                ),
            )

        assert sum(item.is_new for item in reservations) == 1
        assert len({item.record.receipt_id for item in reservations}) == 1

        async with sessions() as restarted_db:
            restarted = RemnawaveConnectionDropReceiptRegistry(restarted_db, hmac_secret=_HMAC_SECRET)
            replay = await restarted.reserve(
                audience=RemnawaveConnectionJobAudience.ADMIN,
                actor_id=actor_id,
                workspace_id=None,
                scope="admin:global",
                client_idempotency_key=_CLIENT_KEY,
                payload=payload,
            )
            assert replay.is_new is False
            assert replay.record.receipt_id == reservations[0].record.receipt_id
            assert replay.record.expires_at is None

            with pytest.raises(RemnawaveConnectionDropReceiptConflictError):
                await restarted.reserve(
                    audience=RemnawaveConnectionJobAudience.ADMIN,
                    actor_id=actor_id,
                    workspace_id=None,
                    scope="admin:global",
                    client_idempotency_key=_CLIENT_KEY,
                    payload={
                        "dropBy": {"by": "userIds", "userIds": [99]},
                        "targetNodes": {"target": "allNodes"},
                    },
                )

            stored = (
                await restarted_db.execute(
                    select(RemnawaveConnectionDropReceiptModel).where(
                        RemnawaveConnectionDropReceiptModel.actor_id == actor_id
                    )
                )
            ).scalar_one()
            assert stored.expires_at is None
            serialized = "|".join(
                (stored.key_hmac, stored.hmac_key_id, stored.scope_hmac, stored.payload_hmac, stored.receipt_id)
            )
            assert _CLIENT_KEY not in serialized
            assert "admin:global" not in serialized
            assert "203.0.113.77" not in serialized
    finally:
        async with sessions() as cleanup:
            await cleanup.execute(
                delete(RemnawaveConnectionDropReceiptModel).where(
                    RemnawaveConnectionDropReceiptModel.actor_id == actor_id
                )
            )
            await cleanup.commit()
        await engine.dispose()


@pytest.mark.integration
async def test_restart_replay_never_sends_connection_drop_to_provider_twice() -> None:
    actor_id = uuid4()
    command = RemnawaveConnectionDropCommand.model_validate(
        {
            "dropBy": {"by": "userIds", "userIds": [42]},
            "targetNodes": {"target": "allNodes"},
        }
    )
    gateway = AsyncMock()
    engine, sessions = _session_factory()
    try:
        async with sessions() as first_db:
            first = await routes._execute_connection_drop(
                audience=RemnawaveConnectionJobAudience.CUSTOMER,
                actor_id=actor_id,
                scope=f"customer:{actor_id}",
                client_idempotency_key=_CLIENT_KEY,
                command=command,
                gateway=gateway,
                receipts=RemnawaveConnectionDropReceiptRegistry(first_db, hmac_secret=_HMAC_SECRET),
            )
        async with sessions() as restarted_db:
            replay = await routes._execute_connection_drop(
                audience=RemnawaveConnectionJobAudience.CUSTOMER,
                actor_id=actor_id,
                scope=f"customer:{actor_id}",
                client_idempotency_key=_CLIENT_KEY,
                command=command,
                gateway=gateway,
                receipts=RemnawaveConnectionDropReceiptRegistry(restarted_db, hmac_secret=_HMAC_SECRET),
            )

        assert first.state == replay.state == "accepted"
        assert first.expires_at is not None
        assert first.expires_in_seconds is not None
        assert replay.expires_at == first.expires_at
        assert replay.requires_reconciliation is False
        assert gateway.drop_once.await_count == 1
    finally:
        async with sessions() as cleanup:
            await cleanup.execute(
                delete(RemnawaveConnectionDropReceiptModel).where(
                    RemnawaveConnectionDropReceiptModel.actor_id == actor_id
                )
            )
            await cleanup.commit()
        await engine.dispose()


@pytest.mark.integration
async def test_terminal_receipt_expires_but_unknown_replacement_does_not() -> None:
    actor_id = uuid4()
    start = datetime.now(UTC)
    payload = {
        "dropBy": {"by": "userIds", "userIds": [42]},
        "targetNodes": {"target": "allNodes"},
    }
    engine, sessions = _session_factory()
    try:
        async with sessions() as first_db:
            registry = RemnawaveConnectionDropReceiptRegistry(
                first_db,
                hmac_secret=_HMAC_SECRET,
                terminal_ttl_seconds=300,
                clock=lambda: start,
            )
            reserved = await registry.reserve(
                audience=RemnawaveConnectionJobAudience.ADMIN,
                actor_id=actor_id,
                workspace_id=None,
                scope="admin:global",
                client_idempotency_key=_CLIENT_KEY,
                payload=payload,
            )
            terminal = await registry.update_state(reserved, RemnawaveConnectionDropState.ACCEPTED)
            assert terminal.expires_at == start + timedelta(seconds=300)

        async with sessions() as later_db:
            replacement = await RemnawaveConnectionDropReceiptRegistry(
                later_db,
                hmac_secret=_HMAC_SECRET,
                terminal_ttl_seconds=300,
                clock=lambda: start + timedelta(seconds=301),
            ).reserve(
                audience=RemnawaveConnectionJobAudience.ADMIN,
                actor_id=actor_id,
                workspace_id=None,
                scope="admin:global",
                client_idempotency_key=_CLIENT_KEY,
                payload=payload,
            )
            assert replacement.is_new is True
            assert replacement.record.receipt_id != terminal.receipt_id
            assert replacement.record.state is RemnawaveConnectionDropState.OUTCOME_UNKNOWN
            assert replacement.record.expires_at is None
            rows = (
                (
                    await later_db.execute(
                        select(RemnawaveConnectionDropReceiptModel).where(
                            RemnawaveConnectionDropReceiptModel.actor_id == actor_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(rows) == 1
            assert rows[0].state == RemnawaveConnectionDropState.OUTCOME_UNKNOWN.value
            assert rows[0].expires_at is None
    finally:
        async with sessions() as cleanup:
            await cleanup.execute(
                delete(RemnawaveConnectionDropReceiptModel).where(
                    RemnawaveConnectionDropReceiptModel.actor_id == actor_id
                )
            )
            await cleanup.commit()
        await engine.dispose()


@pytest.mark.integration
async def test_hmac_rotation_with_active_unknown_receipt_fails_closed() -> None:
    actor_id = uuid4()
    payload = {
        "dropBy": {"by": "userIds", "userIds": [42]},
        "targetNodes": {"target": "allNodes"},
    }
    rotated_secret = b"connections-drop-domain-secret-00000002"
    engine, sessions = _session_factory()
    try:
        async with sessions() as first_db:
            await RemnawaveConnectionDropReceiptRegistry(first_db, hmac_secret=_HMAC_SECRET).reserve(
                audience=RemnawaveConnectionJobAudience.ADMIN,
                actor_id=actor_id,
                workspace_id=None,
                scope="admin:global",
                client_idempotency_key=_CLIENT_KEY,
                payload=payload,
            )

        async with sessions() as rotated_db:
            with pytest.raises(RemnawaveConnectionDropReceiptUnavailableError, match="HMAC key changed"):
                await RemnawaveConnectionDropReceiptRegistry(
                    rotated_db,
                    hmac_secret=rotated_secret,
                ).reserve(
                    audience=RemnawaveConnectionJobAudience.ADMIN,
                    actor_id=actor_id,
                    workspace_id=None,
                    scope="admin:global",
                    client_idempotency_key=_CLIENT_KEY,
                    payload=payload,
                )
            rows = (
                (
                    await rotated_db.execute(
                        select(RemnawaveConnectionDropReceiptModel).where(
                            RemnawaveConnectionDropReceiptModel.actor_id == actor_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(rows) == 1
            assert rows[0].state == RemnawaveConnectionDropState.OUTCOME_UNKNOWN.value
    finally:
        async with sessions() as cleanup:
            await cleanup.execute(
                delete(RemnawaveConnectionDropReceiptModel).where(
                    RemnawaveConnectionDropReceiptModel.actor_id == actor_id
                )
            )
            await cleanup.commit()
        await engine.dispose()


@pytest.mark.integration
async def test_global_capacity_is_strict_under_concurrent_reservations() -> None:
    actor_ids = (uuid4(), uuid4())
    payload = {
        "dropBy": {"by": "userIds", "userIds": [42]},
        "targetNodes": {"target": "allNodes"},
    }
    engine, sessions = _session_factory()
    try:
        async with sessions() as first_db, sessions() as second_db:
            results = await asyncio.gather(
                RemnawaveConnectionDropReceiptRegistry(
                    first_db,
                    hmac_secret=_HMAC_SECRET,
                    max_active_receipts=1,
                ).reserve(
                    audience=RemnawaveConnectionJobAudience.ADMIN,
                    actor_id=actor_ids[0],
                    workspace_id=None,
                    scope="admin:global",
                    client_idempotency_key="postgres-capacity-key-0001",
                    payload=payload,
                ),
                RemnawaveConnectionDropReceiptRegistry(
                    second_db,
                    hmac_secret=_HMAC_SECRET,
                    max_active_receipts=1,
                ).reserve(
                    audience=RemnawaveConnectionJobAudience.ADMIN,
                    actor_id=actor_ids[1],
                    workspace_id=None,
                    scope="admin:global",
                    client_idempotency_key="postgres-capacity-key-0002",
                    payload=payload,
                ),
                return_exceptions=True,
            )

        assert sum(not isinstance(result, Exception) for result in results) == 1
        failures = [result for result in results if isinstance(result, Exception)]
        assert len(failures) == 1
        assert isinstance(failures[0], RemnawaveConnectionDropReceiptCapacityError)
        async with sessions() as inspect_db:
            rows = (
                (
                    await inspect_db.execute(
                        select(RemnawaveConnectionDropReceiptModel).where(
                            RemnawaveConnectionDropReceiptModel.actor_id.in_(actor_ids)
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(rows) == 1
    finally:
        async with sessions() as cleanup:
            await cleanup.execute(
                delete(RemnawaveConnectionDropReceiptModel).where(
                    RemnawaveConnectionDropReceiptModel.actor_id.in_(actor_ids)
                )
            )
            await cleanup.commit()
        await engine.dispose()
