import json
from contextlib import AbstractAsyncContextManager
from typing import Any
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError
from websockets.asyncio.client import ClientConnection

from src.infrastructure.remnawave import node_ssh_gateway as gateway_module
from src.infrastructure.remnawave.node_ssh_gateway import (
    REMNAWAVE_SSH_BROKER_HEADER,
    RemnawaveNodeSshGateway,
    RemnawaveNodeSshScopedBrokerUnavailable,
    RemnawaveUpstreamSshTicket,
    _validated_websocket_endpoint,
)

BROKER_SECRET = "a" * 128
TICKET = "t" * 43
CREDENTIAL = "c" * 43


def _success_payload(**overrides: object) -> dict[str, object]:
    response: dict[str, object] = {
        "ticket": TICKET,
        "credential": CREDENTIAL,
        "path": "/api/cybervpn/node-ssh/ws",
        "protocol": "rw-cybervpn",
        "expiresInSeconds": 10,
    }
    response.update(overrides)
    return {"response": response}


@pytest.mark.unit
async def test_gateway_uses_only_scoped_header_and_exact_actor_bound_contract() -> None:
    node_uuid = uuid4()
    actor_uuid = uuid4()
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json=_success_payload(), request=request)

    client = httpx.AsyncClient(
        base_url="https://panel.internal",
        transport=httpx.MockTransport(handler),
        trust_env=False,
    )
    gateway = RemnawaveNodeSshGateway(
        remnawave_url="https://panel.internal/api",
        broker_secret=BROKER_SECRET,
        http_client=client,
    )

    result = await gateway.create_ticket(str(node_uuid), actor_reference=str(actor_uuid))

    assert result.ticket == TICKET
    assert result.credential == CREDENTIAL
    assert captured["method"] == "POST"
    assert captured["path"] == f"/api/cybervpn/node-ssh/tickets/{node_uuid}"
    assert captured["body"] == {"actorReference": str(actor_uuid)}
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers[REMNAWAVE_SSH_BROKER_HEADER.lower()] == BROKER_SECRET
    assert "authorization" not in headers
    await client.aclose()


@pytest.mark.unit
async def test_gateway_fails_closed_without_secret_before_any_rest_request() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(201, json=_success_payload(), request=request)

    client = httpx.AsyncClient(
        base_url="https://panel.internal",
        transport=httpx.MockTransport(handler),
        trust_env=False,
    )
    gateway = RemnawaveNodeSshGateway(
        remnawave_url="https://panel.internal",
        broker_secret="",
        http_client=client,
    )

    with pytest.raises(RemnawaveNodeSshScopedBrokerUnavailable):
        await gateway.create_ticket(str(uuid4()), actor_reference=str(uuid4()))
    with pytest.raises(RemnawaveNodeSshScopedBrokerUnavailable):
        await gateway.evaluate_vault("YmxpbmRlZA==")

    assert calls == 0
    await client.aclose()


@pytest.mark.unit
async def test_gateway_rejects_client_that_carries_generic_authorization() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(201, json=_success_payload(), request=request)

    client = httpx.AsyncClient(
        base_url="https://panel.internal",
        headers={"Authorization": "Bearer generic-admin-token"},
        transport=httpx.MockTransport(handler),
        trust_env=False,
    )
    gateway = RemnawaveNodeSshGateway(
        remnawave_url="https://panel.internal",
        broker_secret=BROKER_SECRET,
        http_client=client,
    )

    with pytest.raises(RemnawaveNodeSshScopedBrokerUnavailable, match="must not carry"):
        await gateway.create_ticket(str(uuid4()), actor_reference=str(uuid4()))

    assert calls == 0
    await client.aclose()


class _FakeConnectionContext(AbstractAsyncContextManager[ClientConnection]):
    async def __aenter__(self) -> ClientConnection:
        raise AssertionError("test only inspects the constructed WebSocket handshake")

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        _ = exc_type, exc_value, traceback


@pytest.mark.unit
def test_gateway_websocket_offers_exact_scoped_protocol_pair(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    context = _FakeConnectionContext()

    def capture_connect(uri: str, **kwargs: Any) -> AbstractAsyncContextManager[ClientConnection]:
        captured["uri"] = uri
        captured.update(kwargs)
        return context

    monkeypatch.setattr(gateway_module, "websocket_connect", capture_connect)
    gateway = RemnawaveNodeSshGateway(
        remnawave_url="https://panel.internal/api",
        broker_secret=BROKER_SECRET,
    )
    ticket = RemnawaveUpstreamSshTicket.model_validate(_success_payload()["response"])

    assert gateway.connect(ticket) is context
    assert captured["uri"] == "wss://panel.internal/api/cybervpn/node-ssh/ws"
    assert captured["subprotocols"] == ["rw-cybervpn", TICKET, CREDENTIAL]
    assert captured["compression"] is None
    assert captured["proxy"] is None
    assert "additional_headers" not in captured


@pytest.mark.unit
@pytest.mark.parametrize(
    "url",
    [
        "https://user:password@panel.internal/api",
        "https://panel.internal/unexpected",
        "https://panel.internal/api?token=secret",
        "file:///tmp/panel.sock",
    ],
)
def test_gateway_rejects_unsafe_upstream_websocket_urls(url: str) -> None:
    with pytest.raises(ValueError, match="REMNAWAVE_URL"):
        _validated_websocket_endpoint(url)


@pytest.mark.unit
@pytest.mark.parametrize(
    "overrides",
    [
        {"path": "/api/cybervpn/node-ssh/ws/../other"},
        {"protocol": "rw"},
        {"expiresInSeconds": 15},
        {"credential": TICKET},
        {"credential": "short"},
    ],
)
def test_gateway_rejects_malformed_or_scope_broadened_response(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        RemnawaveUpstreamSshTicket.model_validate(_success_payload(**overrides)["response"])
