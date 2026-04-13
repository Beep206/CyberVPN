from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import BaseModel

from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveDeleteResponse


def test_normalize_base_url_strips_api_suffix():
    assert RemnawaveClient._normalize_base_url("http://localhost:3005/api") == "http://localhost:3005"
    assert RemnawaveClient._normalize_base_url("http://localhost:3005") == "http://localhost:3005"


def test_normalize_path_prefixes_api_once():
    assert RemnawaveClient._normalize_path("/system/health") == "/api/system/health"
    assert RemnawaveClient._normalize_path("/api/system/health") == "/api/system/health"
    assert RemnawaveClient._normalize_path("node-plugins") == "/api/node-plugins"


class _CollectionItem(BaseModel):
    uuid: str


class _DeleteTransportResponse:
    def __init__(self, *, status_code: int = 204, content: bytes = b""):
        self.status_code = status_code
        self.content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        raise AssertionError("json() should not be called for empty delete responses")


class _DeleteTransport:
    def __init__(self, response: _DeleteTransportResponse):
        self._response = response

    async def delete(self, *_args, **_kwargs) -> _DeleteTransportResponse:
        return self._response


class _RetryGetTransport:
    def __init__(self, responses: list[object]):
        self._responses = responses
        self.calls = 0

    async def get(self, *_args, **_kwargs):
        response = self._responses[self.calls]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.unit
async def test_get_collection_validated_accepts_named_collection(monkeypatch):
    client = RemnawaveClient()
    monkeypatch.setattr(
        client,
        "get",
        AsyncMock(return_value={"templates": [{"uuid": "tpl-1"}]}),
    )

    result = await client.get_collection_validated("/subscription-templates", "templates", _CollectionItem)

    assert [item.uuid for item in result] == ["tpl-1"]


@pytest.mark.unit
async def test_get_collection_validated_accepts_response_envelope(monkeypatch):
    client = RemnawaveClient()
    monkeypatch.setattr(
        client,
        "get",
        AsyncMock(return_value={"response": [{"uuid": "node-1"}]}),
    )

    result = await client.get_collection_validated("/nodes", "nodes", _CollectionItem)

    assert [item.uuid for item in result] == ["node-1"]


@pytest.mark.unit
async def test_get_collection_validated_accepts_bare_list(monkeypatch):
    client = RemnawaveClient()
    monkeypatch.setattr(
        client,
        "get",
        AsyncMock(return_value=[{"uuid": "snippet-1"}]),
    )

    result = await client.get_collection_validated("/snippets", "snippets", _CollectionItem)

    assert [item.uuid for item in result] == ["snippet-1"]


@pytest.mark.unit
async def test_delete_returns_empty_dict_for_empty_body(monkeypatch):
    client = RemnawaveClient()
    monkeypatch.setattr(
        client,
        "_get_client",
        AsyncMock(return_value=_DeleteTransport(_DeleteTransportResponse())),
    )

    result = await client.delete("/users/demo")

    assert result == {}


@pytest.mark.unit
async def test_delete_validated_accepts_empty_delete_ack(monkeypatch):
    client = RemnawaveClient()
    monkeypatch.setattr(
        client,
        "delete",
        AsyncMock(return_value={}),
    )

    result = await client.delete_validated("/users/demo", RemnawaveDeleteResponse)

    assert result is not None
    assert result.is_deleted is True


@pytest.mark.unit
async def test_get_retries_once_on_http_503(monkeypatch):
    client = RemnawaveClient()
    request = httpx.Request("GET", "http://test/api/system/health")
    transport = _RetryGetTransport(
        [
            httpx.Response(503, request=request, json={"detail": "temporary"}),
            httpx.Response(200, request=request, json={"response": {"uuid": "node-1"}}),
        ]
    )

    client._retry_attempts = 1
    client._retry_backoff_seconds = 0.0
    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=transport))

    result = await client.get("/system/health")

    assert result == {"uuid": "node-1"}
    assert transport.calls == 2


@pytest.mark.unit
async def test_get_retries_once_on_transport_error(monkeypatch):
    client = RemnawaveClient()
    request = httpx.Request("GET", "http://test/api/nodes")
    transport = _RetryGetTransport(
        [
            httpx.ConnectError("upstream unavailable", request=request),
            httpx.Response(200, request=request, json=[{"uuid": "node-1"}]),
        ]
    )

    client._retry_attempts = 1
    client._retry_backoff_seconds = 0.0
    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=transport))

    result = await client.get("/nodes")

    assert result == [{"uuid": "node-1"}]
    assert transport.calls == 2
