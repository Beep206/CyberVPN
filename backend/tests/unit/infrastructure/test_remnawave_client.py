from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import BaseModel

from src.infrastructure.remnawave import client as remnawave_client_module
from src.infrastructure.remnawave.client import (
    RemnawaveClient,
    RemnawaveHTTPStatusError,
    RemnawaveProtocolError,
    RemnawaveTransportError,
)
from src.infrastructure.remnawave.contracts import RemnawaveDeleteResponse


def test_normalize_base_url_strips_api_suffix():
    assert RemnawaveClient._normalize_base_url("http://localhost:3005/api") == "http://localhost:3005"
    assert RemnawaveClient._normalize_base_url("http://localhost:3005") == "http://localhost:3005"


def test_normalize_path_prefixes_api_once():
    assert RemnawaveClient._normalize_path("/system/health") == "/api/system/health"
    assert RemnawaveClient._normalize_path("/api/system/health") == "/api/system/health"
    assert RemnawaveClient._normalize_path("node-plugins") == "/api/node-plugins"


@pytest.mark.unit
async def test_http_client_ignores_ambient_proxy_environment(monkeypatch):
    captured: dict[str, object] = {}

    class _Client:
        is_closed = False

    def _factory(**kwargs):
        captured.update(kwargs)
        return _Client()

    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:3128")
    monkeypatch.setenv("ALL_PROXY", "http://proxy.invalid:3128")
    monkeypatch.setattr(remnawave_client_module, "AsyncClient", _factory)

    await RemnawaveClient()._get_client()

    assert captured["trust_env"] is False


class _CollectionItem(BaseModel):
    uuid: str


class _RequiredMutationResponse(BaseModel):
    operation_id: str


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

    async def post(self, *_args, **_kwargs):
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
async def test_get_collection_validated_accepts_response_keyed_collection_envelope(monkeypatch):
    client = RemnawaveClient()
    monkeypatch.setattr(
        client,
        "get",
        AsyncMock(return_value={"response": {"total": 1, "configProfiles": [{"uuid": "profile-1"}]}}),
    )

    result = await client.get_collection_validated("/config-profiles", "configProfiles", _CollectionItem)

    assert [item.uuid for item in result] == ["profile-1"]


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
        "_request",
        AsyncMock(return_value=_DeleteTransportResponse()),
    )

    result = await client.delete_validated("/users/demo", RemnawaveDeleteResponse)

    assert result is None
    client._request.assert_awaited_once_with("DELETE", "/users/demo")


@pytest.mark.unit
@pytest.mark.parametrize(
    ("method_name", "http_method"),
    [
        ("post_validated", "POST"),
        ("put_validated", "PUT"),
        ("patch_validated", "PATCH"),
        ("delete_validated", "DELETE"),
    ],
)
@pytest.mark.parametrize("status_code", [201, 202, 204])
async def test_validated_mutation_accepts_empty_success_without_repeating_request(
    monkeypatch,
    method_name: str,
    http_method: str,
    status_code: int,
):
    client = RemnawaveClient()
    request = AsyncMock(return_value=_DeleteTransportResponse(status_code=status_code))
    monkeypatch.setattr(client, "_request", request)

    result = await getattr(client, method_name)("/operations/demo", _RequiredMutationResponse)

    assert result is None
    request.assert_awaited_once_with(http_method, "/operations/demo")


@pytest.mark.unit
async def test_validated_mutation_still_validates_non_empty_202_response(monkeypatch):
    client = RemnawaveClient()
    response = httpx.Response(
        202,
        json={"response": {"operation_id": "op-42"}},
        request=httpx.Request("POST", "http://test/api/operations/demo"),
    )
    request = AsyncMock(return_value=response)
    monkeypatch.setattr(client, "_request", request)

    result = await client.post_validated("/operations/demo", _RequiredMutationResponse)

    assert result == _RequiredMutationResponse(operation_id="op-42")
    request.assert_awaited_once_with("POST", "/operations/demo")


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


@pytest.mark.unit
async def test_post_does_not_retry_ambiguous_http_503(monkeypatch):
    client = RemnawaveClient()
    request = httpx.Request("POST", "http://test/api/users")
    transport = _RetryGetTransport(
        [
            httpx.Response(503, request=request, json={"detail": "temporary"}),
            httpx.Response(201, request=request, json={"response": {"id": 42}}),
        ]
    )

    client._retry_attempts = 2
    client._retry_backoff_seconds = 0.0
    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=transport))

    with pytest.raises(httpx.HTTPStatusError):
        await client.post("/users", json={"username": "alice"})

    assert transport.calls == 1


@pytest.mark.unit
async def test_http_error_does_not_retain_provider_body_request_or_credentials(monkeypatch, caplog):
    client = RemnawaveClient()
    client._retry_attempts = 0
    leaks = (
        "alice@example.com",
        "provider-secret-token",
        "https://subscription.example/live-key",
    )
    request = httpx.Request(
        "POST",
        f"http://test/api/users/{leaks[0]}?token={leaks[1]}",
        headers={"Authorization": f"Bearer {leaks[1]}"},
    )
    response = httpx.Response(
        503,
        request=request,
        headers={"x-request-id": "req-safe-123"},
        json={"detail": leaks[2], "email": leaks[0], "token": leaks[1]},
    )
    transport = _RetryGetTransport([response])
    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=transport))

    with caplog.at_level("WARNING"), pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.post("/users", json={"email": leaks[0], "password": leaks[1]})

    error = exc_info.value
    logged = "\n".join(f"{record.getMessage()} {record.__dict__!r}" for record in caplog.records)
    assert isinstance(error, RemnawaveHTTPStatusError)
    assert error.error_code == "remnawave_upstream_http_error"
    assert error.correlation_id == "req-safe-123"
    assert error.response.status_code == 503
    assert error.response.content == b""
    assert str(error.request.url) == "https://remnawave.invalid/"
    assert "authorization" not in error.request.headers
    assert error.__context__ is None
    assert transport.calls == 1
    for leak in leaks:
        assert leak not in str(error)
        assert leak not in repr(error)
        assert leak not in logged
        assert leak not in str(error.request.url)


@pytest.mark.unit
async def test_transport_error_does_not_retain_provider_message_url_or_headers(monkeypatch, caplog):
    client = RemnawaveClient()
    client._retry_attempts = 0
    leaks = ("alice@example.com", "provider-secret-token")
    request = httpx.Request(
        "GET",
        f"http://test/api/users/{leaks[0]}?token={leaks[1]}",
        headers={"Authorization": f"Bearer {leaks[1]}"},
    )
    transport = _RetryGetTransport(
        [httpx.ConnectError(f"connection failed for {leaks[0]} using {leaks[1]}", request=request)]
    )
    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=transport))

    with caplog.at_level("WARNING"), pytest.raises(httpx.RequestError) as exc_info:
        await client.get("/users")

    error = exc_info.value
    logged = "\n".join(f"{record.getMessage()} {record.__dict__!r}" for record in caplog.records)
    assert isinstance(error, RemnawaveTransportError)
    assert error.error_code == "remnawave_upstream_transport_error"
    assert str(error.request.url) == "https://remnawave.invalid/"
    assert "authorization" not in error.request.headers
    assert error.__context__ is None
    assert transport.calls == 1
    for leak in leaks:
        assert leak not in str(error)
        assert leak not in repr(error)
        assert leak not in logged
        assert leak not in str(error.request.url)


@pytest.mark.unit
async def test_invalid_json_does_not_retain_provider_response_text(monkeypatch):
    client = RemnawaveClient()
    leak = "alice@example.com provider-secret-token"
    request = httpx.Request("GET", "http://test/api/users")
    transport = _RetryGetTransport([httpx.Response(200, request=request, content=leak.encode())])
    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=transport))

    with pytest.raises(RemnawaveProtocolError) as exc_info:
        await client.get("/users")

    error = exc_info.value
    assert error.error_code == "remnawave_upstream_protocol_error"
    assert leak not in str(error)
    assert leak not in repr(error)
    assert error.__context__ is None


@pytest.mark.unit
@pytest.mark.parametrize("status_code", [202, 204])
async def test_post_accepts_empty_remnawave_action_response(monkeypatch, status_code):
    client = RemnawaveClient()
    request = httpx.Request("POST", "http://test/api/users/42/actions/revoke")
    transport = _RetryGetTransport([httpx.Response(status_code, request=request, content=b"")])
    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=transport))

    result = await client.post("/users/42/actions/revoke")

    assert result == {}
    assert transport.calls == 1


@pytest.mark.unit
async def test_legacy_post_preserves_non_empty_202_response(monkeypatch):
    client = RemnawaveClient()
    request = httpx.Request("POST", "http://test/api/operations")
    transport = _RetryGetTransport([httpx.Response(202, request=request, json={"response": {"operationId": "op-42"}})])
    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=transport))

    result = await client.post("/operations")

    assert result == {"operationId": "op-42"}
    assert transport.calls == 1


@pytest.mark.unit
async def test_users_cursor_uses_remnawave_3_stream_route(monkeypatch):
    client = RemnawaveClient()
    get = AsyncMock(
        return_value={
            "users": [{"id": 42, "username": "alice"}],
            "nextCursor": "43",
            "hasMore": True,
        }
    )
    monkeypatch.setattr(client, "get", get)

    page = await client.get_all_users_cursor_page(cursor="41", limit=2000)

    get.assert_awaited_once_with("/users/stream", params={"size": 1000, "cursor": "41"})
    assert page.items == [{"id": 42, "username": "alice"}]
    assert page.next_cursor == "43"
    assert page.has_next_page is True
