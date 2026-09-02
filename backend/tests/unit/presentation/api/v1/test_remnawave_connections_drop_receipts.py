from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveConnectionDropReceiptModel
from src.presentation.api.v1.remnawave_connections import drop_receipts
from src.presentation.api.v1.remnawave_connections.drop_receipts import (
    RemnawaveConnectionDropReceiptCapacityError,
    RemnawaveConnectionDropReceiptConflictError,
    RemnawaveConnectionDropReceiptRecord,
    RemnawaveConnectionDropReceiptRegistry,
    RemnawaveConnectionDropReceiptUnavailableError,
    RemnawaveConnectionDropState,
)
from src.presentation.api.v1.remnawave_connections.job_registry import RemnawaveConnectionJobAudience

_CLIENT_KEY = "drop-client-key-0001"
_HMAC_SECRET = b"connections-drop-domain-secret-00000001"
_OTHER_HMAC_SECRET = b"connections-drop-domain-secret-00000002"
_RECEIPT_ID = "r" * 43
_NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
_PAYLOAD = {
    "dropBy": {"by": "ipAddresses", "ipAddresses": ["203.0.113.77"]},
    "targetNodes": {"target": "specificNodes", "nodeUuids": ["323fe749-9d77-464f-8fe2-51a7b0b0209a"]},
}


def _db() -> MagicMock:
    db = MagicMock(spec=AsyncSession)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.execute = AsyncMock()
    return db


def _result() -> MagicMock:
    return MagicMock()


def _scalar_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _count_result(active: int, pending: int, actor_active: int = 0) -> MagicMock:
    result = MagicMock()
    result.one.return_value = (active, actor_active, pending)
    return result


def _new_reservation_results(
    *,
    active: int = 0,
    actor_active: int = 0,
    pending: int = 0,
) -> list[MagicMock]:
    return [
        _result(),  # PostgreSQL advisory transaction lock
        _result(),  # bounded expired-terminal purge
        _scalar_result(None),  # no current idempotency key
        _scalar_result(None),  # no active receipt from a different HMAC key
        _count_result(active, pending, actor_active),
    ]


def _receipt_model(
    *,
    actor_id: UUID,
    state: RemnawaveConnectionDropState,
    hmac_secret: bytes = _HMAC_SECRET,
    expires_at: datetime | None = None,
) -> RemnawaveConnectionDropReceiptModel:
    registry = RemnawaveConnectionDropReceiptRegistry(_db(), hmac_secret=hmac_secret)
    return RemnawaveConnectionDropReceiptModel(
        id=uuid4(),
        key_hmac="a" * 64,
        hmac_key_id=RemnawaveConnectionDropReceiptRegistry.hmac_key_id(hmac_secret),
        receipt_id=_RECEIPT_ID,
        audience=RemnawaveConnectionJobAudience.ADMIN.value,
        actor_id=actor_id,
        workspace_id=None,
        scope_hmac=registry._hmac(  # noqa: SLF001 - deterministic persistence fixture
            drop_receipts._SCOPE_HMAC_CONTEXT,  # noqa: SLF001
            b"admin:global",
        ),
        payload_hmac=RemnawaveConnectionDropReceiptRegistry.payload_hmac(hmac_secret, _PAYLOAD),
        state=state.value,
        created_at=_NOW,
        updated_at=_NOW,
        expires_at=expires_at,
    )


def _integrity_error() -> IntegrityError:
    return IntegrityError("insert", {}, RuntimeError("unique conflict"))


@pytest.mark.unit
async def test_drop_receipt_commits_non_expiring_unknown_before_io_without_raw_material(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = _db()
    db.execute.side_effect = _new_reservation_results()
    monkeypatch.setattr(drop_receipts.secrets, "token_urlsafe", lambda _size: _RECEIPT_ID)
    registry = RemnawaveConnectionDropReceiptRegistry(db, hmac_secret=_HMAC_SECRET, clock=lambda: _NOW)
    actor_id = uuid4()
    workspace_id = uuid4()
    raw_scope = f"partner:{workspace_id}:node:secret-node"

    reservation = await registry.reserve(
        audience=RemnawaveConnectionJobAudience.PARTNER,
        actor_id=actor_id,
        workspace_id=workspace_id,
        scope=raw_scope,
        client_idempotency_key=_CLIENT_KEY,
        payload=_PAYLOAD,
    )

    assert reservation.is_new is True
    assert reservation.record.state is RemnawaveConnectionDropState.OUTCOME_UNKNOWN
    assert reservation.record.expires_at is None
    db.commit.assert_awaited_once_with()
    persisted = db.add.call_args.args[0]
    assert isinstance(persisted, RemnawaveConnectionDropReceiptModel)
    assert persisted.expires_at is None
    assert len(persisted.hmac_key_id) == 64
    assert len(persisted.key_hmac) == len(persisted.scope_hmac) == len(persisted.payload_hmac) == 64
    stored_values = repr(
        {
            "key_hmac": persisted.key_hmac,
            "hmac_key_id": persisted.hmac_key_id,
            "scope_hmac": persisted.scope_hmac,
            "payload_hmac": persisted.payload_hmac,
            "receipt_id": persisted.receipt_id,
        }
    )
    assert _CLIENT_KEY not in stored_values
    assert raw_scope not in stored_values
    assert "secret-node" not in stored_values
    assert "203.0.113.77" not in stored_values
    purge_sql = str(db.execute.await_args_list[1].args[0])
    assert "state IN" in purge_sql
    assert "LIMIT" in purge_sql


@pytest.mark.unit
async def test_unknown_replay_remains_fail_safe_after_terminal_ttl_would_have_elapsed() -> None:
    actor_id = uuid4()
    persisted = _receipt_model(actor_id=actor_id, state=RemnawaveConnectionDropState.OUTCOME_UNKNOWN)
    replay_db = _db()
    replay_db.execute.side_effect = [_result(), _result(), _scalar_result(persisted)]
    registry = RemnawaveConnectionDropReceiptRegistry(
        replay_db,
        hmac_secret=_HMAC_SECRET,
        terminal_ttl_seconds=300,
        clock=lambda: _NOW + timedelta(days=365),
    )

    replay = await registry.reserve(
        audience=RemnawaveConnectionJobAudience.ADMIN,
        actor_id=actor_id,
        workspace_id=None,
        scope="admin:global",
        client_idempotency_key=_CLIENT_KEY,
        payload=_PAYLOAD,
    )

    assert replay.is_new is False
    assert replay.record.state is RemnawaveConnectionDropState.OUTCOME_UNKNOWN
    assert replay.record.expires_at is None
    assert replay_db.execute.await_count == 3
    replay_db.commit.assert_awaited_once_with()


@pytest.mark.unit
async def test_drop_receipt_same_key_with_changed_payload_is_conflict_and_releases_lock() -> None:
    actor_id = uuid4()
    persisted = _receipt_model(actor_id=actor_id, state=RemnawaveConnectionDropState.OUTCOME_UNKNOWN)
    replay_db = _db()
    replay_db.execute.side_effect = [_result(), _result(), _scalar_result(persisted)]
    registry = RemnawaveConnectionDropReceiptRegistry(replay_db, hmac_secret=_HMAC_SECRET, clock=lambda: _NOW)

    with pytest.raises(RemnawaveConnectionDropReceiptConflictError):
        await registry.reserve(
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

    replay_db.rollback.assert_awaited_once_with()
    replay_db.commit.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.parametrize(
    "terminal_state",
    [RemnawaveConnectionDropState.ACCEPTED, RemnawaveConnectionDropState.REJECTED],
)
async def test_drop_receipt_terminal_state_starts_honest_ttl_at_reconciliation(
    terminal_state: RemnawaveConnectionDropState,
) -> None:
    db = _db()
    db.execute.side_effect = _new_reservation_results()
    registry = RemnawaveConnectionDropReceiptRegistry(
        db,
        hmac_secret=_HMAC_SECRET,
        terminal_ttl_seconds=3_600,
        clock=lambda: _NOW,
    )
    reservation = await registry.reserve(
        audience=RemnawaveConnectionJobAudience.ADMIN,
        actor_id=uuid4(),
        workspace_id=None,
        scope="admin:global",
        client_idempotency_key=_CLIENT_KEY,
        payload=_PAYLOAD,
    )
    persisted = db.add.call_args.args[0]
    db.commit.reset_mock()
    db.execute = AsyncMock(return_value=_scalar_result(persisted))

    updated = await registry.update_state(reservation, terminal_state)

    assert updated.state is terminal_state
    assert updated.expires_at == _NOW + timedelta(hours=1)
    assert persisted.state == terminal_state.value
    assert persisted.expires_at == _NOW + timedelta(hours=1)
    db.commit.assert_awaited_once_with()


@pytest.mark.unit
async def test_expired_terminal_receipt_is_released_and_same_key_can_start_new_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor_id = uuid4()
    expired = _receipt_model(
        actor_id=actor_id,
        state=RemnawaveConnectionDropState.ACCEPTED,
        expires_at=_NOW - timedelta(seconds=1),
    )
    db = _db()
    db.execute.side_effect = [
        _result(),
        _result(),
        _scalar_result(expired),
        _scalar_result(expired.id),
        _scalar_result(None),
        _count_result(0, 0),
    ]
    monkeypatch.setattr(drop_receipts.secrets, "token_urlsafe", lambda _size: "n" * 43)
    registry = RemnawaveConnectionDropReceiptRegistry(db, hmac_secret=_HMAC_SECRET, clock=lambda: _NOW)

    reservation = await registry.reserve(
        audience=RemnawaveConnectionJobAudience.ADMIN,
        actor_id=actor_id,
        workspace_id=None,
        scope="admin:global",
        client_idempotency_key=_CLIENT_KEY,
        payload=_PAYLOAD,
    )

    assert reservation.is_new is True
    assert reservation.record.receipt_id == "n" * 43
    assert reservation.record.state is RemnawaveConnectionDropState.OUTCOME_UNKNOWN
    assert reservation.record.expires_at is None
    released_sql = str(db.execute.await_args_list[3].args[0])
    assert "expires_at" in released_sql
    assert "state IN" in released_sql


@pytest.mark.unit
async def test_active_receipts_from_rotated_hmac_key_fail_closed_before_insert() -> None:
    actor_id = uuid4()
    db = _db()
    db.execute.side_effect = [
        _result(),
        _result(),
        _scalar_result(None),
        _scalar_result(uuid4()),
    ]
    registry = RemnawaveConnectionDropReceiptRegistry(db, hmac_secret=_OTHER_HMAC_SECRET, clock=lambda: _NOW)

    with pytest.raises(RemnawaveConnectionDropReceiptUnavailableError, match="HMAC key changed"):
        await registry.reserve(
            audience=RemnawaveConnectionJobAudience.ADMIN,
            actor_id=actor_id,
            workspace_id=None,
            scope="admin:global",
            client_idempotency_key=_CLIENT_KEY,
            payload=_PAYLOAD,
        )

    db.rollback.assert_awaited_once_with()
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("active", "actor_active", "pending", "message"),
    [
        (2, 0, 0, "active capacity"),
        (1, 2, 0, "actor reached"),
        (1, 1, 1, "requires reconciliation"),
    ],
)
async def test_capacity_limits_fail_closed_under_registry_lock(
    active: int,
    actor_active: int,
    pending: int,
    message: str,
) -> None:
    db = _db()
    db.execute.side_effect = _new_reservation_results(
        active=active,
        actor_active=actor_active,
        pending=pending,
    )
    registry = RemnawaveConnectionDropReceiptRegistry(
        db,
        hmac_secret=_HMAC_SECRET,
        max_active_receipts=2,
        max_active_per_actor=2,
        max_pending_per_actor=1,
        clock=lambda: _NOW,
    )

    with pytest.raises(RemnawaveConnectionDropReceiptCapacityError, match=message):
        await registry.reserve(
            audience=RemnawaveConnectionJobAudience.ADMIN,
            actor_id=uuid4(),
            workspace_id=None,
            scope="admin:global",
            client_idempotency_key=_CLIENT_KEY,
            payload=_PAYLOAD,
        )

    lock_sql = str(db.execute.await_args_list[0].args[0])
    assert "pg_advisory_xact_lock" in lock_sql
    db.rollback.assert_awaited_once_with()
    db.add.assert_not_called()


@pytest.mark.unit
async def test_drop_receipt_insert_collision_without_matching_key_fails_closed() -> None:
    db = _db()
    db.execute.side_effect = [*_new_reservation_results(), _scalar_result(None)]
    db.commit.side_effect = _integrity_error()
    registry = RemnawaveConnectionDropReceiptRegistry(db, hmac_secret=_HMAC_SECRET, clock=lambda: _NOW)

    with pytest.raises(RemnawaveConnectionDropReceiptUnavailableError, match="could not be reconciled"):
        await registry.reserve(
            audience=RemnawaveConnectionJobAudience.ADMIN,
            actor_id=uuid4(),
            workspace_id=None,
            scope="admin:global",
            client_idempotency_key=_CLIENT_KEY,
            payload=_PAYLOAD,
        )

    db.rollback.assert_awaited_once_with()


@pytest.mark.unit
def test_drop_receipt_hmac_key_id_is_stable_domain_separated_and_secret_free() -> None:
    first = RemnawaveConnectionDropReceiptRegistry.hmac_key_id(_HMAC_SECRET)
    replay = RemnawaveConnectionDropReceiptRegistry.hmac_key_id(_HMAC_SECRET)
    rotated = RemnawaveConnectionDropReceiptRegistry.hmac_key_id(_OTHER_HMAC_SECRET)

    assert first == replay
    assert first != rotated
    assert len(first) == 64
    assert _HMAC_SECRET.decode() not in first


@pytest.mark.unit
def test_drop_receipt_rejects_naive_clock() -> None:
    registry = RemnawaveConnectionDropReceiptRegistry(
        _db(),
        hmac_secret=_HMAC_SECRET,
        clock=lambda: datetime(2026, 8, 31, 12, 0),
    )

    with pytest.raises(RemnawaveConnectionDropReceiptUnavailableError, match="clock"):
        registry._now()  # noqa: SLF001 - direct invariant test


@pytest.mark.unit
def test_drop_receipt_record_rejects_naive_persisted_timestamps() -> None:
    with pytest.raises(ValueError, match="timestamps must include timezone"):
        RemnawaveConnectionDropReceiptRecord(
            database_id=uuid4(),
            receipt_id=_RECEIPT_ID,
            hmac_key_id="a" * 64,
            audience=RemnawaveConnectionJobAudience.ADMIN,
            actor_id=uuid4(),
            scope_hmac="b" * 64,
            payload_hmac="c" * 64,
            state=RemnawaveConnectionDropState.OUTCOME_UNKNOWN,
            created_at=datetime(2026, 8, 31, 12, 0),
            updated_at=datetime(2026, 8, 31, 12, 0),
            expires_at=None,
        )
