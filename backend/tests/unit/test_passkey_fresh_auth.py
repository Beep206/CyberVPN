from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from redis.exceptions import ResponseError

from src.infrastructure.cache.passkey_fresh_auth import (
    PasskeyFreshAuthGrantError,
    PasskeyFreshAuthGrantRecord,
    PasskeyFreshAuthGrantStore,
    endpoint_scope_for_action,
)
from tests.helpers.realm_auth import FakeRedis

_EXPECTED = {
    "expected_principal_subject": "user-123",
    "expected_principal_class": "partner_operator",
    "expected_auth_realm_id": "realm-partner",
    "expected_realm_key": "partner",
    "expected_action": "partner.member.update:workspace-123:member-456",
}


class FakeRedisWithoutGetdel:
    def __init__(self) -> None:
        self._delegate = FakeRedis()
        self.commands: list[tuple[object, ...]] = []

    async def setex(self, key: str, ttl_seconds: int, value: object) -> bool:
        return await self._delegate.setex(key, ttl_seconds, value)

    async def get(self, key: str) -> object | None:
        return await self._delegate.get(key)

    async def execute_command(self, *args: object, **_options: object) -> object | None:
        self.commands.append(args)
        command = str(args[0]).upper()
        if command == "GETDEL" and len(args) == 2:
            return await self._delegate.getdel(str(args[1]))
        raise NotImplementedError(command)


class FakeRedisWithUnsupportedGetdel:
    def __init__(self) -> None:
        self._delegate = FakeRedis()
        self.commands: list[tuple[object, ...]] = []
        self.eval_called = False

    async def setex(self, key: str, ttl_seconds: int, value: object) -> bool:
        return await self._delegate.setex(key, ttl_seconds, value)

    async def get(self, key: str) -> object | None:
        return await self._delegate.get(key)

    async def getdel(self, _key: str) -> object | None:
        raise ResponseError("unknown command 'GETDEL'")

    async def execute_command(self, *args: object, **_options: object) -> object | None:
        self.commands.append(args)
        raise ResponseError("unknown command 'GETDEL'")

    async def eval(self, _script: str, numkeys: int, key: str) -> object | None:
        self.eval_called = True
        assert numkeys == 1
        return await self._delegate.getdel(key)


async def _consume(
    store: PasskeyFreshAuthGrantStore,
    grant_id: str,
    **overrides: str,
):
    expected = {**_EXPECTED, **overrides}
    return await store.consume(grant_id, **expected)


async def _create_matching_grant(store: PasskeyFreshAuthGrantStore):
    return await store.create(
        principal_subject=_EXPECTED["expected_principal_subject"],
        principal_class=_EXPECTED["expected_principal_class"],
        auth_realm_id=_EXPECTED["expected_auth_realm_id"],
        realm_key=_EXPECTED["expected_realm_key"],
        action=_EXPECTED["expected_action"],
        ttl_seconds=300,
    )


@pytest.mark.asyncio
async def test_consume_missing_fresh_auth_grant_rejects() -> None:
    store = PasskeyFreshAuthGrantStore(FakeRedis())

    with pytest.raises(PasskeyFreshAuthGrantError, match="passkey_fresh_auth_missing"):
        await _consume(store, str(uuid4()))


@pytest.mark.asyncio
async def test_consume_expired_fresh_auth_grant_rejects_and_consumes() -> None:
    redis = FakeRedis()
    store = PasskeyFreshAuthGrantStore(redis)
    grant_id = str(uuid4())
    record = PasskeyFreshAuthGrantRecord(
        grant_id=grant_id,
        principal_subject=_EXPECTED["expected_principal_subject"],
        principal_class=_EXPECTED["expected_principal_class"],
        auth_realm_id=_EXPECTED["expected_auth_realm_id"],
        realm_key=_EXPECTED["expected_realm_key"],
        action=_EXPECTED["expected_action"],
        endpoint_scope=endpoint_scope_for_action(_EXPECTED["expected_action"]),
        issued_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
    )
    key = f"{store.key_prefix}{grant_id}"
    await redis.setex(key, 300, json.dumps(asdict(record), separators=(",", ":")))

    with pytest.raises(PasskeyFreshAuthGrantError, match="passkey_fresh_auth_expired"):
        await _consume(store, grant_id)

    assert await redis.get(key) is None


@pytest.mark.asyncio
async def test_consume_wrong_action_fresh_auth_grant_rejects_and_consumes() -> None:
    redis = FakeRedis()
    store = PasskeyFreshAuthGrantStore(redis)
    grant = await store.create(
        principal_subject=_EXPECTED["expected_principal_subject"],
        principal_class=_EXPECTED["expected_principal_class"],
        auth_realm_id=_EXPECTED["expected_auth_realm_id"],
        realm_key=_EXPECTED["expected_realm_key"],
        action="partner.member.create:workspace-123",
        ttl_seconds=300,
    )

    with pytest.raises(PasskeyFreshAuthGrantError, match="passkey_fresh_auth_mismatch"):
        await _consume(store, grant.grant_id)

    assert await redis.get(f"{store.key_prefix}{grant.grant_id}") is None


@pytest.mark.asyncio
async def test_consume_wrong_realm_fresh_auth_grant_rejects_and_consumes() -> None:
    redis = FakeRedis()
    store = PasskeyFreshAuthGrantStore(redis)
    grant = await store.create(
        principal_subject=_EXPECTED["expected_principal_subject"],
        principal_class=_EXPECTED["expected_principal_class"],
        auth_realm_id="realm-admin",
        realm_key="admin",
        action=_EXPECTED["expected_action"],
        ttl_seconds=300,
    )

    with pytest.raises(PasskeyFreshAuthGrantError, match="passkey_fresh_auth_mismatch"):
        await _consume(store, grant.grant_id)

    assert await redis.get(f"{store.key_prefix}{grant.grant_id}") is None


@pytest.mark.asyncio
async def test_consume_wrong_endpoint_scope_fresh_auth_grant_rejects_and_consumes() -> None:
    redis = FakeRedis()
    store = PasskeyFreshAuthGrantStore(redis)
    grant_id = str(uuid4())
    record = PasskeyFreshAuthGrantRecord(
        grant_id=grant_id,
        principal_subject=_EXPECTED["expected_principal_subject"],
        principal_class=_EXPECTED["expected_principal_class"],
        auth_realm_id=_EXPECTED["expected_auth_realm_id"],
        realm_key=_EXPECTED["expected_realm_key"],
        action=_EXPECTED["expected_action"],
        endpoint_scope="partner.member.create",
        issued_at=datetime.now(UTC).isoformat(),
        expires_at=(datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    )
    key = f"{store.key_prefix}{grant_id}"
    await redis.setex(key, 300, json.dumps(asdict(record), separators=(",", ":")))

    with pytest.raises(PasskeyFreshAuthGrantError, match="passkey_fresh_auth_mismatch"):
        await _consume(store, grant_id)

    assert await redis.get(key) is None


@pytest.mark.asyncio
async def test_consume_matching_fresh_auth_grant_accepts_once_then_rejects_reuse() -> None:
    redis = FakeRedis()
    store = PasskeyFreshAuthGrantStore(redis)
    grant = await _create_matching_grant(store)

    consumed = await _consume(store, grant.grant_id)

    assert consumed.grant_id == grant.grant_id
    assert consumed.action == _EXPECTED["expected_action"]
    assert await redis.get(f"{store.key_prefix}{grant.grant_id}") is None
    with pytest.raises(PasskeyFreshAuthGrantError, match="passkey_fresh_auth_missing"):
        await _consume(store, grant.grant_id)


def test_partner_integration_credential_rotation_requires_fresh_auth() -> None:
    routes_source = (
        Path(__file__).resolve().parents[2]
        / "src/presentation/api/v1/partners/routes.py"
    ).read_text(encoding="utf-8")
    handler = routes_source.split("async def rotate_partner_workspace_integration_credential", 1)[1]
    handler = handler.split("@router.", 1)[0]

    assert "request: Request" in handler
    assert "current_realm: RealmResolution = Depends(get_request_admin_realm)" in handler
    assert "redis_client: redis.Redis = Depends(get_redis)" in handler
    assert "await _enforce_partner_passkey_fresh_auth(" in handler
    assert "partner.integration_credential.rotate:" in handler
    assert handler.index("await _enforce_partner_passkey_fresh_auth(") < handler.index(
        "RotatePartnerWorkspaceIntegrationCredentialUseCase(db).execute("
    )


@pytest.mark.asyncio
async def test_consume_without_getdel_uses_atomic_execute_command() -> None:
    redis = FakeRedisWithoutGetdel()
    store = PasskeyFreshAuthGrantStore(redis)  # type: ignore[arg-type]
    grant = await _create_matching_grant(store)

    consumed = await _consume(store, grant.grant_id)

    assert consumed.grant_id == grant.grant_id
    assert redis.commands == [("GETDEL", f"{store.key_prefix}{grant.grant_id}")]
    assert await redis.get(f"{store.key_prefix}{grant.grant_id}") is None
    with pytest.raises(PasskeyFreshAuthGrantError, match="passkey_fresh_auth_missing"):
        await _consume(store, grant.grant_id)


@pytest.mark.asyncio
async def test_consume_when_getdel_unsupported_falls_back_to_lua_once() -> None:
    redis = FakeRedisWithUnsupportedGetdel()
    store = PasskeyFreshAuthGrantStore(redis)  # type: ignore[arg-type]
    grant = await _create_matching_grant(store)

    consumed = await _consume(store, grant.grant_id)

    assert consumed.grant_id == grant.grant_id
    assert redis.commands == [("GETDEL", f"{store.key_prefix}{grant.grant_id}")]
    assert redis.eval_called is True
    assert await redis.get(f"{store.key_prefix}{grant.grant_id}") is None
    with pytest.raises(PasskeyFreshAuthGrantError, match="passkey_fresh_auth_missing"):
        await _consume(store, grant.grant_id)
