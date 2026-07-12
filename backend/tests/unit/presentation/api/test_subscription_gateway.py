from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from src.application.use_cases.subscription_gateway.resolve import (
    ResolvedSubscriptionProduct,
    SubscriptionGatewayNotFoundError,
)
from src.infrastructure.monitoring.subscription_gateway_metrics import subscription_response_total
from src.infrastructure.remnawave.subscription_proxy import SubscriptionProxyResponse
from src.presentation.api.subscription_gateway import routes
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.subscription_gateway import get_remnawave_subscription_proxy_client


def _request(*, headers: list[tuple[bytes, bytes]]) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/api/sub/abcdefghijklmnop",
            "raw_path": b"/api/sub/abcdefghijklmnop",
            "query_string": b"",
            "headers": headers,
            "client": ("203.0.113.9", 12345),
            "server": ("cyber-vpn.org", 443),
        }
    )


def test_build_upstream_headers_overwrites_spoofed_product_headers() -> None:
    request = _request(
        headers=[
            (b"user-agent", b"INCY/1.2"),
            (b"x-hwid", b"device-1"),
            (b"x-cybervpn-product", b"attacker-plan"),
            (b"x-cybervpn-client-family", b"attacker-family"),
            (b"x-cybervpn-xray-failover-canary", b"1"),
            (b"authorization", b"Bearer must-not-forward"),
        ]
    )

    headers = routes.build_upstream_headers(
        request,
        product_code="premium_smart_ru",
        client_family="incy",
    )

    assert headers["X-CyberVPN-Product"] == "premium_smart_ru"
    assert headers["X-CyberVPN-Client-Family"] == "incy"
    assert headers["x-hwid"] == "device-1"
    assert "authorization" not in {name.lower() for name in headers}
    assert routes.XRAY_FAILOVER_CANARY_HEADER not in headers
    assert "attacker-plan" not in headers.values()
    assert "attacker-family" not in headers.values()


@pytest.mark.parametrize("client_family", ["incy", "happ"])
def test_build_upstream_headers_emits_server_owned_canary_for_xray_clients(client_family: str) -> None:
    request = _request(
        headers=[
            (b"user-agent", f"{client_family}/1.2".encode()),
            (b"x-cybervpn-xray-failover-canary", b"spoofed"),
        ]
    )

    headers = routes.build_upstream_headers(
        request,
        product_code="premium_smart_ru",
        client_family=client_family,
        xray_failover_canary=True,
    )

    assert headers[routes.XRAY_FAILOVER_CANARY_HEADER] == "1"
    assert "spoofed" not in headers.values()


@pytest.mark.parametrize(
    ("product_code", "client_family", "xray_failover_canary"),
    [
        ("premium_spb_de_exceptions", "incy", True),
        ("premium_smart_ru", "browser", True),
        ("premium_smart_ru", "generic", True),
        ("premium_smart_ru", "mihomo", True),
        ("premium_smart_ru", "happ", False),
        ("premium_smart_ru", "incy", False),
    ],
)
def test_build_upstream_headers_omits_canary_for_other_products_families_or_disabled_resolver_flag(
    product_code: str,
    client_family: str,
    xray_failover_canary: bool,
) -> None:
    request = _request(headers=[(b"x-cybervpn-xray-failover-canary", b"spoofed")])

    headers = routes.build_upstream_headers(
        request,
        product_code=product_code,
        client_family=client_family,
        xray_failover_canary=xray_failover_canary,
    )

    assert routes.XRAY_FAILOVER_CANARY_HEADER not in headers
    assert "spoofed" not in headers.values()


@pytest.mark.parametrize(
    ("user_agent", "accept", "expected"),
    [
        ("INCY/3.3.1/android Dalvik/2.1.0", "*/*", "incy"),
        ("INCY/2.0.3", "*/*", "incy"),
        ("Happ/3.0 Android", "*/*", "happ"),
        ("Happ/3.0 iOS", "*/*", "happ"),
        ("ClashMetaForAndroid/2.11", "*/*", "mihomo"),
        ("Mozilla/5.0", "text/html,application/xhtml+xml", "browser"),
        ("sing-box/1.12", "*/*", "generic"),
        ("unhappy-client/1.0", "*/*", "generic"),
        ("notincy/1.0", "*/*", "generic"),
    ],
)
def test_classify_client_family(user_agent: str, accept: str, expected: str) -> None:
    request = _request(headers=[(b"user-agent", user_agent.encode()), (b"accept", accept.encode())])

    assert routes.classify_client_family(request) == expected


@pytest.mark.parametrize(
    ("client_family", "expected"),
    [
        ("browser", "BROWSER"),
        ("mihomo", "MIHOMO"),
        ("incy", "XRAY_JSON"),
        ("happ", "XRAY_JSON"),
        ("generic", "COMPATIBILITY"),
    ],
)
def test_response_type_is_bounded_by_client_family(client_family: str, expected: str) -> None:
    assert routes.response_type_for_client_family(client_family) == expected


@pytest.mark.asyncio
async def test_gateway_resolves_server_owned_product_before_proxying(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Resolver:
        def __init__(self, db, client) -> None:
            captured["db"] = db
            captured["management_client"] = client

        async def execute(self, short_uuid: str) -> ResolvedSubscriptionProduct:
            captured["short_uuid"] = short_uuid
            return ResolvedSubscriptionProduct(product_code="premium_smart_ru", xray_failover_canary=True)

    class _Proxy:
        async def fetch(self, short_uuid: str, *, headers: dict[str, str]):
            captured["proxy_short_uuid"] = short_uuid
            captured["headers"] = headers
            return SubscriptionProxyResponse(
                content=b'{"outbounds":[]}',
                headers={"content-type": "application/json", "cache-control": "no-store"},
            )

    db = SimpleNamespace()
    management_client = SimpleNamespace()
    proxy = _Proxy()
    monkeypatch.setattr(routes, "ResolveSubscriptionProductUseCase", _Resolver)

    app = FastAPI()
    app.include_router(routes.router)

    async def _db_override():
        yield db

    async def _management_override():
        return management_client

    async def _proxy_override():
        return proxy

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_remnawave_client] = _management_override
    app.dependency_overrides[get_remnawave_subscription_proxy_client] = _proxy_override

    metric = subscription_response_total.labels(
        product="premium_smart_ru",
        client="incy",
        response_type="XRAY_JSON",
    )
    metric_before = metric._value.get()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://cyber-vpn.org",
    ) as client:
        response = await client.get(
            "/api/sub/abcdefghijklmnop",
            headers={
                "User-Agent": "INCY/1.2",
                "X-CyberVPN-Product": "premium_spb_de_exceptions",
                "X-CyberVPN-Xray-Failover-Canary": "spoofed",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"outbounds": []}
    assert captured["db"] is db
    assert captured["management_client"] is management_client
    assert captured["short_uuid"] == "abcdefghijklmnop"
    assert captured["proxy_short_uuid"] == "abcdefghijklmnop"
    forwarded_headers = cast(dict[str, str], captured["headers"])
    assert forwarded_headers["X-CyberVPN-Product"] == "premium_smart_ru"
    assert forwarded_headers["X-CyberVPN-Client-Family"] == "incy"
    assert forwarded_headers[routes.XRAY_FAILOVER_CANARY_HEADER] == "1"
    assert metric._value.get() == metric_before + 1


@pytest.mark.asyncio
async def test_gateway_omits_spoofed_canary_when_resolver_flag_is_false(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Resolver:
        def __init__(self, db, client) -> None:
            captured["db"] = db
            captured["management_client"] = client

        async def execute(self, short_uuid: str) -> ResolvedSubscriptionProduct:
            captured["short_uuid"] = short_uuid
            return ResolvedSubscriptionProduct(product_code="premium_smart_ru", xray_failover_canary=False)

    class _Proxy:
        async def fetch(self, short_uuid: str, *, headers: dict[str, str]):
            captured["proxy_short_uuid"] = short_uuid
            captured["headers"] = headers
            return SubscriptionProxyResponse(
                content=b'{"outbounds":[]}',
                headers={"content-type": "application/json", "cache-control": "no-store"},
            )

    db = SimpleNamespace()
    management_client = SimpleNamespace()
    proxy = _Proxy()
    monkeypatch.setattr(routes, "ResolveSubscriptionProductUseCase", _Resolver)

    app = FastAPI()
    app.include_router(routes.router)

    async def _db_override():
        yield db

    async def _management_override():
        return management_client

    async def _proxy_override():
        return proxy

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_remnawave_client] = _management_override
    app.dependency_overrides[get_remnawave_subscription_proxy_client] = _proxy_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://cyber-vpn.org",
    ) as client:
        response = await client.get(
            "/api/sub/abcdefghijklmnop",
            headers={
                "User-Agent": "INCY/1.2",
                "X-CyberVPN-Xray-Failover-Canary": "spoofed",
            },
        )

    assert response.status_code == 200
    assert captured["db"] is db
    assert captured["management_client"] is management_client
    assert captured["short_uuid"] == "abcdefghijklmnop"
    assert captured["proxy_short_uuid"] == "abcdefghijklmnop"
    forwarded_headers = cast(dict[str, str], captured["headers"])
    assert routes.XRAY_FAILOVER_CANARY_HEADER not in forwarded_headers
    assert "spoofed" not in forwarded_headers.values()


@pytest.mark.asyncio
async def test_gateway_not_found_resolution_does_not_proxy(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Resolver:
        def __init__(self, db, client) -> None:
            captured["db"] = db
            captured["management_client"] = client

        async def execute(self, short_uuid: str) -> ResolvedSubscriptionProduct:
            captured["short_uuid"] = short_uuid
            raise SubscriptionGatewayNotFoundError

    class _Proxy:
        async def fetch(self, short_uuid: str, *, headers: dict[str, str]):  # noqa: ARG002
            raise AssertionError("unresolved subscriptions must not be proxied to Remnawave")

    db = SimpleNamespace()
    management_client = SimpleNamespace()
    proxy = _Proxy()
    monkeypatch.setattr(routes, "ResolveSubscriptionProductUseCase", _Resolver)

    app = FastAPI()
    app.include_router(routes.router)

    async def _db_override():
        yield db

    async def _management_override():
        return management_client

    async def _proxy_override():
        return proxy

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_remnawave_client] = _management_override
    app.dependency_overrides[get_remnawave_subscription_proxy_client] = _proxy_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://cyber-vpn.org",
    ) as client:
        response = await client.get(
            "/api/sub/abcdefghijklmnop",
            headers={"User-Agent": "INCY/1.2"},
        )

    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store"
    assert captured["db"] is db
    assert captured["management_client"] is management_client
    assert captured["short_uuid"] == "abcdefghijklmnop"
