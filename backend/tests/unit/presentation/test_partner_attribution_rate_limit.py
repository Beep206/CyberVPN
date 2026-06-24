from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

import pytest
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from prometheus_client import REGISTRY
from starlette.requests import Request

from src.application.use_cases.auth_realms import RealmResolution
from src.config import settings
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.presentation.api.v1.partner_attribution.routes import router as partner_attribution_router
from src.presentation.api.v1.partner_attribution.schemas import PartnerAttributionCaptureRequest
from src.presentation.dependencies.auth_realms import get_request_public_customer_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_attribution_rate_limit import (
    BROWSER_ACTIVE_SESSION_LIMIT,
    CAPTURE_IP_LIMIT,
    CAPTURE_SLUG_LIMIT,
    CLAIM_USER_LIMIT,
    TRANSFER_IP_LIMIT,
    check_partner_attribution_capture_rate_limit,
    check_partner_attribution_claim_rate_limit,
    check_partner_attribution_transfer_rate_limit,
)


class _FakeRedisPipeline:
    def __init__(self, store: dict[str, dict[str, float]], *, fail: bool = False) -> None:
        self.store = store
        self.fail = fail
        self.ops: list[tuple[str, tuple[object, ...]]] = []

    async def __aenter__(self) -> _FakeRedisPipeline:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def zremrangebyscore(self, key: str, minimum: float, maximum: float) -> None:
        self.ops.append(("zremrangebyscore", (key, minimum, maximum)))

    def zadd(self, key: str, mapping: Mapping[str, float]) -> None:
        self.ops.append(("zadd", (key, mapping)))

    def zcard(self, key: str) -> None:
        self.ops.append(("zcard", (key,)))

    def expire(self, key: str, seconds: int) -> None:
        self.ops.append(("expire", (key, seconds)))

    async def execute(self) -> list[int | bool]:
        if self.fail:
            raise redis.ConnectionError("fake redis outage")

        results: list[int | bool] = []
        for op_name, args in self.ops:
            if op_name == "zremrangebyscore":
                key, _minimum, maximum = args
                bucket = self.store[str(key)]
                removed = [member for member, score in bucket.items() if score <= float(maximum)]
                for member in removed:
                    bucket.pop(member, None)
                results.append(len(removed))
            elif op_name == "zadd":
                key, mapping = args
                assert isinstance(mapping, Mapping)
                self.store[str(key)].update({str(member): float(score) for member, score in mapping.items()})
                results.append(len(mapping))
            elif op_name == "zcard":
                (key,) = args
                results.append(len(self.store[str(key)]))
            elif op_name == "expire":
                results.append(True)
        return results


class _FakeRedisClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.store: dict[str, dict[str, float]] = defaultdict(dict)
        self.fail = fail

    def pipeline(self, transaction: bool = True) -> _FakeRedisPipeline:
        assert transaction is True
        return _FakeRedisPipeline(self.store, fail=self.fail)


def _request(*, ip: str = "203.0.113.10") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/partner-attribution/capture",
            "headers": [],
            "client": (ip, 43120),
            "scheme": "https",
            "server": ("backend", 443),
        }
    )


def _capture_payload(
    *,
    public_token: str = "public-token-123",
    browser_key: str = "test-browser-key",
) -> PartnerAttributionCaptureRequest:
    return PartnerAttributionCaptureRequest(public_token=public_token, browser_key=browser_key)


def _capture_route_app(*, redis_client: _FakeRedisClient | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(partner_attribution_router)

    async def _override_redis():
        yield redis_client or _FakeRedisClient()

    async def _override_db():
        yield object()

    async def _override_realm():
        return RealmResolution(
            auth_realm=AuthRealmModel(
                realm_key="customer",
                realm_type="customer",
                display_name="Customer",
                audience="cybervpn:customer",
                cookie_namespace="customer",
                status="active",
                is_default=True,
            ),
            source="test",
            host="cyber-vpn.net",
        )

    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_request_public_customer_realm] = _override_realm
    return app


@pytest.mark.asyncio
async def test_capture_ip_limit_returns_429_with_retry_after() -> None:
    redis_client = _FakeRedisClient()
    payload = _capture_payload()

    for _ in range(CAPTURE_IP_LIMIT):
        await check_partner_attribution_capture_rate_limit(
            request=_request(),
            payload=payload,
            redis_client=redis_client,  # type: ignore[arg-type]
        )

    before = REGISTRY.get_sample_value("partner_attribution_rate_limited_total", {"scope": "capture_ip"}) or 0
    with pytest.raises(HTTPException) as exc_info:
        await check_partner_attribution_capture_rate_limit(
            request=_request(),
            payload=payload,
            redis_client=redis_client,  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {"Retry-After": "600"}
    assert exc_info.value.detail["code"] == "PARTNER_ATTRIBUTION_RATE_LIMITED"
    assert exc_info.value.detail["scope"] == "capture_ip"
    after = REGISTRY.get_sample_value("partner_attribution_rate_limited_total", {"scope": "capture_ip"}) or 0
    assert after == before + 1


@pytest.mark.asyncio
async def test_capture_slug_limit_is_shared_across_ips() -> None:
    redis_client = _FakeRedisClient()
    payload = _capture_payload(public_token="shared-public-token")

    for index in range(CAPTURE_SLUG_LIMIT):
        await check_partner_attribution_capture_rate_limit(
            request=_request(ip=f"203.0.113.{index + 1}"),
            payload=payload,
            redis_client=redis_client,  # type: ignore[arg-type]
        )

    with pytest.raises(HTTPException) as exc_info:
        await check_partner_attribution_capture_rate_limit(
            request=_request(ip="198.51.100.200"),
            payload=payload,
            redis_client=redis_client,  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["scope"] == "capture_slug"


@pytest.mark.asyncio
async def test_capture_rate_limit_does_not_treat_browser_history_as_active_sessions() -> None:
    redis_client = _FakeRedisClient()
    browser_key = "browser-opaque-key"

    for index in range(BROWSER_ACTIVE_SESSION_LIMIT + 1):
        await check_partner_attribution_capture_rate_limit(
            request=_request(ip=f"203.0.113.{index + 1}"),
            payload=_capture_payload(public_token=f"public-token-{index}", browser_key=browser_key),
            redis_client=redis_client,  # type: ignore[arg-type]
        )

    await check_partner_attribution_capture_rate_limit(
        request=_request(ip="203.0.113.100"),
        payload=_capture_payload(public_token="public-token-0", browser_key=browser_key),
        redis_client=redis_client,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_transfer_consume_ip_limit_returns_429() -> None:
    redis_client = _FakeRedisClient()
    for _ in range(TRANSFER_IP_LIMIT):
        await check_partner_attribution_transfer_rate_limit(
            request=_request(),
            redis_client=redis_client,  # type: ignore[arg-type]
        )

    with pytest.raises(HTTPException) as exc_info:
        await check_partner_attribution_transfer_rate_limit(
            request=_request(),
            redis_client=redis_client,  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["scope"] == "transfer_ip"


@pytest.mark.asyncio
async def test_claim_user_limit_returns_429() -> None:
    redis_client = _FakeRedisClient()
    for _ in range(CLAIM_USER_LIMIT):
        await check_partner_attribution_claim_rate_limit(
            user_id="customer-user-id",
            redis_client=redis_client,  # type: ignore[arg-type]
        )

    with pytest.raises(HTTPException) as exc_info:
        await check_partner_attribution_claim_rate_limit(
            user_id="customer-user-id",
            redis_client=redis_client,  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["scope"] == "claim_user"


@pytest.mark.asyncio
async def test_redis_outage_fails_closed_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "rate_limit_fail_open", False)

    with pytest.raises(HTTPException) as exc_info:
        await check_partner_attribution_transfer_rate_limit(
            request=_request(),
            redis_client=_FakeRedisClient(fail=True),  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.headers == {"Retry-After": "30"}
    assert exc_info.value.detail["code"] == "PARTNER_ATTRIBUTION_RATE_LIMIT_UNAVAILABLE"


@pytest.mark.asyncio
async def test_redis_outage_fails_open_outside_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "rate_limit_fail_open", False)

    await check_partner_attribution_transfer_rate_limit(
        request=_request(),
        redis_client=_FakeRedisClient(fail=True),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_capture_route_returns_429_before_use_case_when_ip_bucket_is_exhausted() -> None:
    redis_client = _FakeRedisClient()
    payload = _capture_payload(browser_key="route-browser-key")
    for _ in range(CAPTURE_IP_LIMIT):
        await check_partner_attribution_capture_rate_limit(
            request=_request(ip="127.0.0.1"),
            payload=payload,
            redis_client=redis_client,  # type: ignore[arg-type]
        )

    app = _capture_route_app(redis_client=redis_client)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://cyber-vpn.net") as client:
        response = await client.post(
            "/partner-attribution/capture",
            headers={"Idempotency-Key": "route-capture-idempotency"},
            json={
                "public_token": payload.public_token,
                "browser_key": payload.browser_key,
            },
        )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "600"
    assert response.json()["detail"]["scope"] == "capture_ip"


@pytest.mark.asyncio
async def test_capture_route_requires_idempotency_key_before_capture_use_case() -> None:
    app = _capture_route_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://cyber-vpn.net") as client:
        response = await client.post(
            "/partner-attribution/capture",
            json={"public_token": "public-token-123", "browser_key": "route-browser-key"},
        )

    assert response.status_code == 428
    assert response.json()["detail"]["code"] == "PARTNER_CAPTURE_IDEMPOTENCY_KEY_REQUIRED"


@pytest.mark.asyncio
async def test_capture_route_requires_browser_key_before_capture_use_case() -> None:
    app = _capture_route_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://cyber-vpn.net") as client:
        response = await client.post(
            "/partner-attribution/capture",
            headers={"Idempotency-Key": "route-capture-idempotency"},
            json={"public_token": "public-token-123"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_capture_route_rejects_oversized_sub_id_map_before_rate_limit() -> None:
    redis_client = _FakeRedisClient()
    app = _capture_route_app(redis_client=redis_client)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://cyber-vpn.net") as client:
        response = await client.post(
            "/partner-attribution/capture",
            headers={"Idempotency-Key": "route-capture-idempotency"},
            json={
                "public_token": "public-token-123",
                "browser_key": "route-browser-key",
                "sub_ids": {f"sub_{index}": "value" for index in range(17)},
            },
        )

    assert response.status_code == 422
    assert redis_client.store == {}


@pytest.mark.asyncio
async def test_capture_route_rejects_nested_campaign_params_before_rate_limit() -> None:
    redis_client = _FakeRedisClient()
    app = _capture_route_app(redis_client=redis_client)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://cyber-vpn.net") as client:
        response = await client.post(
            "/partner-attribution/capture",
            headers={"Idempotency-Key": "route-capture-idempotency"},
            json={
                "public_token": "public-token-123",
                "browser_key": "route-browser-key",
                "campaign_params": {"utm_source": {"nested": "value"}},
            },
        )

    assert response.status_code == 422
    assert redis_client.store == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,payload",
    [
        ("campaign_params", {"campaign_params": {f"utm_{index}": "value" for index in range(25)}}),
        ("sub_ids", {"sub_ids": {"s" * 49: "value"}}),
        ("sub_ids", {"sub_ids": {"sub": "v" * 161}}),
        ("campaign_params", {"campaign_params": {"u" * 65: "value"}}),
        ("campaign_params", {"campaign_params": {"utm_source": "v" * 201}}),
    ],
)
async def test_capture_route_rejects_unbounded_campaign_and_sub_id_fields_before_rate_limit(
    field: str,
    payload: dict[str, dict[str, str]],
) -> None:
    redis_client = _FakeRedisClient()
    app = _capture_route_app(redis_client=redis_client)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://cyber-vpn.net") as client:
        response = await client.post(
            "/partner-attribution/capture",
            headers={"Idempotency-Key": f"route-capture-{field}"},
            json={
                "public_token": "public-token-123",
                "browser_key": "route-browser-key",
                **payload,
            },
        )

    assert response.status_code == 422
    assert redis_client.store == {}


def test_capture_request_accepts_campaign_and_sub_id_boundary_values() -> None:
    request = PartnerAttributionCaptureRequest(
        public_token="public-token-123",
        browser_key="route-browser-key",
        sub_ids={f"sub_{index:02d}": "v" * 160 for index in range(16)},
        campaign_params={f"utm_{index:02d}": "v" * 200 for index in range(24)},
    )

    assert len(request.sub_ids or {}) == 16
    assert len(request.campaign_params or {}) == 24


def test_capture_request_coerces_scalar_campaign_and_sub_id_values_for_compatibility() -> None:
    request = PartnerAttributionCaptureRequest(
        public_token="public-token-123",
        browser_key="route-browser-key",
        sub_ids={"creator": 42},
        campaign_params={"utm_source": "newsletter", "utm_term": 7, "utm_paid": False},
    )

    assert request.sub_ids == {"creator": "42"}
    assert request.campaign_params == {
        "utm_source": "newsletter",
        "utm_term": "7",
        "utm_paid": "False",
    }
