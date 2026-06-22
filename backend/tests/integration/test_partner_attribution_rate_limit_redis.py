from __future__ import annotations

import os
from uuid import UUID

import pytest
import redis.asyncio as redis
from fastapi import HTTPException
from prometheus_client import REGISTRY
from starlette.requests import Request

from src.presentation.api.v1.partner_attribution.schemas import PartnerAttributionCaptureRequest
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


def _redis_url() -> str:
    url = os.getenv("CYBERVPN_TEST_REDIS_URL")
    if not url:
        pytest.skip("CYBERVPN_TEST_REDIS_URL is required for Redis integration rate-limit tests")
    return url


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


async def _assert_limited(coro, *, scope: str, retry_after: str) -> None:
    before = REGISTRY.get_sample_value("partner_attribution_rate_limited_total", {"scope": scope}) or 0
    with pytest.raises(HTTPException) as exc_info:
        await coro

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {"Retry-After": retry_after}
    assert exc_info.value.detail["code"] == "PARTNER_ATTRIBUTION_RATE_LIMITED"
    assert exc_info.value.detail["scope"] == scope
    after = REGISTRY.get_sample_value("partner_attribution_rate_limited_total", {"scope": scope}) or 0
    assert after == before + 1


@pytest.mark.asyncio
async def test_partner_attribution_rate_limits_against_real_redis() -> None:
    redis_client = redis.from_url(_redis_url(), encoding="utf-8", decode_responses=True)
    try:
        await redis_client.flushdb()

        payload = PartnerAttributionCaptureRequest(
            public_token="rt-capture-ip-token",
            browser_key="rt-capture-ip-browser",
        )
        for _ in range(CAPTURE_IP_LIMIT):
            await check_partner_attribution_capture_rate_limit(
                request=_request(ip="203.0.113.10"),
                payload=payload,
                redis_client=redis_client,
            )
        await _assert_limited(
            check_partner_attribution_capture_rate_limit(
                request=_request(ip="203.0.113.10"),
                payload=payload,
                redis_client=redis_client,
            ),
            scope="capture_ip",
            retry_after="600",
        )

        await redis_client.flushdb()

        payload = PartnerAttributionCaptureRequest(
            public_token="rt-shared-slug-token",
            browser_key="rt-shared-slug-browser",
        )
        for index in range(CAPTURE_SLUG_LIMIT):
            await check_partner_attribution_capture_rate_limit(
                request=_request(ip=f"198.51.100.{(index % 200) + 1}"),
                payload=payload,
                redis_client=redis_client,
            )
        await _assert_limited(
            check_partner_attribution_capture_rate_limit(
                request=_request(ip="192.0.2.200"),
                payload=payload,
                redis_client=redis_client,
            ),
            scope="capture_slug",
            retry_after="600",
        )

        await redis_client.flushdb()

        browser_key = "runtime-browser-key"
        for index in range(BROWSER_ACTIVE_SESSION_LIMIT + 1):
            await check_partner_attribution_capture_rate_limit(
                request=_request(ip=f"203.0.113.{index + 1}"),
                payload=PartnerAttributionCaptureRequest(
                    public_token=f"rt-browser-token-{index}",
                    browser_key=browser_key,
                ),
                redis_client=redis_client,
            )
        await check_partner_attribution_capture_rate_limit(
            request=_request(ip="203.0.113.200"),
            payload=PartnerAttributionCaptureRequest(public_token="rt-browser-token-0", browser_key=browser_key),
            redis_client=redis_client,
        )
        await check_partner_attribution_capture_rate_limit(
            request=_request(ip="203.0.113.201"),
            payload=PartnerAttributionCaptureRequest(
                public_token="rt-browser-token-over",
                browser_key=browser_key,
            ),
            redis_client=redis_client,
        )

        await redis_client.flushdb()

        for _ in range(TRANSFER_IP_LIMIT):
            await check_partner_attribution_transfer_rate_limit(
                request=_request(ip="203.0.113.30"),
                redis_client=redis_client,
            )
        await _assert_limited(
            check_partner_attribution_transfer_rate_limit(
                request=_request(ip="203.0.113.30"),
                redis_client=redis_client,
            ),
            scope="transfer_ip",
            retry_after="600",
        )

        await redis_client.flushdb()

        user_id = UUID("11111111-1111-4111-8111-111111111111")
        for _ in range(CLAIM_USER_LIMIT):
            await check_partner_attribution_claim_rate_limit(user_id=user_id, redis_client=redis_client)
        await _assert_limited(
            check_partner_attribution_claim_rate_limit(user_id=user_id, redis_client=redis_client),
            scope="claim_user",
            retry_after="600",
        )
    finally:
        await redis_client.aclose()
