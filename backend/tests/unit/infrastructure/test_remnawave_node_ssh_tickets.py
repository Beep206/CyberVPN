import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest
import redis.asyncio as redis

from src.infrastructure.cache.remnawave_node_ssh_tickets import (
    RemnawaveNodeSshTicketError,
    RemnawaveNodeSshTicketStore,
)


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expiry: dict[str, int] = {}

    async def set(
        self,
        key: str,
        value: object,
        *,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool:
        if nx and key in self.values:
            return False
        self.values[key] = str(value)
        if ex is not None:
            self.expiry[key] = ex
        return True

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            deleted += int(self.values.pop(key, None) is not None)
            self.expiry.pop(key, None)
        return deleted

    async def eval(self, _script: str, numkeys: int, *args: object) -> object | None:
        if numkeys == 2 and len(args) == 3:
            pending_key, active_key, active_ttl = (str(item) for item in args)
            raw = self.values.pop(pending_key, None)
            self.expiry.pop(pending_key, None)
            if raw is None:
                return None
            self.values[active_key] = raw
            self.expiry[active_key] = int(active_ttl)
            return raw

        if numkeys == 2 and len(args) == 2:
            pending_key, active_key = (str(item) for item in args)
            for key, state in ((pending_key, "pending"), (active_key, "active")):
                raw = self.values.pop(key, None)
                self.expiry.pop(key, None)
                if raw is not None:
                    return [raw, state]
            return None

        key, expected = (str(item) for item in args)
        if self.values.get(key) != expected:
            return 0
        await self.delete(key)
        return 1


def _store() -> tuple[RemnawaveNodeSshTicketStore, _FakeRedis]:
    fake = _FakeRedis()
    return RemnawaveNodeSshTicketStore(cast(redis.Redis, fake), master_secret="s" * 64), fake


async def _create_ticket(
    store: RemnawaveNodeSshTicketStore,
    *,
    admin_id=None,
    auth_realm_id=None,
    node_uuid=None,
    access_jti: str = "access-session-a",
    device_cookie: str = "d" * 43,
):
    resolved_admin_id = admin_id or uuid4()
    resolved_realm_id = auth_realm_id or uuid4()
    return await store.create(
        admin_id=resolved_admin_id,
        auth_realm_id=resolved_realm_id,
        auth_session_binding=store.build_session_binding(
            admin_id=resolved_admin_id,
            auth_realm_id=resolved_realm_id,
            access_jti=access_jti,
            device_cookie=device_cookie,
        ),
        node_uuid=node_uuid or uuid4(),
        origin="https://admin.cyber-vpn.net",
        issue_ip="203.0.113.10",
        upstream_ticket="u" * 43,
        upstream_credential="c" * 43,
        upstream_path="/api/cybervpn/node-ssh/ws",
        upstream_protocol="rw-cybervpn",
        ttl_seconds=15,
    )


@pytest.mark.unit
async def test_ticket_is_atomically_consumed_once_and_bound_to_origin() -> None:
    store, _redis = _store()
    issued = await _create_ticket(store)

    consumed = await store.consume(
        issued.ticket_id,
        expected_admin_id=UUID(issued.admin_id),
        expected_auth_realm_id=UUID(issued.auth_realm_id),
        expected_auth_session_binding=issued.auth_session_binding,
        expected_origin="https://admin.cyber-vpn.net",
        expected_issue_ip="203.0.113.10",
        active_ttl_seconds=600,
    )

    assert consumed == issued
    assert await store.is_session_active(issued.ticket_id) is True
    with pytest.raises(RemnawaveNodeSshTicketError, match="node_ssh_ticket_missing"):
        await store.consume(
            issued.ticket_id,
            expected_admin_id=UUID(issued.admin_id),
            expected_auth_realm_id=UUID(issued.auth_realm_id),
            expected_auth_session_binding=issued.auth_session_binding,
            expected_origin="https://admin.cyber-vpn.net",
            expected_issue_ip="203.0.113.10",
            active_ttl_seconds=600,
        )


@pytest.mark.unit
async def test_wrong_origin_burns_ticket_and_prevents_replay() -> None:
    store, _redis = _store()
    issued = await _create_ticket(store)

    with pytest.raises(RemnawaveNodeSshTicketError, match="node_ssh_ticket_origin_mismatch"):
        await store.consume(
            issued.ticket_id,
            expected_admin_id=UUID(issued.admin_id),
            expected_auth_realm_id=UUID(issued.auth_realm_id),
            expected_auth_session_binding=issued.auth_session_binding,
            expected_origin="https://attacker.example",
            expected_issue_ip="203.0.113.10",
            active_ttl_seconds=600,
        )

    assert await store.is_session_active(issued.ticket_id) is False
    with pytest.raises(RemnawaveNodeSshTicketError, match="node_ssh_ticket_missing"):
        await store.consume(
            issued.ticket_id,
            expected_admin_id=UUID(issued.admin_id),
            expected_auth_realm_id=UUID(issued.auth_realm_id),
            expected_auth_session_binding=issued.auth_session_binding,
            expected_origin="https://admin.cyber-vpn.net",
            expected_issue_ip="203.0.113.10",
            active_ttl_seconds=600,
        )


@pytest.mark.unit
async def test_different_client_ip_burns_ticket_and_prevents_replay() -> None:
    store, _redis = _store()
    issued = await _create_ticket(store)

    with pytest.raises(RemnawaveNodeSshTicketError, match="node_ssh_ticket_ip_mismatch"):
        await store.consume(
            issued.ticket_id,
            expected_admin_id=UUID(issued.admin_id),
            expected_auth_realm_id=UUID(issued.auth_realm_id),
            expected_auth_session_binding=issued.auth_session_binding,
            expected_origin="https://admin.cyber-vpn.net",
            expected_issue_ip="198.51.100.25",
            active_ttl_seconds=600,
        )

    assert await store.is_session_active(issued.ticket_id) is False
    with pytest.raises(RemnawaveNodeSshTicketError, match="node_ssh_ticket_missing"):
        await store.consume(
            issued.ticket_id,
            expected_admin_id=UUID(issued.admin_id),
            expected_auth_realm_id=UUID(issued.auth_realm_id),
            expected_auth_session_binding=issued.auth_session_binding,
            expected_origin="https://admin.cyber-vpn.net",
            expected_issue_ip="203.0.113.10",
            active_ttl_seconds=600,
        )


@pytest.mark.unit
async def test_expired_ticket_is_rejected_and_destroyed() -> None:
    store, fake = _store()
    issued = await _create_ticket(store)
    pending_key = store._pending_key(issued.ticket_id)
    expired = replace(issued, expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat())
    fake.values[pending_key] = store._seal_record(expired)

    with pytest.raises(RemnawaveNodeSshTicketError, match="node_ssh_ticket_expired"):
        await store.consume(
            issued.ticket_id,
            expected_admin_id=UUID(issued.admin_id),
            expected_auth_realm_id=UUID(issued.auth_realm_id),
            expected_auth_session_binding=issued.auth_session_binding,
            expected_origin="https://admin.cyber-vpn.net",
            expected_issue_ip="203.0.113.10",
            active_ttl_seconds=600,
        )

    assert await store.is_session_active(issued.ticket_id) is False


@pytest.mark.unit
async def test_owner_can_immediately_revoke_pending_and_active_tickets() -> None:
    store, _redis = _store()
    admin_id = uuid4()
    foreign_admin_id = uuid4()
    pending = await _create_ticket(store, admin_id=admin_id)

    assert await store.revoke(pending.ticket_id, expected_admin_id=foreign_admin_id) is None
    revoked_pending = await store.revoke(pending.ticket_id, expected_admin_id=admin_id)
    assert revoked_pending is not None
    assert revoked_pending[1] == "pending"

    active = await _create_ticket(store, admin_id=admin_id)
    await store.consume(
        active.ticket_id,
        expected_admin_id=admin_id,
        expected_auth_realm_id=UUID(active.auth_realm_id),
        expected_auth_session_binding=active.auth_session_binding,
        expected_origin="https://admin.cyber-vpn.net",
        expected_issue_ip="203.0.113.10",
        active_ttl_seconds=600,
    )
    revoked_active = await store.revoke(active.ticket_id, expected_admin_id=admin_id)
    assert revoked_active is not None
    assert revoked_active[1] == "active"
    assert await store.is_session_active(active.ticket_id) is False


@pytest.mark.unit
async def test_store_rejects_unbounded_active_session_ttl() -> None:
    store, _redis = _store()
    issued = await _create_ticket(store)

    with pytest.raises(ValueError, match="active session TTL"):
        await store.consume(
            issued.ticket_id,
            expected_admin_id=UUID(issued.admin_id),
            expected_auth_realm_id=UUID(issued.auth_realm_id),
            expected_auth_session_binding=issued.auth_session_binding,
            expected_origin="https://admin.cyber-vpn.net",
            expected_issue_ip="203.0.113.10",
            active_ttl_seconds=3601,
        )


@pytest.mark.unit
async def test_redis_contains_neither_local_nor_upstream_ticket_plaintext() -> None:
    store, fake = _store()
    issued = await _create_ticket(store)

    assert len(fake.values) == 1
    redis_key, redis_value = next(iter(fake.values.items()))
    assert issued.ticket_id not in redis_key
    assert issued.ticket_id not in redis_value
    assert "u" * 43 not in redis_value
    assert "c" * 43 not in redis_value
    assert redis_value.startswith("v1.")


@pytest.mark.unit
async def test_ticket_is_bound_to_exact_admin_session_and_mismatch_burns_replay() -> None:
    store, _redis = _store()
    issued = await _create_ticket(store)
    wrong_binding = store.build_session_binding(
        admin_id=UUID(issued.admin_id),
        auth_realm_id=UUID(issued.auth_realm_id),
        access_jti="other-access-session",
        device_cookie="d" * 43,
    )

    with pytest.raises(RemnawaveNodeSshTicketError, match="session_mismatch"):
        await store.consume(
            issued.ticket_id,
            expected_admin_id=UUID(issued.admin_id),
            expected_auth_realm_id=UUID(issued.auth_realm_id),
            expected_auth_session_binding=wrong_binding,
            expected_origin="https://admin.cyber-vpn.net",
            expected_issue_ip="203.0.113.10",
            active_ttl_seconds=600,
        )

    assert await store.is_session_active(issued.ticket_id) is False
    with pytest.raises(RemnawaveNodeSshTicketError, match="ticket_missing"):
        await store.consume(
            issued.ticket_id,
            expected_admin_id=UUID(issued.admin_id),
            expected_auth_realm_id=UUID(issued.auth_realm_id),
            expected_auth_session_binding=issued.auth_session_binding,
            expected_origin="https://admin.cyber-vpn.net",
            expected_issue_ip="203.0.113.10",
            active_ttl_seconds=600,
        )


@pytest.mark.unit
async def test_supervisor_revoke_is_atomic_and_replay_safe() -> None:
    store, _redis = _store()
    issued = await _create_ticket(store)

    first, second = await asyncio.gather(
        store.revoke_as_supervisor(issued.ticket_id),
        store.revoke_as_supervisor(issued.ticket_id),
    )

    assert sum(result is not None for result in (first, second)) == 1
    winner = first or second
    assert winner is not None
    assert winner[0].ticket_id == issued.ticket_id
    assert await store.revoke_as_supervisor(issued.ticket_id) is None


@pytest.mark.unit
async def test_envelope_cannot_be_decrypted_with_another_server_secret() -> None:
    store, fake = _store()
    issued = await _create_ticket(store)
    other_store = RemnawaveNodeSshTicketStore(cast(redis.Redis, fake), master_secret="x" * 64)

    with pytest.raises(RemnawaveNodeSshTicketError, match="ticket_corrupt"):
        other_store._open_record(issued.stored_envelope, ticket_id=issued.ticket_id)
