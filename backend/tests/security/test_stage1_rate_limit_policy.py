"""S1-BE-007 rate-limit policy checks for launch-critical surfaces."""

from __future__ import annotations

from collections import defaultdict
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from src.presentation.middleware.rate_limit import RateLimitMiddleware


def _request(path: str, method: str = "POST") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "client": ("203.0.113.10", 43120),
            "scheme": "https",
            "server": ("backend", 443),
        }
    )


def _s1_middleware(**overrides: int) -> RateLimitMiddleware:
    RateLimitMiddleware._circuit_breaker = None
    return RateLimitMiddleware(
        MagicMock(),
        requests_per_minute=100,
        window_seconds=60,
        fail_open=False,
        auth_sensitive_requests_per_minute=overrides.get("auth", 20),
        payment_write_requests_per_minute=overrides.get("payment", 30),
        trial_activate_requests_per_minute=overrides.get("trial", 10),
        growth_sensitive_requests_per_minute=overrides.get("growth", 60),
        support_write_requests_per_minute=overrides.get("support", 30),
        messaging_write_requests_per_minute=overrides.get("messaging_write", 30),
        messaging_realtime_requests_per_minute=overrides.get("messaging_realtime", 60),
        messaging_admin_read_requests_per_minute=overrides.get("messaging_admin_read", 120),
        messaging_broadcast_requests_per_minute=overrides.get("messaging_broadcast", 10),
    )


class _FakeRedisPipeline:
    def __init__(self, store: dict[str, dict[str, float]]) -> None:
        self.store = store
        self.ops: list[tuple[str, tuple]] = []

    async def __aenter__(self) -> _FakeRedisPipeline:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def zremrangebyscore(self, key: str, minimum: float, maximum: float) -> None:
        self.ops.append(("zremrangebyscore", (key, minimum, maximum)))

    def zadd(self, key: str, mapping: dict[str, float]) -> None:
        self.ops.append(("zadd", (key, mapping)))

    def zcard(self, key: str) -> None:
        self.ops.append(("zcard", (key,)))

    def expire(self, key: str, seconds: int) -> None:
        self.ops.append(("expire", (key, seconds)))

    async def execute(self) -> list[int | bool]:
        results: list[int | bool] = []
        for op_name, args in self.ops:
            if op_name == "zremrangebyscore":
                key, _minimum, maximum = args
                bucket = self.store[key]
                removed = [member for member, score in bucket.items() if score <= maximum]
                for member in removed:
                    bucket.pop(member, None)
                results.append(len(removed))
            elif op_name == "zadd":
                key, mapping = args
                self.store[key].update(mapping)
                results.append(len(mapping))
            elif op_name == "zcard":
                (key,) = args
                results.append(len(self.store[key]))
            elif op_name == "expire":
                results.append(True)
        return results


class _FakeRedisClient:
    def __init__(self) -> None:
        self.store: dict[str, dict[str, float]] = defaultdict(dict)

    def pipeline(self, transaction: bool = True) -> _FakeRedisPipeline:
        return _FakeRedisPipeline(self.store)

    async def aclose(self) -> None:
        return None


@pytest.mark.parametrize(
    ("path", "method", "expected_bucket", "expected_limit"),
    [
        ("/api/v1/auth/login", "POST", "s1_auth_sensitive", 20),
        ("/api/v1/auth/refresh", "POST", "s1_auth_sensitive", 20),
        ("/api/v1/mobile/auth/register", "POST", "s1_auth_sensitive", 20),
        ("/api/v1/oauth/github/callback", "POST", "s1_auth_sensitive", 20),
        ("/api/v1/payments/checkout/commit", "POST", "s1_payment_write", 30),
        ("/api/v1/checkout-sessions/", "POST", "s1_payment_write", 30),
        ("/api/v1/payment-attempts/", "POST", "s1_payment_write", 30),
        ("/api/v1/telegram/payments/stars", "POST", "s1_payment_write", 30),
        ("/api/v1/telegram/bot/user/123/checkout/commit", "POST", "s1_payment_write", 30),
        ("/api/v1/trial/activate", "POST", "s1_trial_activate", 10),
        ("/api/v1/miniapp/trial/activate", "POST", "s1_trial_activate", 10),
        ("/api/v1/telegram/bot/user/123/trial/activate", "POST", "s1_trial_activate", 10),
        ("/api/v1/referral/code", "GET", "s1_growth_sensitive", 60),
        ("/api/v1/promo/validate", "POST", "s1_growth_sensitive", 60),
        ("/api/v1/gifts/redeem", "POST", "s1_growth_sensitive", 60),
        ("/api/v1/admin/mobile-users/user-id/notes", "POST", "s1_support_write", 30),
        ("/api/v1/admin/mobile-users/user-id/devices/device-id", "DELETE", "s1_support_write", 30),
        ("/api/v1/me/conversations/conv_1/messages", "POST", "messaging_write", 30),
        ("/api/v1/me/conversations/conv_1/read", "POST", "messaging_write", 30),
        ("/api/v1/me/notifications/read", "POST", "messaging_write", 30),
        ("/api/v1/me/notifications/dismiss", "POST", "messaging_write", 30),
        ("/api/v1/admin/messaging/conversations", "POST", "messaging_write", 30),
        ("/api/v1/admin/messaging/conversations/conv_1/internal-notes", "POST", "messaging_write", 30),
        ("/api/v1/me/realtime/sync", "GET", "messaging_realtime", 60),
        ("/api/v1/me/realtime/ticket", "POST", "messaging_realtime", 60),
        ("/api/v1/admin/messaging/realtime/sse", "GET", "messaging_realtime", 60),
        ("/api/v1/admin/messaging/conversations", "GET", "messaging_admin_read", 120),
        ("/api/v1/admin/messaging/conversations/conv_1", "GET", "messaging_admin_read", 120),
        ("/api/v1/admin/notifications/broadcasts", "POST", "messaging_broadcast", 10),
        ("/api/v1/admin/notifications/broadcasts/bc_1/cancel", "POST", "messaging_broadcast", 10),
    ],
)
def test_stage1_critical_surfaces_have_category_budgets(
    path: str,
    method: str,
    expected_bucket: str,
    expected_limit: int,
) -> None:
    middleware = _s1_middleware()
    request = _request(path, method)

    assert middleware._rate_limit_bucket_for(request) == expected_bucket
    assert middleware._requests_budget_for(request) == expected_limit


def test_stage1_non_critical_routes_keep_default_path_bucket() -> None:
    middleware = _s1_middleware()
    request = _request("/api/v1/status", "GET")

    assert middleware._rate_limit_bucket_for(request) == "/api/v1/status"
    assert middleware._requests_budget_for(request) == 100


def test_stage1_helix_admin_get_budget_stays_high_for_polling() -> None:
    middleware = _s1_middleware()
    request = _request("/api/v1/helix/admin/rollouts/rollout-helix-lab/canary-evidence", "GET")

    assert middleware._rate_limit_bucket_for(request) == request.url.path
    assert middleware._requests_budget_for(request) == 1500


@pytest.mark.asyncio
async def test_stage1_payment_write_bucket_returns_429_when_shared_category_budget_is_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    RateLimitMiddleware._circuit_breaker = None
    fake_redis = _FakeRedisClient()
    monkeypatch.setattr(
        "src.presentation.middleware.rate_limit.get_redis_pool",
        lambda: object(),
    )
    monkeypatch.setattr(
        "src.presentation.middleware.rate_limit.redis.Redis",
        lambda connection_pool: fake_redis,
    )

    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=100,
        window_seconds=60,
        fail_open=False,
        payment_write_requests_per_minute=2,
    )

    @app.post("/api/v1/payments/checkout/quote")
    async def quote() -> dict[str, str]:
        return {"status": "quoted"}

    @app.post("/api/v1/payments/checkout/commit")
    async def commit() -> dict[str, str]:
        return {"status": "committed"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://backend") as client:
        first = await client.post("/api/v1/payments/checkout/quote")
        second = await client.post("/api/v1/payments/checkout/commit")
        third = await client.post("/api/v1/payments/checkout/quote")

    assert [first.status_code, second.status_code, third.status_code] == [200, 200, 429]
    assert third.json() == {"detail": "Too many requests"}
    assert third.headers["Retry-After"] == "60"


@pytest.mark.parametrize(
    ("path", "method", "expect_limited"),
    [
        ("/api/v1/auth/me", "GET", False),
        ("/api/v1/auth/session", "GET", False),
        ("/api/v1/auth/refresh", "POST", True),
    ],
)
def test_stage1_only_read_session_auth_paths_remain_exempt(
    path: str,
    method: str,
    expect_limited: bool,
) -> None:
    middleware = _s1_middleware()
    request = _request(path, method)

    assert (
        path not in middleware._EXEMPT_PATHS and middleware._rate_limit_bucket_for(request) == "s1_auth_sensitive"
    ) is expect_limited
