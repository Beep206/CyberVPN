"""Exact, bounded Remnawave 3.4.3 operator contracts."""

from __future__ import annotations

import json
import re
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TagResource = Literal[
    "subscription-page-configs",
    "users",
    "subscription-templates",
    "config-profiles",
    "internal-squads",
    "external-squads",
    "nodes",
    "node-plugins",
    "hosts",
]
MutableTagResource = Literal[
    "subscription-page-configs",
    "subscription-templates",
    "config-profiles",
    "internal-squads",
    "external-squads",
    "node-plugins",
]

_TAG_PATTERN = re.compile(r"^[A-Z0-9_:]+$")
_SNIPPET_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_ -]+(?:/[A-Za-z0-9_ -]+)*$")
_SHARED_LIST_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*$")
_MAX_OPERATOR_JSON_BYTES = 512 * 1024
_MAX_OPERATOR_JSON_DEPTH = 12
_MAX_OPERATOR_JSON_NODES = 20_000


class _RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class _ResponseModel(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        validate_by_alias=True,
        validate_by_name=True,
    )


def _validate_bounded_json(value: Any) -> Any:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    if len(encoded) > _MAX_OPERATOR_JSON_BYTES:
        raise ValueError("operator JSON payload exceeds 512 KiB")
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_OPERATOR_JSON_NODES:
            raise ValueError("operator JSON payload is too complex")
        if depth > _MAX_OPERATOR_JSON_DEPTH:
            raise ValueError("operator JSON payload is nested too deeply")
        if isinstance(current, dict):
            if any(not isinstance(key, str) or len(key) > 255 for key in current):
                raise ValueError("operator JSON object key is invalid")
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
        elif not isinstance(current, (str, int, float, bool, type(None))):
            raise ValueError("operator JSON payload contains an unsupported value")
        elif isinstance(current, str) and len(current) > 128 * 1024:
            raise ValueError("operator JSON string is too large")
    return value


class OperatorMutationReceipt(_ResponseModel):
    attempt_id: UUID
    state: Literal["accepted", "reconciliation_required"]
    resource_kind: str = Field(min_length=3, max_length=80)
    requires_reconciliation: bool


class TagsResponse(_ResponseModel):
    resource: TagResource
    tags: list[str]


class UpstreamTagsResponse(_ResponseModel):
    tags: list[str]


TagValue = Annotated[str, Field(min_length=1, max_length=36, pattern=r"^[A-Z0-9_:]+$")]


class SetTagsRequest(_RequestModel):
    uuid: UUID
    tags: list[TagValue] = Field(max_length=10)

    @field_validator("tags")
    @classmethod
    def reject_duplicate_tags(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)) or any(_TAG_PATTERN.fullmatch(value) is None for value in values):
            raise ValueError("tags must be unique uppercase values")
        return values


class SetTagsResponse(_ResponseModel):
    uuid: UUID
    tags: list[str]


class GeoCheckRequest(_RequestModel):
    ip: str | None = Field(default=None, min_length=2, max_length=255)
    interface: str | None = Field(default=None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def require_at_most_one_source(self) -> GeoCheckRequest:
        if self.ip is not None and self.interface is not None:
            raise ValueError("ip and interface are mutually exclusive")
        return self


class GeoCheckJobResponse(_ResponseModel):
    job_id: str = Field(alias="jobId", min_length=1, max_length=255)


class GeoCheckImage(_ResponseModel):
    format: Literal["svg"]
    media_type: Literal["image/svg+xml"]
    encoding: Literal["base64"]
    data: str = Field(max_length=8 * 1024 * 1024)


class GeoCheckResult(_ResponseModel):
    success: bool
    node_uuid: UUID = Field(alias="nodeUuid")
    image: GeoCheckImage | None
    raw_report: dict[str, Any] | None = Field(alias="rawReport")
    message: str | None = Field(max_length=4_096)

    @field_validator("raw_report")
    @classmethod
    def bound_raw_report(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return _validate_bounded_json(value) if value is not None else None


class GeoCheckResultResponse(_ResponseModel):
    is_completed: bool = Field(alias="isCompleted")
    is_failed: bool = Field(alias="isFailed")
    result: GeoCheckResult | None


class NodeIntegration(_ResponseModel):
    uuid: UUID
    name: str = Field(min_length=2, max_length=30)
    description: str | None = Field(default=None, max_length=255)
    config: dict[str, Any]

    @field_validator("config")
    @classmethod
    def bound_config(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_bounded_json(value)


class NodeIntegrationCollection(_ResponseModel):
    total: int = Field(ge=0)
    node_integrations: list[NodeIntegration] = Field(alias="nodeIntegrations", max_length=10_000)


class AdminNodeIntegrationCollection(_ResponseModel):
    total: int = Field(ge=0)
    items: list[NodeIntegration] = Field(max_length=10_000)


class CreateNodeIntegrationRequest(_RequestModel):
    name: str = Field(min_length=2, max_length=30)
    description: str | None = Field(default=None, max_length=255)
    config: dict[str, Any]

    @field_validator("config")
    @classmethod
    def bound_config(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_bounded_json(value)


class UpdateNodeIntegrationRequest(_RequestModel):
    uuid: UUID
    name: str | None = Field(default=None, min_length=2, max_length=30)
    description: str | None = Field(default=None, max_length=255)
    config: dict[str, Any] | None = None
    restart_nodes: bool | None = Field(default=None, alias="restartNodes")

    @field_validator("config")
    @classmethod
    def bound_config(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return _validate_bounded_json(value) if value is not None else None

    @model_validator(mode="after")
    def require_update_field(self) -> UpdateNodeIntegrationRequest:
        fields = self.model_fields_set - {"uuid"}
        if not fields:
            raise ValueError("at least one integration update field is required")
        if "name" in fields and self.name is None:
            raise ValueError("integration name cannot be null")
        if "config" in fields and self.config is None:
            raise ValueError("integration config cannot be null")
        if "restart_nodes" in fields and self.restart_nodes is None:
            raise ValueError("restartNodes cannot be null")
        return self


SharedListName = Annotated[
    str,
    Field(min_length=2, max_length=255, pattern=r"^[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*$"),
]


class SharedListPreview(_ResponseModel):
    name: SharedListName
    type: str = Field(min_length=1, max_length=80)
    items_count: int = Field(alias="itemsCount", ge=0)


class SharedListPreviewCollection(_ResponseModel):
    total: int = Field(ge=0)
    shared_lists: list[SharedListPreview] = Field(alias="sharedLists", max_length=10_000)


class AdminSharedListPreviewCollection(_ResponseModel):
    total: int = Field(ge=0)
    items: list[SharedListPreview] = Field(max_length=10_000)


class SharedList(_ResponseModel):
    name: SharedListName
    config: dict[str, Any]

    @field_validator("config")
    @classmethod
    def bound_config(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_bounded_json(value)


class SharedListMutationRequest(_RequestModel):
    name: SharedListName
    config: dict[str, Any]

    @field_validator("config")
    @classmethod
    def bound_config(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_bounded_json(value)


class NamedOperatorRequest(_RequestModel):
    name: str = Field(min_length=2, max_length=255)


class SharedListNameRequest(_RequestModel):
    name: SharedListName


SnippetName = Annotated[
    str,
    Field(min_length=2, max_length=255, pattern=r"^[A-Za-z0-9_ -]+(?:/[A-Za-z0-9_ -]+)*$"),
]


class Snippet(_ResponseModel):
    name: SnippetName
    snippet: list[dict[str, Any]] = Field(max_length=5_000)

    @field_validator("snippet")
    @classmethod
    def bound_snippet(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return _validate_bounded_json(value)


class SnippetCollection(_ResponseModel):
    total: int = Field(ge=0)
    snippets: list[Snippet] = Field(max_length=10_000)


class AdminSnippetCollection(_ResponseModel):
    total: int = Field(ge=0)
    items: list[Snippet] = Field(max_length=10_000)


class SnippetMutationRequest(_RequestModel):
    name: SnippetName
    snippet: list[dict[str, Any]] = Field(max_length=5_000)

    @field_validator("snippet")
    @classmethod
    def bound_snippet(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return _validate_bounded_json(value)


class SnippetNameRequest(_RequestModel):
    name: SnippetName


def validate_snippet_name(name: str) -> str:
    if _SNIPPET_NAME_PATTERN.fullmatch(name) is None:
        raise ValueError("invalid snippet name")
    return name


def validate_shared_list_name(name: str) -> str:
    if _SHARED_LIST_NAME_PATTERN.fullmatch(name) is None:
        raise ValueError("invalid shared-list name")
    return name
