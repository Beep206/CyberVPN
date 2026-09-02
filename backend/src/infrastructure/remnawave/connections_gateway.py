"""Typed Remnawave 3.4.3 connections API boundary.

The upstream read operations create short-lived jobs with POST and expose the
result through retry-safe GET requests. Connection dropping is an explicitly
single-attempt operation because upstream 3.4.3 has neither an idempotency key
nor a result/reconciliation route; callers must reserve local ambiguity state
before invoking it.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, ValidationError, field_validator, model_validator

from src.infrastructure.remnawave.client import RemnawaveClient

_JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_MAX_CONNECTION_IPS_PER_USER = 1_000
_MAX_CONNECTION_USERS_PER_NODE = 100_000
_MAX_CONNECTION_NODES_PER_USER = 1_000


class RemnawaveConnectionsInvalidResponseError(RuntimeError):
    """The provider returned a successful but unsafe or inconsistent payload."""


class RemnawaveConnectionJob(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    job_id: str = Field(alias="jobId", min_length=1, max_length=128)

    @field_validator("job_id")
    @classmethod
    def validate_job_id(cls, value: str) -> str:
        if _JOB_ID_RE.fullmatch(value) is None:
            raise ValueError("Invalid Remnawave connection job id")
        return value


class RemnawaveConnectionIp(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    ip: IPvAnyAddress
    last_seen: datetime = Field(alias="lastSeen")

    @field_validator("last_seen")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Remnawave connection timestamp must include timezone")
        return value.astimezone(UTC)

    @property
    def public_ip(self) -> str:
        return str(self.ip)


class RemnawaveConnectionProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    completed: int = Field(ge=0)
    percent: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_progress(self) -> RemnawaveConnectionProgress:
        if self.completed > self.total:
            raise ValueError("Remnawave connection progress exceeds total")
        return self


class RemnawaveUserConnectionNode(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    node_uuid: UUID = Field(alias="nodeUuid")
    node_name: str = Field(alias="nodeName", max_length=256)
    country_code: str = Field(alias="countryCode", max_length=16)
    ips: list[RemnawaveConnectionIp] = Field(max_length=_MAX_CONNECTION_IPS_PER_USER)


class RemnawaveUserConnectionsResult(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    success: bool
    user_id: int = Field(alias="userId", ge=1)
    nodes: list[RemnawaveUserConnectionNode] = Field(max_length=_MAX_CONNECTION_NODES_PER_USER)


class RemnawaveUserConnectionsJobResult(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    is_completed: bool = Field(alias="isCompleted")
    is_failed: bool = Field(alias="isFailed")
    progress: RemnawaveConnectionProgress
    result: RemnawaveUserConnectionsResult | None

    @model_validator(mode="after")
    def validate_terminal_shape(self) -> RemnawaveUserConnectionsJobResult:
        if self.is_completed and not self.is_failed and self.result is None:
            raise ValueError("Completed Remnawave user connection job has no result")
        if not self.is_completed and self.result is not None:
            raise ValueError("Pending Remnawave user connection job unexpectedly has a result")
        return self


class RemnawaveNodeConnectionUser(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    user_id: int = Field(alias="userId", ge=1)
    ips: list[RemnawaveConnectionIp] = Field(max_length=_MAX_CONNECTION_IPS_PER_USER)


class RemnawaveNodeConnectionsResult(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    success: bool
    node_uuid: UUID = Field(alias="nodeUuid")
    users: list[RemnawaveNodeConnectionUser] = Field(max_length=_MAX_CONNECTION_USERS_PER_NODE)


class RemnawaveNodeConnectionsJobResult(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    is_completed: bool = Field(alias="isCompleted")
    is_failed: bool = Field(alias="isFailed")
    result: RemnawaveNodeConnectionsResult | None

    @model_validator(mode="after")
    def validate_terminal_shape(self) -> RemnawaveNodeConnectionsJobResult:
        if self.is_completed and not self.is_failed and self.result is None:
            raise ValueError("Completed Remnawave node connection job has no result")
        if not self.is_completed and self.result is not None:
            raise ValueError("Pending Remnawave node connection job unexpectedly has a result")
        return self


class RemnawaveDropByUserIds(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    by: Literal["userIds"] = "userIds"
    user_ids: list[int] = Field(alias="userIds", min_length=1, max_length=1_000)


class RemnawaveDropByIpAddresses(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    by: Literal["ipAddresses"] = "ipAddresses"
    ip_addresses: list[IPvAnyAddress] = Field(alias="ipAddresses", min_length=1, max_length=1_000)


class RemnawaveDropOnAllNodes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: Literal["allNodes"] = "allNodes"


class RemnawaveDropOnSpecificNodes(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    target: Literal["specificNodes"] = "specificNodes"
    node_uuids: list[UUID] = Field(alias="nodeUuids", min_length=1, max_length=128)


RemnawaveDropBy = Annotated[
    RemnawaveDropByUserIds | RemnawaveDropByIpAddresses,
    Field(discriminator="by"),
]
RemnawaveDropTargetNodes = Annotated[
    RemnawaveDropOnAllNodes | RemnawaveDropOnSpecificNodes,
    Field(discriminator="target"),
]


class RemnawaveConnectionDropCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    drop_by: RemnawaveDropBy = Field(alias="dropBy")
    target_nodes: RemnawaveDropTargetNodes = Field(alias="targetNodes")

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, mode="json")


class RemnawaveConnectionsGateway:
    """Exact, bounded adapter for the Remnawave 3.4.3 connections routes."""

    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client

    async def request_by_user(self, user_id: int) -> RemnawaveConnectionJob:
        if isinstance(user_id, bool) or user_id <= 0:
            raise ValueError("Remnawave user id must be a positive integer")
        try:
            job = await self._client.post_validated(
                f"/connections/by-user/{user_id}",
                RemnawaveConnectionJob,
            )
        except ValidationError as exc:
            raise RemnawaveConnectionsInvalidResponseError("Invalid Remnawave connection job response") from exc
        if job is None:
            raise RemnawaveConnectionsInvalidResponseError("Remnawave connection job response was empty")
        return job

    async def get_by_user_result(
        self,
        *,
        job_id: str,
        expected_user_id: int,
    ) -> RemnawaveUserConnectionsJobResult:
        self._validate_job_id(job_id)
        try:
            result = await self._client.get_validated(
                f"/connections/by-user/{job_id}",
                RemnawaveUserConnectionsJobResult,
            )
        except ValidationError as exc:
            raise RemnawaveConnectionsInvalidResponseError("Invalid Remnawave user connections response") from exc
        if result.result is not None and result.result.user_id != expected_user_id:
            raise RemnawaveConnectionsInvalidResponseError("Remnawave user connection result target mismatch")
        return result

    async def request_by_node(self, node_uuid: UUID) -> RemnawaveConnectionJob:
        try:
            job = await self._client.post_validated(
                f"/connections/by-node/{node_uuid}",
                RemnawaveConnectionJob,
            )
        except ValidationError as exc:
            raise RemnawaveConnectionsInvalidResponseError("Invalid Remnawave connection job response") from exc
        if job is None:
            raise RemnawaveConnectionsInvalidResponseError("Remnawave connection job response was empty")
        return job

    async def get_by_node_result(
        self,
        *,
        job_id: str,
        expected_node_uuid: UUID,
    ) -> RemnawaveNodeConnectionsJobResult:
        self._validate_job_id(job_id)
        try:
            result = await self._client.get_validated(
                f"/connections/by-node/{job_id}",
                RemnawaveNodeConnectionsJobResult,
            )
        except ValidationError as exc:
            raise RemnawaveConnectionsInvalidResponseError("Invalid Remnawave node connections response") from exc
        if result.result is not None and result.result.node_uuid != expected_node_uuid:
            raise RemnawaveConnectionsInvalidResponseError("Remnawave node connection result target mismatch")
        return result

    async def drop_once(self, command: RemnawaveConnectionDropCommand) -> None:
        """Send exactly one drop request; callers own durable ambiguity handling."""

        await self._client.post(
            "/connections/drop",
            json=command.canonical_payload(),
        )

    @staticmethod
    def _validate_job_id(job_id: str) -> None:
        if _JOB_ID_RE.fullmatch(job_id) is None:
            raise RemnawaveConnectionsInvalidResponseError("Invalid stored Remnawave connection job id")
