"""Redis-backed WebAuthn challenge store."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import redis.asyncio as redis
from redis.exceptions import ResponseError
from webauthn.helpers import bytes_to_base64url

from src.config.settings import settings

_GETDEL_LUA = """
local value = redis.call("GET", KEYS[1])
if value then
  redis.call("DEL", KEYS[1])
end
return value
"""


@dataclass(frozen=True)
class PasskeyChallengeRecord:
    challenge_id: str
    challenge_b64: str
    challenge_hash: str
    ceremony: str
    rp_id: str
    expected_origin: str
    auth_realm_id: str
    realm_key: str
    audience: str
    principal_class: str | None
    principal_subject: str | None
    user_handle: str | None
    identifier_hash: str | None
    require_user_verification: bool
    action: str | None
    issued_at: str
    expires_at: str


class PasskeyChallengeError(Exception):
    """Base error for invalid or unavailable passkey challenges."""


class PasskeyChallengeStore:
    key_prefix = "passkey:challenge:"

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def create(
        self,
        *,
        challenge: bytes,
        ceremony: str,
        rp_id: str,
        expected_origin: str,
        auth_realm_id: str,
        realm_key: str,
        audience: str,
        principal_class: str | None,
        principal_subject: str | None,
        user_handle: str | None,
        identifier_hash: str | None,
        require_user_verification: bool,
        action: str | None = None,
        ttl_seconds: int | None = None,
    ) -> PasskeyChallengeRecord:
        issued_at = datetime.now(UTC)
        effective_ttl_seconds = ttl_seconds if ttl_seconds is not None else settings.passkey_challenge_ttl_seconds
        expires_at = issued_at + timedelta(seconds=effective_ttl_seconds)
        challenge_b64 = bytes_to_base64url(challenge)
        challenge_id = str(uuid4())
        record = PasskeyChallengeRecord(
            challenge_id=challenge_id,
            challenge_b64=challenge_b64,
            challenge_hash=sha256(challenge).hexdigest(),
            ceremony=ceremony,
            rp_id=rp_id,
            expected_origin=expected_origin,
            auth_realm_id=auth_realm_id,
            realm_key=realm_key,
            audience=audience,
            principal_class=principal_class,
            principal_subject=principal_subject,
            user_handle=user_handle,
            identifier_hash=identifier_hash,
            require_user_verification=require_user_verification,
            action=action,
            issued_at=issued_at.isoformat(),
            expires_at=expires_at.isoformat(),
        )
        await self._redis.setex(
            self._key(challenge_id),
            effective_ttl_seconds,
            json.dumps(asdict(record), separators=(",", ":")),
        )
        return record

    async def consume(self, challenge_id: str, *, expected_ceremony: str) -> PasskeyChallengeRecord:
        key = self._key(challenge_id)
        raw = await self._consume_raw(key)
        if raw is None:
            raise PasskeyChallengeError("passkey_challenge_missing")

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")

        try:
            data = json.loads(str(raw))
            record = PasskeyChallengeRecord(**data)
        except Exception as exc:
            raise PasskeyChallengeError("passkey_challenge_corrupt") from exc

        if record.ceremony != expected_ceremony:
            raise PasskeyChallengeError("passkey_challenge_type_mismatch")

        expires_at = datetime.fromisoformat(record.expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            raise PasskeyChallengeError("passkey_challenge_expired")

        return record

    async def _consume_raw(self, key: str) -> object | None:
        getdel = getattr(self._redis, "getdel", None)
        if getdel is not None:
            try:
                return await getdel(key)
            except ResponseError as exc:
                if not self._is_unknown_command(exc):
                    raise

        execute_command = getattr(self._redis, "execute_command", None)
        if execute_command is not None:
            try:
                return await execute_command("GETDEL", key)
            except ResponseError as exc:
                if not self._is_unknown_command(exc):
                    raise

        eval_command = getattr(self._redis, "eval", None)
        if eval_command is not None:
            return await eval_command(_GETDEL_LUA, 1, key)

        raise PasskeyChallengeError("passkey_challenge_atomic_consume_unavailable")

    def _key(self, challenge_id: str) -> str:
        return f"{self.key_prefix}{challenge_id}"

    @staticmethod
    def _is_unknown_command(exc: ResponseError) -> bool:
        return "unknown command" in str(exc).lower()
