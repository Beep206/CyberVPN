"""Redis-backed ephemeral presence for messaging realtime channels."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import redis.asyncio as redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MessagingPresenceIdentity:
    participant_type: str
    participant_id: str
    connection_id: str
    transport: str


class MessagingPresenceRegistry:
    """Store short-lived connection presence in Redis.

    Presence is advisory. Redis failures must not reject an already authenticated
    realtime connection because REST sync remains the source of truth.
    """

    KEY_PREFIX = "messaging:presence"

    def __init__(self, redis_client: redis.Redis, *, ttl_seconds: int) -> None:
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    async def register(self, identity: MessagingPresenceIdentity) -> bool:
        key = self._connection_key(identity)
        index_key = self._index_key(identity)
        payload = self._payload(identity)
        try:
            await self._redis.set(key, payload, ex=self._ttl_seconds)
            await self._redis.sadd(index_key, identity.connection_id)
            await self._redis.expire(index_key, self._ttl_seconds)
        except RedisError:
            logger.warning("Messaging presence Redis register failed", exc_info=True)
            return False
        return True

    async def refresh(self, identity: MessagingPresenceIdentity) -> bool:
        key = self._connection_key(identity)
        index_key = self._index_key(identity)
        try:
            await self._redis.expire(key, self._ttl_seconds)
            await self._redis.expire(index_key, self._ttl_seconds)
        except RedisError:
            logger.warning("Messaging presence Redis refresh failed", exc_info=True)
            return False
        return True

    async def disconnect(self, identity: MessagingPresenceIdentity) -> bool:
        try:
            await self._redis.delete(self._connection_key(identity))
            await self._redis.srem(self._index_key(identity), identity.connection_id)
        except RedisError:
            logger.warning("Messaging presence Redis disconnect failed", exc_info=True)
            return False
        return True

    async def connection_count(self, *, participant_type: str, participant_id: str) -> int:
        index_key = self._index_key_for(participant_type=participant_type, participant_id=participant_id)
        try:
            connection_ids = await self._redis.smembers(index_key)
            count = 0
            stale: list[str] = []
            for raw_connection_id in connection_ids:
                connection_id = (
                    raw_connection_id.decode() if isinstance(raw_connection_id, bytes) else raw_connection_id
                )
                key = self._connection_key_for(
                    participant_type=participant_type,
                    participant_id=participant_id,
                    connection_id=str(connection_id),
                )
                if await self._redis.exists(key):
                    count += 1
                else:
                    stale.append(str(connection_id))
            if stale:
                await self._redis.srem(index_key, *stale)
            return count
        except RedisError:
            logger.warning("Messaging presence Redis count failed", exc_info=True)
            return 0

    def _payload(self, identity: MessagingPresenceIdentity) -> str:
        observed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return f"{identity.transport}:{observed_at}"

    def _connection_key(self, identity: MessagingPresenceIdentity) -> str:
        return self._connection_key_for(
            participant_type=identity.participant_type,
            participant_id=identity.participant_id,
            connection_id=identity.connection_id,
        )

    def _index_key(self, identity: MessagingPresenceIdentity) -> str:
        return self._index_key_for(participant_type=identity.participant_type, participant_id=identity.participant_id)

    def _connection_key_for(self, *, participant_type: str, participant_id: str, connection_id: str) -> str:
        return f"{self.KEY_PREFIX}:{participant_type}:{participant_id}:{connection_id}"

    def _index_key_for(self, *, participant_type: str, participant_id: str) -> str:
        return f"{self.KEY_PREFIX}:index:{participant_type}:{participant_id}"
