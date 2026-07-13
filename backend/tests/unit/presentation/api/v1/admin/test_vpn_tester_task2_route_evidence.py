from __future__ import annotations

import asyncio
import json
from collections.abc import Generator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from redis.exceptions import RedisError

from src.application.vpn_testing.task2_route_evidence import (
    TASK2_ROUTE_EVIDENCE_RESULT_PREFIX,
    TASK2_XRAY_WEBHOOK_SECRET_HEADER,
    Task2RouteEvidenceExpectation,
    Task2RouteEvidenceStore,
    task2_route_evidence_target_digest,
)
from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis
from src.presentation.api.v1.admin import vpn_tester as vpn_tester_module
from src.presentation.api.v1.admin.vpn_tester import router
from src.presentation.middleware.admin_host_guard import (
    TASK2_ROUTE_EVIDENCE_EXEMPT_PATH,
    TASK2_ROUTE_EVIDENCE_HOST,
    AdminHostGuardMiddleware,
)

WEBHOOK_SECRET = "liveRouteEvidenceWebhookCredentialAlpha123456"
SYNTHETIC_USER = "task2-route-evidence@cybervpn.internal"
NOW = 1_771_886_901
PATH = "/admin/vpn-tester/internal/task2/route-evidence/xray-routing-webhook"


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.fail_on: str | None = None

    async def set(self, name: str, value: str, *, ex: int, nx: bool = False) -> bool:
        if self.fail_on == "set":
            raise RedisError("redis unavailable")
        if nx and name in self.values:
            return False
        self.values[name] = value
        self.ttls[name] = ex
        return True

    async def getdel(self, name: str) -> str | None:
        if self.fail_on == "getdel":
            raise RedisError("redis unavailable")
        self.ttls.pop(name, None)
        return self.values.pop(name, None)

    async def get(self, name: str) -> str | None:
        if self.fail_on == "get":
            raise RedisError("redis unavailable")
        return self.values.get(name)

    async def delete(self, *names: str) -> int:
        deleted = 0
        for name in names:
            self.ttls.pop(name, None)
            deleted += int(self.values.pop(name, None) is not None)
        return deleted


def _payload(
    *,
    target: str = "tcp:example.org:443",
    email: str | None = SYNTHETIC_USER,
    selected_outbound: str | None = "DE_EXCEPTIONS_BRIDGE",
) -> dict[str, Any]:
    return {
        "email": email,
        "level": None,
        "protocol": "tls",
        "network": "tcp",
        "source": "tcp:198.51.100.10:54203",
        "destination": target,
        "routeTarget": "tcp:de-bridge.cybervpn.internal:443",
        "originalTarget": target,
        "inboundTag": "SPB_EXCEPTIONS_REALITY_443",
        "inboundName": "vless",
        "inboundLocal": "tcp:192.0.2.10:443",
        "outboundTag": selected_outbound,
        "ts": NOW,
    }


def _configure_settings(
    monkeypatch: pytest.MonkeyPatch,
    *,
    enabled: bool = True,
    max_body_bytes: int = 4096,
) -> None:
    monkeypatch.setattr(settings, "vpn_tester_task2_route_evidence_enabled", enabled)
    monkeypatch.setattr(settings, "vpn_tester_task2_xray_webhook_secret", SecretStr(WEBHOOK_SECRET))
    monkeypatch.setattr(settings, "vpn_tester_task2_synthetic_user", SYNTHETIC_USER)
    monkeypatch.setattr(settings, "vpn_tester_task2_route_evidence_expectation_ttl_seconds", 300)
    monkeypatch.setattr(settings, "vpn_tester_task2_route_evidence_result_ttl_seconds", 3600)
    monkeypatch.setattr(settings, "vpn_tester_task2_xray_webhook_max_skew_seconds", 60)
    monkeypatch.setattr(settings, "vpn_tester_task2_xray_webhook_max_body_bytes", max_body_bytes)
    monkeypatch.setattr(vpn_tester_module.time, "time", lambda: NOW)


def _app(fake_redis: FakeRedis) -> FastAPI:
    app = FastAPI()

    async def override_get_redis() -> Generator[FakeRedis]:
        yield fake_redis

    app.dependency_overrides[get_redis] = override_get_redis
    app.include_router(router)
    return app


def _guarded_full_path_app(fake_redis: FakeRedis) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        AdminHostGuardMiddleware,
        allowed_hosts=["admin.cyber-vpn.net"],
        environment="production",
    )

    async def override_get_redis() -> Generator[FakeRedis]:
        yield fake_redis

    app.dependency_overrides[get_redis] = override_get_redis
    app.include_router(router, prefix="/api/v1")
    return app


async def _seed_expectation(
    fake_redis: FakeRedis,
    *,
    target: str = "tcp:example.org:443",
    expected_outbound: str = "DE_EXCEPTIONS_BRIDGE",
) -> Task2RouteEvidenceExpectation:
    store = Task2RouteEvidenceStore(
        fake_redis,
        expectation_ttl_seconds=300,
        result_ttl_seconds=3600,
        webhook_secret=WEBHOOK_SECRET,
    )
    expectation = Task2RouteEvidenceExpectation(
        run_id="run-1",
        route_key="task2.route.tcp.example",
        target_digest=task2_route_evidence_target_digest(WEBHOOK_SECRET, target),
        expected_outbound=expected_outbound,
        expected_inbound_tag="SPB_EXCEPTIONS_REALITY_443",
        expected_network="tcp",
    )
    await store.create_expectation(expectation)
    return expectation


def _headers(secret: str = WEBHOOK_SECRET) -> dict[str, str]:
    return {
        TASK2_XRAY_WEBHOOK_SECRET_HEADER: secret,
        vpn_tester_module.TASK2_ROUTE_EVIDENCE_INGRESS_HEADER: (
            vpn_tester_module.TASK2_ROUTE_EVIDENCE_INGRESS_MARKER
        ),
        "Content-Type": "application/json",
    }


@pytest.fixture
def client_and_redis(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[TestClient, FakeRedis]]:
    fake_redis = FakeRedis()
    _configure_settings(monkeypatch)
    with TestClient(_app(fake_redis)) as client:
        yield client, fake_redis


def test_valid_callback_returns_safe_response_and_route_is_hidden_from_openapi(
    client_and_redis: tuple[TestClient, FakeRedis],
) -> None:
    client, fake_redis = client_and_redis
    asyncio.run(_seed_expectation(fake_redis))

    response = client.post(PATH, headers=_headers(), json=_payload())

    assert response.status_code == 202
    body = response.json()
    assert set(body) == {"run_id", "route_key", "selected_outbound", "verdict", "digest"}
    assert body["selected_outbound"] == "DE_EXCEPTIONS_BRIDGE"
    assert body["verdict"] == "pass"
    assert PATH not in client.get("/openapi.json").json()["paths"]


def test_full_admin_host_guard_allows_only_dedicated_task2_collector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = FakeRedis()
    _configure_settings(monkeypatch)
    asyncio.run(_seed_expectation(fake_redis))

    with TestClient(
        _guarded_full_path_app(fake_redis),
        base_url=f"https://{TASK2_ROUTE_EVIDENCE_HOST}",
    ) as client:
        collector = client.post(TASK2_ROUTE_EVIDENCE_EXEMPT_PATH, headers=_headers(), json=_payload())
        other_admin = client.get("/api/v1/admin/vpn-tester/overview")

    assert collector.status_code == 202
    assert other_admin.status_code == 404


def test_bad_secret_returns_401_without_consuming_expectation(client_and_redis: tuple[TestClient, FakeRedis]) -> None:
    client, fake_redis = client_and_redis
    expectation = asyncio.run(_seed_expectation(fake_redis))

    response = client.post(PATH, headers=_headers("wrong-secret"), json=_payload())

    assert response.status_code == 401
    assert Task2RouteEvidenceStore.expectation_key(expectation.target_digest) in fake_redis.values


def test_missing_trusted_ingress_marker_returns_404_without_consuming_expectation(
    client_and_redis: tuple[TestClient, FakeRedis],
) -> None:
    client, fake_redis = client_and_redis
    expectation = asyncio.run(_seed_expectation(fake_redis))

    response = client.post(
        PATH,
        headers={TASK2_XRAY_WEBHOOK_SECRET_HEADER: WEBHOOK_SECRET, "Content-Type": "application/json"},
        json=_payload(),
    )

    assert response.status_code == 404
    assert Task2RouteEvidenceStore.expectation_key(expectation.target_digest) in fake_redis.values


def test_disabled_feature_returns_404_without_consuming_expectation(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    _configure_settings(monkeypatch, enabled=False)
    expectation = asyncio.run(_seed_expectation(fake_redis))

    with TestClient(_app(fake_redis)) as client:
        response = client.post(PATH, headers=_headers(), json=_payload())

    assert response.status_code == 404
    assert Task2RouteEvidenceStore.expectation_key(expectation.target_digest) in fake_redis.values


def test_body_size_limit_rejects_before_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    _configure_settings(monkeypatch, max_body_bytes=512)
    asyncio.run(_seed_expectation(fake_redis, target="tcp:oversized.example:443"))
    oversized_target = f"tcp:{'x' * 900}.example:443"

    with TestClient(_app(fake_redis)) as client:
        response = client.post(PATH, headers=_headers(), json=_payload(target=oversized_target))

    assert response.status_code == 413
    assert not any(key.startswith(TASK2_ROUTE_EVIDENCE_RESULT_PREFIX) for key in fake_redis.values)


def test_redis_failure_returns_503_not_success(client_and_redis: tuple[TestClient, FakeRedis]) -> None:
    client, fake_redis = client_and_redis
    asyncio.run(_seed_expectation(fake_redis))
    fake_redis.fail_on = "getdel"

    response = client.post(PATH, headers=_headers(), json=_payload())

    assert response.status_code == 503


def test_non_json_content_type_is_rejected(client_and_redis: tuple[TestClient, FakeRedis]) -> None:
    client, fake_redis = client_and_redis
    asyncio.run(_seed_expectation(fake_redis))

    response = client.post(
        PATH,
        headers={**_headers(), "Content-Type": "text/plain"},
        content=json.dumps(_payload()),
    )

    assert response.status_code == 415


def test_query_string_is_rejected(client_and_redis: tuple[TestClient, FakeRedis]) -> None:
    client, fake_redis = client_and_redis
    asyncio.run(_seed_expectation(fake_redis))

    response = client.post(f"{PATH}?secret=bad", headers=_headers(), json=_payload())

    assert response.status_code == 400


def test_cookie_header_is_rejected(client_and_redis: tuple[TestClient, FakeRedis]) -> None:
    client, fake_redis = client_and_redis
    asyncio.run(_seed_expectation(fake_redis))

    response = client.post(PATH, headers={**_headers(), "Cookie": "session=secret"}, json=_payload())

    assert response.status_code == 400


def test_authorization_header_is_rejected(client_and_redis: tuple[TestClient, FakeRedis]) -> None:
    client, fake_redis = client_and_redis
    asyncio.run(_seed_expectation(fake_redis))

    response = client.post(PATH, headers={**_headers(), "Authorization": "Bearer token"}, json=_payload())

    assert response.status_code == 400


def test_duplicate_webhook_secret_header_is_rejected(client_and_redis: tuple[TestClient, FakeRedis]) -> None:
    client, fake_redis = client_and_redis
    asyncio.run(_seed_expectation(fake_redis))

    response = client.post(
        PATH,
        headers=[
            (TASK2_XRAY_WEBHOOK_SECRET_HEADER, WEBHOOK_SECRET),
            (TASK2_XRAY_WEBHOOK_SECRET_HEADER, WEBHOOK_SECRET),
            (
                vpn_tester_module.TASK2_ROUTE_EVIDENCE_INGRESS_HEADER,
                vpn_tester_module.TASK2_ROUTE_EVIDENCE_INGRESS_MARKER,
            ),
            ("Content-Type", "application/json"),
        ],
        content=json.dumps(_payload()),
    )

    assert response.status_code == 400


def test_duplicate_ingress_marker_header_is_rejected(client_and_redis: tuple[TestClient, FakeRedis]) -> None:
    client, fake_redis = client_and_redis
    expectation = asyncio.run(_seed_expectation(fake_redis))

    response = client.post(
        PATH,
        headers=[
            (TASK2_XRAY_WEBHOOK_SECRET_HEADER, WEBHOOK_SECRET),
            (
                vpn_tester_module.TASK2_ROUTE_EVIDENCE_INGRESS_HEADER,
                vpn_tester_module.TASK2_ROUTE_EVIDENCE_INGRESS_MARKER,
            ),
            (
                vpn_tester_module.TASK2_ROUTE_EVIDENCE_INGRESS_HEADER,
                vpn_tester_module.TASK2_ROUTE_EVIDENCE_INGRESS_MARKER,
            ),
            ("Content-Type", "application/json"),
        ],
        content=json.dumps(_payload()),
    )

    assert response.status_code == 400
    assert Task2RouteEvidenceStore.expectation_key(expectation.target_digest) in fake_redis.values
