from __future__ import annotations

import pytest
from redis.exceptions import ResponseError

from src.infrastructure.cache.passkey_challenges import PasskeyChallengeError, PasskeyChallengeStore
from tests.helpers.realm_auth import FakeRedis


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


class FakeRedisWithoutAtomicConsume:
    async def setex(self, _key: str, _ttl_seconds: int, _value: object) -> bool:
        return True


async def _create_challenge(store: PasskeyChallengeStore):
    return await store.create(
        challenge=b"challenge",
        ceremony="authentication",
        rp_id="cyber-vpn.net",
        expected_origin="https://admin.cyber-vpn.net",
        auth_realm_id="realm-admin",
        realm_key="admin",
        audience="cybervpn:admin",
        principal_class="admin",
        principal_subject="subject",
        user_handle="handle",
        identifier_hash=None,
        require_user_verification=True,
        ttl_seconds=300,
    )


@pytest.mark.asyncio
async def test_challenge_consume_without_getdel_uses_atomic_execute_command() -> None:
    redis = FakeRedisWithoutGetdel()
    store = PasskeyChallengeStore(redis)  # type: ignore[arg-type]
    challenge = await _create_challenge(store)

    consumed = await store.consume(challenge.challenge_id, expected_ceremony="authentication")

    assert consumed.challenge_id == challenge.challenge_id
    assert redis.commands == [("GETDEL", f"{store.key_prefix}{challenge.challenge_id}")]
    assert await redis.get(f"{store.key_prefix}{challenge.challenge_id}") is None
    with pytest.raises(PasskeyChallengeError, match="passkey_challenge_missing"):
        await store.consume(challenge.challenge_id, expected_ceremony="authentication")


@pytest.mark.asyncio
async def test_challenge_consume_when_getdel_unsupported_falls_back_to_lua_once() -> None:
    redis = FakeRedisWithUnsupportedGetdel()
    store = PasskeyChallengeStore(redis)  # type: ignore[arg-type]
    challenge = await _create_challenge(store)

    consumed = await store.consume(challenge.challenge_id, expected_ceremony="authentication")

    assert consumed.challenge_id == challenge.challenge_id
    assert redis.commands == [("GETDEL", f"{store.key_prefix}{challenge.challenge_id}")]
    assert redis.eval_called is True
    assert await redis.get(f"{store.key_prefix}{challenge.challenge_id}") is None
    with pytest.raises(PasskeyChallengeError, match="passkey_challenge_missing"):
        await store.consume(challenge.challenge_id, expected_ceremony="authentication")


@pytest.mark.asyncio
async def test_challenge_consume_without_atomic_fallback_fails_closed() -> None:
    store = PasskeyChallengeStore(FakeRedisWithoutAtomicConsume())  # type: ignore[arg-type]

    with pytest.raises(PasskeyChallengeError, match="passkey_challenge_atomic_consume_unavailable"):
        await store.consume("challenge-id", expected_ceremony="authentication")
