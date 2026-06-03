"""Redis-backed one-time passkey fresh-auth grant store."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import redis.asyncio as redis
from redis.exceptions import ResponseError

from src.config.settings import settings

_GETDEL_LUA = """
local value = redis.call("GET", KEYS[1])
if value then
  redis.call("DEL", KEYS[1])
end
return value
"""


def endpoint_scope_for_action(action: str) -> str:
    return action.split(":", 1)[0]


@dataclass(frozen=True)
class PasskeyFreshAuthGrantRecord:
    grant_id: str
    principal_subject: str
    principal_class: str
    auth_realm_id: str
    realm_key: str
    action: str
    endpoint_scope: str
    issued_at: str
    expires_at: str


class PasskeyFreshAuthGrantError(Exception):
    """Base error for invalid or unavailable fresh-auth grants."""


class PasskeyFreshAuthGrantStore:
    key_prefix = "passkey:fresh:"

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def create(
        self,
        *,
        principal_subject: str,
        principal_class: str,
        auth_realm_id: str,
        realm_key: str,
        action: str,
        ttl_seconds: int | None = None,
    ) -> PasskeyFreshAuthGrantRecord:
        grant_id = str(uuid4())
        issued_at = datetime.now(UTC)
        effective_ttl_seconds = ttl_seconds if ttl_seconds is not None else settings.passkey_fresh_auth_ttl_seconds
        expires_at = issued_at + timedelta(seconds=effective_ttl_seconds)
        record = PasskeyFreshAuthGrantRecord(
            grant_id=grant_id,
            principal_subject=principal_subject,
            principal_class=principal_class,
            auth_realm_id=auth_realm_id,
            realm_key=realm_key,
            action=action,
            endpoint_scope=endpoint_scope_for_action(action),
            issued_at=issued_at.isoformat(),
            expires_at=expires_at.isoformat(),
        )
        await self._redis.setex(
            self._key(grant_id),
            effective_ttl_seconds,
            json.dumps(asdict(record), separators=(",", ":")),
        )
        return record

    async def consume(
        self,
        grant_id: str,
        *,
        expected_principal_subject: str,
        expected_principal_class: str,
        expected_auth_realm_id: str,
        expected_realm_key: str,
        expected_action: str,
    ) -> PasskeyFreshAuthGrantRecord:
        normalized_grant_id = self._normalize_grant_id(grant_id)
        raw = await self._consume_raw(self._key(normalized_grant_id))
        if raw is None:
            raise PasskeyFreshAuthGrantError("passkey_fresh_auth_missing")

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")

        try:
            data = json.loads(str(raw))
            record = PasskeyFreshAuthGrantRecord(
                grant_id=str(data.get("grant_id") or normalized_grant_id),
                principal_subject=str(data["principal_subject"]),
                principal_class=str(data["principal_class"]),
                auth_realm_id=str(data["auth_realm_id"]),
                realm_key=str(data["realm_key"]),
                action=str(data["action"]),
                endpoint_scope=str(data.get("endpoint_scope") or endpoint_scope_for_action(str(data["action"]))),
                issued_at=str(data.get("issued_at") or ""),
                expires_at=str(data["expires_at"]),
            )
        except Exception as exc:
            raise PasskeyFreshAuthGrantError("passkey_fresh_auth_corrupt") from exc

        if record.grant_id != normalized_grant_id:
            raise PasskeyFreshAuthGrantError("passkey_fresh_auth_id_mismatch")

        expires_at = datetime.fromisoformat(record.expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            raise PasskeyFreshAuthGrantError("passkey_fresh_auth_expired")

        if (
            record.principal_subject != expected_principal_subject
            or record.principal_class != expected_principal_class
            or record.auth_realm_id != expected_auth_realm_id
            or record.realm_key != expected_realm_key
            or record.action != expected_action
            or record.endpoint_scope != endpoint_scope_for_action(expected_action)
        ):
            raise PasskeyFreshAuthGrantError("passkey_fresh_auth_mismatch")

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

        raise PasskeyFreshAuthGrantError("passkey_fresh_auth_atomic_consume_unavailable")

    def _key(self, grant_id: str) -> str:
        return f"{self.key_prefix}{grant_id}"

    @staticmethod
    def _is_unknown_command(exc: ResponseError) -> bool:
        return "unknown command" in str(exc).lower()

    @staticmethod
    def _normalize_grant_id(grant_id: str) -> str:
        value = grant_id.strip()
        try:
            return str(UUID(value))
        except ValueError as exc:
            raise PasskeyFreshAuthGrantError("passkey_fresh_auth_invalid_id") from exc
