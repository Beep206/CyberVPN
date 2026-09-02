"""Bounded authoritative REST reads used after ephemeral stream loss."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.application.services.remnawave_stream_ingestion import ConnectionIp, ConnectionUser
from src.application.services.remnawave_stream_reconciliation import AuthoritativeNodePresenceSnapshot
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveNodeResponse, RemnawaveUserResponse

_MAX_USERS = 100_000
_MAX_USER_PAGES = 100
_MAX_NODES = 128
_MAX_CONNECTION_JOB_POLLS = 40
_JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class RemnawaveStreamAuthoritativeReadError(RuntimeError):
    pass


class _ConnectionsJob(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    job_id: str = Field(alias="jobId", min_length=1, max_length=128)

    @field_validator("job_id")
    @classmethod
    def validate_job_id(cls, value: str) -> str:
        if _JOB_ID_RE.fullmatch(value) is None:
            raise ValueError("Invalid Remnawave connection job id")
        return value


class _ConnectionsIp(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    ip: str = Field(min_length=2, max_length=64)
    last_seen: datetime = Field(alias="lastSeen")

    @field_validator("last_seen")
    @classmethod
    def require_aware_last_seen(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Remnawave connection timestamp must include timezone")
        return value


class _ConnectionsUser(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    user_id: int = Field(alias="userId", ge=1)
    ips: list[_ConnectionsIp] = Field(max_length=1_000)


class _ConnectionsResultPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    success: bool
    node_uuid: UUID = Field(alias="nodeUuid")
    users: list[_ConnectionsUser] = Field(max_length=_MAX_USERS)


class _ConnectionsJobResult(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    is_completed: bool = Field(alias="isCompleted")
    is_failed: bool = Field(alias="isFailed")
    result: _ConnectionsResultPayload | None

    @model_validator(mode="after")
    def validate_terminal_shape(self) -> _ConnectionsJobResult:
        if self.is_completed and not self.is_failed and self.result is None:
            raise ValueError("Completed Remnawave connection job has no result")
        return self


class RemnawaveStreamRestReconciliationGateway:
    """Fetch current truth without pretending that lost historical events were recovered."""

    def __init__(
        self,
        client: RemnawaveClient,
        *,
        clock: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))
        self._sleeper = sleeper or asyncio.sleep

    async def read_user_usage_inventory(self) -> int:
        """Validate a complete bounded numeric user inventory and current usage counters."""

        seen_ids: set[int] = set()
        seen_cursors: set[str] = set()
        cursor: str | None = None
        for _page_number in range(_MAX_USER_PAGES):
            page = await self._client.get_all_users_cursor_page(cursor=cursor, limit=1000)
            for raw_user in page.items:
                user = RemnawaveUserResponse.model_validate(raw_user)
                numeric_id = user.remnawave_numeric_id
                if isinstance(numeric_id, bool) or numeric_id is None or numeric_id <= 0:
                    raise RemnawaveStreamAuthoritativeReadError(
                        "Authoritative Remnawave user inventory contains a non-numeric identity"
                    )
                if numeric_id in seen_ids:
                    raise RemnawaveStreamAuthoritativeReadError(
                        "Authoritative Remnawave user inventory contains duplicate numeric identities"
                    )
                for counter in (user.used_traffic_bytes, user.lifetime_used_traffic_bytes):
                    if counter is not None and (isinstance(counter, bool) or counter < 0):
                        raise RemnawaveStreamAuthoritativeReadError(
                            "Authoritative Remnawave user inventory contains an invalid usage counter"
                        )
                seen_ids.add(numeric_id)
                if len(seen_ids) > _MAX_USERS:
                    raise RemnawaveStreamAuthoritativeReadError(
                        "Authoritative Remnawave user inventory exceeds the reconciliation bound"
                    )

            next_cursor = page.next_cursor
            if not next_cursor or page.has_next_page is False or not page.items:
                return len(seen_ids)
            if next_cursor in seen_cursors:
                raise RemnawaveStreamAuthoritativeReadError(
                    "Authoritative Remnawave user inventory repeated a pagination cursor"
                )
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        raise RemnawaveStreamAuthoritativeReadError(
            "Authoritative Remnawave user inventory exceeded the pagination bound"
        )

    async def read_node_presence_snapshots(self) -> tuple[AuthoritativeNodePresenceSnapshot, ...]:
        nodes = await self._client.get_collection_validated(
            "/nodes",
            "nodes",
            RemnawaveNodeResponse,
        )
        if len(nodes) > _MAX_NODES:
            raise RemnawaveStreamAuthoritativeReadError(
                "Authoritative Remnawave node inventory exceeds the reconciliation bound"
            )
        seen_node_ids: set[int] = set()
        seen_node_uuids: set[UUID] = set()
        for node in nodes:
            if isinstance(node.id, bool) or node.id is None or node.id <= 0:
                raise RemnawaveStreamAuthoritativeReadError(
                    "Authoritative Remnawave node inventory contains a non-numeric identity"
                )
            try:
                node_uuid = UUID(node.uuid)
            except ValueError as exc:
                raise RemnawaveStreamAuthoritativeReadError(
                    "Authoritative Remnawave node inventory contains an invalid UUID"
                ) from exc
            if node.id in seen_node_ids or node_uuid in seen_node_uuids:
                raise RemnawaveStreamAuthoritativeReadError(
                    "Authoritative Remnawave node inventory contains duplicate identities"
                )
            seen_node_ids.add(node.id)
            seen_node_uuids.add(node_uuid)
        semaphore = asyncio.Semaphore(4)

        async def bounded_read(node: RemnawaveNodeResponse) -> AuthoritativeNodePresenceSnapshot:
            async with semaphore:
                return await self._read_node_presence(node)

        return tuple(await asyncio.gather(*(bounded_read(node) for node in nodes)))

    async def _read_node_presence(self, node: RemnawaveNodeResponse) -> AuthoritativeNodePresenceSnapshot:
        node_id = node.id
        if isinstance(node_id, bool) or node_id is None or node_id <= 0:
            raise RemnawaveStreamAuthoritativeReadError(
                "Authoritative Remnawave node inventory contains a non-numeric identity"
            )
        try:
            node_uuid = UUID(node.uuid)
        except ValueError as exc:
            raise RemnawaveStreamAuthoritativeReadError(
                "Authoritative Remnawave node inventory contains an invalid UUID"
            ) from exc
        job = _ConnectionsJob.model_validate(await self._client.post(f"/connections/by-node/{node_uuid}"))
        for attempt in range(_MAX_CONNECTION_JOB_POLLS):
            result = _ConnectionsJobResult.model_validate(await self._client.get(f"/connections/by-node/{job.job_id}"))
            if result.is_failed:
                raise RemnawaveStreamAuthoritativeReadError("Authoritative Remnawave node connection read failed")
            if result.is_completed:
                payload = result.result
                if payload is None or not payload.success or payload.node_uuid != node_uuid:
                    raise RemnawaveStreamAuthoritativeReadError(
                        "Authoritative Remnawave node connection result is inconsistent"
                    )
                return AuthoritativeNodePresenceSnapshot(
                    node_id=node_id,
                    observed_at=self._aware_utc(self._clock()),
                    users=tuple(
                        ConnectionUser(
                            user_id=user.user_id,
                            ips=tuple(
                                ConnectionIp(ip=item.ip, last_seen=self._aware_utc(item.last_seen)) for item in user.ips
                            ),
                        )
                        for user in payload.users
                    ),
                )
            if attempt + 1 < _MAX_CONNECTION_JOB_POLLS:
                await self._sleeper(0.25)
        raise RemnawaveStreamAuthoritativeReadError("Authoritative Remnawave node connection read timed out")

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
