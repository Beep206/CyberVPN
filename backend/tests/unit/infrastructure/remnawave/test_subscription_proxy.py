from __future__ import annotations

import httpx
import pytest

from src.infrastructure.remnawave import subscription_proxy as proxy_module
from src.infrastructure.remnawave.subscription_proxy import (
    MAX_SUBSCRIPTION_RESPONSE_BYTES,
    RemnawaveSubscriptionProxyClient,
    SubscriptionUpstreamNotFoundError,
    SubscriptionUpstreamUnavailableError,
)


class _OversizedStream(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.read_past_limit = False

    async def __aiter__(self):
        yield b"1234"
        yield b"5"
        self.read_past_limit = True
        yield b"must-not-be-read"


def _client(handler) -> RemnawaveSubscriptionProxyClient:
    result = RemnawaveSubscriptionProxyClient()
    result._client = httpx.AsyncClient(
        base_url="http://remnawave.test",
        transport=httpx.MockTransport(handler),
        trust_env=False,
    )
    return result


@pytest.mark.asyncio
async def test_fetch_forwards_only_caller_supplied_trusted_headers_and_safe_response_headers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/sub/abcdefghijklmnop"
        assert request.headers["x-cybervpn-product"] == "premium_smart_ru"
        assert "authorization" not in request.headers
        return httpx.Response(
            200,
            content=b"subscription-body",
            headers={
                "Content-Type": "application/json",
                "Routing": "encoded-routing-policy",
                "Subscription-Userinfo": "upload=0; download=1",
                "Set-Cookie": "must-not-leak=true",
            },
        )

    proxy = _client(handler)
    try:
        response = await proxy.fetch(
            "abcdefghijklmnop",
            headers={"X-CyberVPN-Product": "premium_smart_ru"},
        )
    finally:
        await proxy.close()

    assert response.content == b"subscription-body"
    assert response.headers["content-type"] == "application/json"
    assert response.headers["routing"] == "encoded-routing-policy"
    assert response.headers["subscription-userinfo"] == "upload=0; download=1"
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers


@pytest.mark.asyncio
async def test_fetch_maps_missing_or_disabled_subscription_to_not_found() -> None:
    proxy = _client(lambda _request: httpx.Response(403))
    try:
        with pytest.raises(SubscriptionUpstreamNotFoundError):
            await proxy.fetch("abcdefghijklmnop", headers={})
    finally:
        await proxy.close()


@pytest.mark.asyncio
async def test_fetch_rejects_oversized_response_before_returning_it() -> None:
    proxy = _client(
        lambda _request: httpx.Response(
            200,
            content=b"x",
            headers={"Content-Length": str(MAX_SUBSCRIPTION_RESPONSE_BYTES + 1)},
        )
    )
    try:
        with pytest.raises(SubscriptionUpstreamUnavailableError):
            await proxy.fetch("abcdefghijklmnop", headers={})
    finally:
        await proxy.close()


@pytest.mark.asyncio
async def test_fetch_stops_streaming_immediately_after_decoded_body_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = _OversizedStream()
    monkeypatch.setattr(proxy_module, "MAX_SUBSCRIPTION_RESPONSE_BYTES", 4)
    proxy = _client(lambda _request: httpx.Response(200, stream=stream))
    try:
        with pytest.raises(SubscriptionUpstreamUnavailableError):
            await proxy.fetch("abcdefghijklmnop", headers={})
    finally:
        await proxy.close()

    assert stream.read_past_limit is False
