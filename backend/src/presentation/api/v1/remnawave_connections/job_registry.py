"""Short-lived, opaque bindings for Remnawave connection read jobs."""

from __future__ import annotations

import re
import secrets
from enum import StrEnum
from uuid import UUID

import redis.asyncio as redis
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

_PUBLIC_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_UPSTREAM_JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class RemnawaveConnectionJobAudience(StrEnum):
    ADMIN = "admin"
    PARTNER = "partner"
    CUSTOMER = "customer"


class RemnawaveConnectionJobKind(StrEnum):
    USER = "user"
    NODE = "node"


class RemnawaveConnectionJobRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audience: RemnawaveConnectionJobAudience
    kind: RemnawaveConnectionJobKind
    actor_id: UUID
    upstream_job_id: str = Field(min_length=1, max_length=128, pattern=_UPSTREAM_JOB_ID_RE.pattern)
    workspace_id: UUID | None = None
    user_id: int | None = Field(default=None, ge=1)
    node_uuid: UUID | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> RemnawaveConnectionJobRecord:
        if self.kind is RemnawaveConnectionJobKind.USER:
            if self.user_id is None or self.node_uuid is not None:
                raise ValueError("User connection job requires only a numeric user target")
        elif self.node_uuid is None or self.user_id is not None:
            raise ValueError("Node connection job requires only a node UUID target")
        if self.audience is RemnawaveConnectionJobAudience.PARTNER and self.workspace_id is None:
            raise ValueError("Partner connection job requires a workspace")
        if self.audience is not RemnawaveConnectionJobAudience.PARTNER and self.workspace_id is not None:
            raise ValueError("Only partner connection jobs may carry a workspace")
        return self


class RemnawaveConnectionJobNotFoundError(RuntimeError):
    """The public request id is absent, expired, or outside the caller scope."""


class RemnawaveConnectionJobRegistryUnavailableError(RuntimeError):
    """The binding registry cannot safely issue or resolve a request id."""


class RemnawaveConnectionJobRegistry:
    """Bind provider job IDs to authenticated actors without exposing them.

    The opaque random identifier prevents a provider job ID from becoming a
    cross-tenant lookup oracle.  Every poll also re-runs current authorization;
    records expire automatically and contain no connection IP payloads.
    """

    ttl_seconds = 300
    key_prefix = "remnawave:connections:job:v1:"

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def issue(self, record: RemnawaveConnectionJobRecord) -> str:
        encoded = record.model_dump_json()
        for _attempt in range(3):
            request_id = secrets.token_urlsafe(32)
            try:
                created = await self._redis.set(
                    self._key(request_id),
                    encoded,
                    ex=self.ttl_seconds,
                    nx=True,
                )
            except redis.RedisError as exc:
                raise RemnawaveConnectionJobRegistryUnavailableError(
                    "Remnawave connection job registry is unavailable"
                ) from exc
            if created:
                return request_id
        raise RemnawaveConnectionJobRegistryUnavailableError(
            "Could not allocate an opaque Remnawave connection request id"
        )

    async def load(self, request_id: str) -> RemnawaveConnectionJobRecord:
        if _PUBLIC_REQUEST_ID_RE.fullmatch(request_id) is None:
            raise RemnawaveConnectionJobNotFoundError("Remnawave connection request not found")
        try:
            raw = await self._redis.get(self._key(request_id))
        except redis.RedisError as exc:
            raise RemnawaveConnectionJobRegistryUnavailableError(
                "Remnawave connection job registry is unavailable"
            ) from exc
        if raw is None:
            raise RemnawaveConnectionJobNotFoundError("Remnawave connection request not found")
        try:
            return RemnawaveConnectionJobRecord.model_validate_json(raw)
        except (ValidationError, TypeError, ValueError) as exc:
            try:
                await self._redis.delete(self._key(request_id))
            except redis.RedisError:
                pass
            raise RemnawaveConnectionJobRegistryUnavailableError(
                "Remnawave connection job registry contains an invalid binding"
            ) from exc

    @classmethod
    def _key(cls, request_id: str) -> str:
        return f"{cls.key_prefix}{request_id}"
